import json
import os
from pathlib import Path

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

load_dotenv()
profile = Path(os.getenv("BNF_PROFILE_DIR", "./.chrome-profile")).resolve()
session_file = Path(os.getenv("BNF_SESSION_FILE", "./data/session.json")).resolve()
profile.mkdir(parents=True, exist_ok=True)
session_file.parent.mkdir(parents=True, exist_ok=True)

options = Options()
options.add_argument(f"--user-data-dir={profile}")
options.add_argument("--window-size=1440,900")
options.add_argument("--disable-blink-features=AutomationControlled")

driver = webdriver.Chrome(options=options)
try:
    driver.get("https://gocharting.com/")
    print("Sign in to GoCharting in Chrome, then press Enter here.")
    input()
    session = {
        "cookies": driver.get_cookies(),
        "local_storage": driver.execute_script("return {...localStorage};"),
        "session_storage": driver.execute_script("return {...sessionStorage};"),
    }
    session_file.write_text(json.dumps(session, indent=2), encoding="utf-8")
    print(f"Profile saved in {profile}")
    print(f"Portable session saved in {session_file}")
finally:
    driver.quit()
