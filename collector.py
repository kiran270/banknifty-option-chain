import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from db import connect

load_dotenv()
PROFILE_DIR = Path(os.getenv("BNF_PROFILE_DIR", "./.chrome-profile")).resolve()
FETCH_TIMEOUT = float(os.getenv("BNF_FETCH_TIMEOUT", "15"))
HEADLESS = os.getenv("BNF_HEADLESS", "true").lower() == "true"
CONCURRENCY = max(1, min(int(os.getenv("BNF_CONCURRENCY", "5")), 10))
SESSION_FILE = Path(os.getenv("BNF_SESSION_FILE", "./data/session.json")).resolve()
CHROME_BINARY = os.getenv("CHROME_BINARY", "")
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", "")


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


def create_driver():
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    options = Options()
    options.add_argument(f"--user-data-dir={PROFILE_DIR}")
    options.add_argument("--window-size=1440,900")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    # Additional options for better WebSocket/performance logging in headless
    options.add_argument("--enable-features=NetworkService,NetworkServiceInProcess")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--enable-logging")
    options.add_argument("--v=1")
    # Ensure JavaScript is enabled
    options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.javascript": 1
    })
    if CHROME_BINARY:
        options.binary_location = CHROME_BINARY
    if HEADLESS:
        options.add_argument("--headless=new")
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    service = Service(CHROMEDRIVER_PATH) if CHROMEDRIVER_PATH else Service()
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(20)

    if SESSION_FILE.exists():
        driver.get("https://gocharting.com/")
        saved_session = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
        cookies = saved_session.get("cookies", [])
        for saved in cookies:
            cookie = {
                key: value for key, value in saved.items()
                if key in {"name", "value", "domain", "path", "expiry", "secure", "httpOnly", "sameSite"}
            }
            if cookie.get("sameSite") not in {"Strict", "Lax", "None"}:
                cookie.pop("sameSite", None)
            try:
                driver.add_cookie(cookie)
            except Exception:
                pass
        for key, value in saved_session.get("local_storage", {}).items():
            driver.execute_script("localStorage.setItem(arguments[0], arguments[1]);", key, value)
        for key, value in saved_session.get("session_storage", {}).items():
            driver.execute_script("sessionStorage.setItem(arguments[0], arguments[1]);", key, value)
        driver.refresh()
    return driver



def generate_tickers(center, expiry, step, sides):
    strikes = [center + offset * step for offset in range(-sides, sides + 1)]
    return [
        (f"BANKNIFTY{expiry}{strike}{side}", strike, side)
        for strike in strikes
        for side in ("CE", "PE")
    ]


def extract_snapshot(logs, ticker):
    for entry in reversed(logs):
        try:
            message = json.loads(entry["message"])["message"]
            if message["method"] != "Network.webSocketFrameReceived":
                continue
            payload = message["params"]["response"]["payloadData"]
            if ticker not in payload:
                continue
            parsed = json.loads(payload)
            if parsed.get("channel") != "snapshot":
                continue
            values = parsed.get("payload", {})
            for key, value in values.items():
                if key == ticker or key.endswith(f":{ticker}") or ticker in key:
                    return value
            if len(values) == 1:
                return next(iter(values.values()))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
    return None



def text_value(text, pattern):
    match = re.search(pattern, text, re.IGNORECASE)
    return parse_number(match.group(1)) if match else None


