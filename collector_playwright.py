import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from db import connect

load_dotenv()
PROFILE_DIR = Path(os.getenv("BNF_PROFILE_DIR", "./.chrome-profile")).resolve()
FETCH_TIMEOUT = float(os.getenv("BNF_FETCH_TIMEOUT", "15"))
HEADLESS = os.getenv("BNF_HEADLESS", "true").lower() == "true"
CONCURRENCY = max(1, min(int(os.getenv("BNF_CONCURRENCY", "5")), 10))
SESSION_FILE = Path(os.getenv("BNF_SESSION_FILE", "./data/session.json")).resolve()


def parse_number(value):
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    multiplier = 1
    if text[-1:].lower() == "k":
        multiplier, text = 1_000, text[:-1]
    elif text[-1:].lower() == "m":
        multiplier, text = 1_000_000, text[:-1]
    try:
        return float(text) * multiplier
    except ValueError:
        return None


def generate_tickers(center, expiry, step, sides):
    strikes = [center + offset * step for offset in range(-sides, sides + 1)]
    return [
        (f"BANKNIFTY{expiry}{strike}{side}", strike, side)
        for strike in strikes
        for side in ("CE", "PE")
    ]


def fetch_ticker_data(context, ticker, strike, option_type, timeout_ms=15000):
    result = {
        "symbol": ticker, "strike": strike, "option_type": option_type,
        "open": None, "high": None, "low": None, "close": None,
        "volume": None, "cumulative_delta": None,
        "buy_volume": None, "sell_volume": None, "error": None,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    page = None
    snapshot_data = None

    def handle_websocket(ws):
        nonlocal snapshot_data
        
        def on_frame(payload):
            nonlocal snapshot_data
            try:
                if isinstance(payload, bytes):
                    payload = payload.decode('utf-8')
                
                if '"channel":"snapshot"' in payload and ticker in payload:
                    msg = json.loads(payload)
                    payload_data = msg.get("payload", {})
                    
                    # Try to find the ticker data
                    for key in payload_data:
                        if key == ticker or key.endswith(f":{ticker}") or ticker in key:
                            snapshot_data = payload_data[key]
                            return
                    
                    # Fallback: if only one key, use it
                    if len(payload_data) == 1:
                        snapshot_data = list(payload_data.values())[0]
            except Exception:
                pass
        
        ws.on("framereceived", lambda event: on_frame(event["payload"]))

    try:
        page = context.new_page()
        page.on("websocket", handle_websocket)
        
        url = f"https://gocharting.com/terminal?ticker=NSE:OPTIONS:{ticker}"
        page.goto(url, wait_until="commit", timeout=15000)
        
        # Wait for page to load
        page.wait_for_timeout(5000)
        
        # Trigger delta display with Alt+D
        page.keyboard.press("Alt+d")
        page.wait_for_timeout(1000)
        
        # Wait for snapshot data
        deadline = datetime.now().timestamp() * 1000 + timeout_ms
        while snapshot_data is None and datetime.now().timestamp() * 1000 < deadline:
            page.wait_for_timeout(300)
        
        # Extract data from snapshot
        if snapshot_data:
            derived = snapshot_data.get("derived_values") or {}
            result.update({
                "open": snapshot_data.get("open"),
                "high": snapshot_data.get("high"),
                "low": snapshot_data.get("low"),
                "close": snapshot_data.get("ltp"),
                "volume": snapshot_data.get("volume"),
                "cumulative_delta": derived.get("delta") or snapshot_data.get("delta") or snapshot_data.get("cum_delta"),
                "buy_volume": snapshot_data.get("buy_volume"),
                "sell_volume": snapshot_data.get("sell_volume"),
            })
        
        # Fallback: scrape from page text
        if snapshot_data is None:
            page.wait_for_timeout(2000)
        
        page_text = page.evaluate("() => document.body.innerText.slice(0, 5000)")
        
        # Parse buy/sell volumes from text
        buy_match = re.search(r"Buy\s*Vol(?:ume)?[:\s]+([\d,.]+[KkMm]?)", page_text, re.I)
        sell_match = re.search(r"Sell\s*Vol(?:ume)?[:\s]+([\d,.]+[KkMm]?)", page_text, re.I)
        
        if buy_match:
            result["buy_volume"] = parse_number(buy_match.group(1))
        if sell_match:
            result["sell_volume"] = parse_number(sell_match.group(1))
        
        # Fallback OHLC if snapshot didn't provide
        if result["open"] is None:
            patterns = {
                "open": r"O:\s*([\d,.]+)",
                "high": r"H:\s*([\d,.]+)",
                "low": r"L:\s*([\d,.]+)",
                "close": r"C:\s*([\d,.]+)",
            }
            for field, pattern in patterns.items():
                match = re.search(pattern, page_text)
                if match:
                    result[field] = parse_number(match.group(1))
        
        # Fallback volume
        if result["volume"] is None:
            vol_match = re.search(r"\bV:\s*([\d,.]+[KkMm]?)", page_text)
            if vol_match:
                result["volume"] = parse_number(vol_match.group(1))
        
        # Calculate delta from buy/sell if not from snapshot
        if result["cumulative_delta"] is None:
            if result["buy_volume"] is not None and result["sell_volume"] is not None:
                result["cumulative_delta"] = result["buy_volume"] - result["sell_volume"]
        
        # Check if we got any usable data
        if result["close"] is None and result["cumulative_delta"] is None:
            result["error"] = "No usable GoCharting data"
            
    except Exception as e:
        result["error"] = str(e)[:250]
    finally:
        if page:
            try:
                page.close()
            except:
                pass
    
    return result


def collect_option_chain(center, expiry, step=100, sides=5):
    from db import create_run, finish_run, save_snapshot

    run_id = create_run(center, expiry, step, sides)
    playwright = None
    browser = None
    results = []
    
    try:
        playwright = sync_playwright().start()
        
        # Launch browser with persistent context if session file exists
        if SESSION_FILE.exists():
            browser = playwright.chromium.launch(
                headless=HEADLESS,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ]
            )
            context = browser.new_context(
                viewport={"width": 1440, "height": 900},
                ignore_https_errors=True,
            )
            
            # Load session data
            page = context.new_page()
            page.goto("https://gocharting.com/")
            page.wait_for_timeout(2000)
            
            session_data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
            
            # Add cookies
            cookies = []
            for cookie in session_data.get("cookies", []):
                cookie_dict = {
                    "name": cookie["name"],
                    "value": cookie["value"],
                    "domain": cookie.get("domain", ".gocharting.com"),
                    "path": cookie.get("path", "/"),
                }
                if "expiry" in cookie:
                    cookie_dict["expires"] = cookie["expiry"]
                if "httpOnly" in cookie:
                    cookie_dict["httpOnly"] = cookie["httpOnly"]
                if "secure" in cookie:
                    cookie_dict["secure"] = cookie["secure"]
                if cookie.get("sameSite") in ["Strict", "Lax", "None"]:
                    cookie_dict["sameSite"] = cookie["sameSite"]
                
                cookies.append(cookie_dict)
            
            context.add_cookies(cookies)
            
            # Set local storage
            for key, value in session_data.get("local_storage", {}).items():
                page.evaluate(f"localStorage.setItem('{key}', {json.dumps(value)})")
            
            # Set session storage
            for key, value in session_data.get("session_storage", {}).items():
                page.evaluate(f"sessionStorage.setItem('{key}', {json.dumps(value)})")
            
            page.close()
        else:
            browser = playwright.chromium.launch(headless=HEADLESS)
            context = browser.new_context(
                viewport={"width": 1440, "height": 900}
            )
        
        # Generate tickers and collect
        tickers = generate_tickers(center, expiry, step, sides)
        
        # Process in batches
        for i in range(0, len(tickers), CONCURRENCY):
            batch = tickers[i:i + CONCURRENCY]
            
            # Process batch sequentially (Playwright context is not thread-safe for parallel tabs)
            for ticker, strike, option_type in batch:
                item = fetch_ticker_data(context, ticker, strike, option_type)
                save_snapshot(run_id, item)
                results.append(item)
        
        context.close()
        finish_run(run_id, "completed")
        
        return {
            "run_id": run_id,
            "center": center,
            "expiry": expiry,
            "concurrency": CONCURRENCY,
            "count": len(results),
            "successful": sum(1 for item in results if item["close"] is not None),
            "rows": results,
        }
        
    except Exception as exc:
        finish_run(run_id, "failed", str(exc)[:500])
        raise
    finally:
        if browser:
            try:
                browser.close()
            except:
                pass
        if playwright:
            try:
                playwright.stop()
            except:
                pass