def collect_ticker(driver, ticker, strike, option_type):
    result = {
        "symbol": ticker, "strike": strike, "option_type": option_type,
        "open": None, "high": None, "low": None, "close": None,
        "volume": None, "cumulative_delta": None,
        "buy_volume": None, "sell_volume": None, "error": None,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        driver.get_log("performance")
        url = f"https://gocharting.com/terminal?ticker=NSE:OPTIONS:{ticker}"
        driver.get(url)
        # Increased wait time for WebSocket connections to establish in headless mode
        time.sleep(5.0)
        ActionChains(driver).key_down(Keys.ALT).send_keys("d").key_up(Keys.ALT).perform()
        # Additional wait after triggering delta display
        time.sleep(1.0)

        snapshot = None
        deadline = time.time() + FETCH_TIMEOUT
        while time.time() < deadline and snapshot is None:
            snapshot = extract_snapshot(driver.get_log("performance"), ticker)
            if snapshot is None:
                time.sleep(0.3)

        if snapshot:
            derived = snapshot.get("derived_values") or {}
            result.update({
                "open": snapshot.get("open"), "high": snapshot.get("high"),
                "low": snapshot.get("low"), "close": snapshot.get("ltp"),
                "volume": snapshot.get("volume"),
                "cumulative_delta": derived.get("delta", snapshot.get("delta", snapshot.get("cum_delta"))),
                "buy_volume": snapshot.get("buy_volume"),
                "sell_volume": snapshot.get("sell_volume"),
            })

        text = driver.find_element("tag name", "body").text[:5000]
        result["buy_volume"] = result["buy_volume"] or text_value(
            text, r"Buy\s*Vol(?:ume)?[:\s]+([\d,.]+[KkMm]?)"
        )
        result["sell_volume"] = result["sell_volume"] or text_value(
            text, r"Sell\s*Vol(?:ume)?[:\s]+([\d,.]+[KkMm]?)"
        )
        result["open"] = result["open"] or text_value(text, r"O:\s*([\d,.]+)")
        result["high"] = result["high"] or text_value(text, r"H:\s*([\d,.]+)")
        result["low"] = result["low"] or text_value(text, r"L:\s*([\d,.]+)")
        result["close"] = result["close"] or text_value(text, r"C:\s*([\d,.]+)")
        result["volume"] = result["volume"] or text_value(text, r"\bV:\s*([\d,.]+[KkMm]?)")

        if result["cumulative_delta"] is None:
            buy, sell = result["buy_volume"], result["sell_volume"]
            if buy is not None and sell is not None:
                result["cumulative_delta"] = buy - sell
        if snapshot is None and result["close"] is None and result["cumulative_delta"] is None:
            result["error"] = "No usable GoCharting data; verify saved login session and contract"
    except Exception as exc:
        result["error"] = str(exc)[:250]
    return result


def collect_option_chain(center, expiry, step=100, sides=5):
    from db import create_run, finish_run, save_snapshot

    run_id = create_run(center, expiry, step, sides)
    driver = None
    results = []
    try:
        driver = create_driver()
        tickers = generate_tickers(center, expiry, step, sides)
        for offset in range(0, len(tickers), CONCURRENCY):
            batch = tickers[offset:offset + CONCURRENCY]
            for item in collect_batch(driver, batch):
                save_snapshot(run_id, item)
                results.append(item)
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
        if driver:
            driver.quit()



def _empty_result(ticker, strike, option_type):
    return {
        "symbol": ticker, "strike": strike, "option_type": option_type,
        "open": None, "high": None, "low": None, "close": None,
        "volume": None, "cumulative_delta": None,
        "buy_volume": None, "sell_volume": None, "error": None,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def _fill_result(driver, ticker, strike, option_type, snapshot):
    result = _empty_result(ticker, strike, option_type)
    if snapshot:
        derived = snapshot.get("derived_values") or {}
        result.update({
            "open": snapshot.get("open"), "high": snapshot.get("high"),
            "low": snapshot.get("low"), "close": snapshot.get("ltp"),
            "volume": snapshot.get("volume"),
            "cumulative_delta": derived.get(
                "delta", snapshot.get("delta", snapshot.get("cum_delta"))
            ),
            "buy_volume": snapshot.get("buy_volume"),
            "sell_volume": snapshot.get("sell_volume"),
        })

    text = driver.find_element("tag name", "body").text[:5000]
    fallbacks = {
        "buy_volume": r"Buy\s*Vol(?:ume)?[:\s]+([\d,.]+[KkMm]?)",
        "sell_volume": r"Sell\s*Vol(?:ume)?[:\s]+([\d,.]+[KkMm]?)",
        "open": r"O:\s*([\d,.]+)", "high": r"H:\s*([\d,.]+)",
        "low": r"L:\s*([\d,.]+)", "close": r"C:\s*([\d,.]+)",
        "volume": r"\bV:\s*([\d,.]+[KkMm]?)",
        "cumulative_delta": r"(?:Cumulative\s*)?Delta[:\s]+([-+]?[\d,.]+[KkMm]?)",
    }
    for field, pattern in fallbacks.items():
        if result[field] is None:
            result[field] = text_value(text, pattern)

    if result["cumulative_delta"] is None:
        buy, sell = result["buy_volume"], result["sell_volume"]
        if buy is not None and sell is not None:
            result["cumulative_delta"] = buy - sell
    if result["close"] is None and result["cumulative_delta"] is None:
        result["error"] = "No usable GoCharting data; verify login and contract"
    return result


def collect_batch(driver, entries):
    """Load a batch concurrently in tabs, then extract each result."""
    root_handle = driver.current_window_handle
    handles = {}
    snapshots = {}
    driver.get_log("performance")

    for ticker, _, _ in entries:
        before = set(driver.window_handles)
        url = f"https://gocharting.com/terminal?ticker=NSE:OPTIONS:{ticker}"
        driver.execute_script("window.open(arguments[0], '_blank');", url)
        deadline = time.time() + 3
        while time.time() < deadline:
            created = set(driver.window_handles) - before
            if created:
                handles[ticker] = created.pop()
                break
            time.sleep(0.1)

    time.sleep(5.0)  # Increased for headless mode WebSocket connections
    for ticker, _, _ in entries:
        handle = handles.get(ticker)
        if not handle:
            continue
        try:
            driver.switch_to.window(handle)
            ActionChains(driver).key_down(Keys.ALT).send_keys("d").key_up(Keys.ALT).perform()
        except Exception:
            pass
    
    # Additional wait after triggering delta on all tabs
    time.sleep(1.5)

    pending = {ticker for ticker, _, _ in entries if ticker in handles}
    deadline = time.time() + FETCH_TIMEOUT
    while pending and time.time() < deadline:
        logs = driver.get_log("performance")
        for ticker in list(pending):
            snapshot = extract_snapshot(logs, ticker)
            if snapshot is not None:
                snapshots[ticker] = snapshot
                pending.remove(ticker)
        if pending:
            time.sleep(0.3)

    results = []
    for ticker, strike, option_type in entries:
        handle = handles.get(ticker)
        if not handle:
            item = _empty_result(ticker, strike, option_type)
            item["error"] = "Chrome tab could not be opened"
            results.append(item)
            continue
        try:
            driver.switch_to.window(handle)
            results.append(_fill_result(
                driver, ticker, strike, option_type, snapshots.get(ticker)
            ))
        except Exception as exc:
            item = _empty_result(ticker, strike, option_type)
            item["error"] = str(exc)[:250]
            results.append(item)

    for handle in handles.values():
        try:
            driver.switch_to.window(handle)
            driver.close()
        except Exception:
            pass
    driver.switch_to.window(root_handle)
    return results
