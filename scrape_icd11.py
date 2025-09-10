import os
import time
import sys
import glob
import shutil
from typing import List, Optional

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
import requests


ICD11_URL = "https://icd.who.int/browse/2025-01/tm2/en"
OUTPUT_CSV = "icd11_tm2_2025-01.csv"
DOWNLOAD_DIR = os.path.abspath(os.path.join(os.getcwd(), "downloads"))
TIMEOUT_SECONDS = 60


def ensure_dir(path: str) -> None:
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)


def get_latest_file(directory: str, patterns: List[str]) -> Optional[str]:
    latest_path = None
    latest_mtime = -1.0
    for pattern in patterns:
        for path in glob.glob(os.path.join(directory, pattern)):
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            if mtime > latest_mtime:
                latest_mtime = mtime
                latest_path = path
    return latest_path


def configure_chrome(download_dir: str) -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    options.add_experimental_option("prefs", prefs)
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def wait_for_download(download_dir: str, timeout: int = TIMEOUT_SECONDS) -> str:
    end_time = time.time() + timeout
    partial_extensions = (".crdownload", ".part", ".tmp")
    while time.time() < end_time:
        candidate = get_latest_file(download_dir, ["*.xlsx", "*.xls", "*.csv"])
        if candidate and not candidate.endswith(partial_extensions):
            return candidate
        time.sleep(1)
    raise TimeoutError("Timed out waiting for spreadsheet download to complete.")


def find_spreadsheet_href(driver: webdriver.Chrome) -> Optional[str]:
    # Try to find any anchor with .xlsx in href
    anchors = driver.find_elements(By.TAG_NAME, "a")
    hrefs = []
    for a in anchors:
        try:
            href = a.get_attribute("href")
        except Exception:
            href = None
        if href:
            hrefs.append(href)
    # prefer xlsx
    for href in hrefs:
        if ".xlsx" in href.lower():
            return href
    # fallback to any excel-related
    for href in hrefs:
        if "excel" in href.lower() or "spreadsheet" in href.lower():
            return href
    return None


def find_and_click_spreadsheet_link(driver: webdriver.Chrome) -> None:
    wait = WebDriverWait(driver, TIMEOUT_SECONDS)
    link_locators = [
        (By.PARTIAL_LINK_TEXT, "Spreadsheet"),
        (By.PARTIAL_LINK_TEXT, "Excel"),
        (By.CSS_SELECTOR, "a[href*='xlsx']"),
        (By.XPATH, "//a[contains(@href, '.xlsx')]")
    ]

    for by, selector in link_locators:
        try:
            elem = wait.until(EC.element_to_be_clickable((by, selector)))
            elem.click()
            return
        except Exception:
            continue

    # Try expanding downloads-like sections then retry
    possible_download_toggles = [
        (By.XPATH, "//*[contains(translate(text(),'DOWNLOADS','downloads'),'downloads')]")
    ]
    for by, selector in possible_download_toggles:
        try:
            toggle = wait.until(EC.element_to_be_clickable((by, selector)))
            toggle.click()
            time.sleep(1)
        except Exception:
            pass

    for by, selector in link_locators:
        try:
            elem = wait.until(EC.element_to_be_clickable((by, selector)))
            elem.click()
            return
        except Exception:
            continue

    # Last resort: try to navigate directly if we can find the href
    href = find_spreadsheet_href(driver)
    if href:
        driver.get(href)
        return

    raise RuntimeError("Could not find a spreadsheet download link on the page.")


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    column_map = {c.lower().strip(): c for c in df.columns}

    code_keys = [
        "icd-11 code", "icd11 code", "code", "icd code", "icd-11 code without dot", "postcoordination code"
    ]
    title_keys = [
        "title", "name", "disease name", "preferred term"
    ]
    desc_keys = [
        "definition", "description", "long definition"
    ]

    def pick(keys: List[str]) -> Optional[str]:
        for k in keys:
            if k in column_map:
                return column_map[k]
        for key in keys:
            for col_lower, orig in column_map.items():
                if key in col_lower:
                    return orig
        return None

    code_col = pick(code_keys)
    title_col = pick(title_keys)
    desc_col = pick(desc_keys)

    if not code_col or not title_col:
        raise ValueError(f"Could not locate required columns. Found: {list(df.columns)}")

    if desc_col and desc_col not in df.columns:
        desc_col = None

    out = pd.DataFrame()
    out["icd11_code"] = df[code_col].astype(str).str.strip()
    out["disease_name"] = df[title_col].astype(str).str.strip()
    if desc_col:
        out["disease_description"] = df[desc_col].astype(str).str.strip()
    else:
        out["disease_description"] = ""
    return out


def http_download(url: str, dest_path: str) -> None:
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)


def main() -> int:
    ensure_dir(DOWNLOAD_DIR)

    driver = configure_chrome(DOWNLOAD_DIR)
    try:
        driver.get(ICD11_URL)
        WebDriverWait(driver, TIMEOUT_SECONDS).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(3)

        # Try click-based download first; this also handles direct navigate if href is found
        try:
            find_and_click_spreadsheet_link(driver)
            downloaded_path = wait_for_download(DOWNLOAD_DIR, TIMEOUT_SECONDS * 2)
        except Exception:
            # Fallback: extract href and download via HTTP
            href = find_spreadsheet_href(driver)
            if not href:
                raise
            filename = os.path.basename(href.split("?")[0]) or "icd11_mms_2025-01.xlsx"
            dest = os.path.join(DOWNLOAD_DIR, filename)
            http_download(href, dest)
            downloaded_path = dest

    finally:
        try:
            driver.quit()
        except Exception:
            pass

    filename = os.path.basename(downloaded_path)
    local_path = os.path.abspath(os.path.join(os.getcwd(), filename))
    try:
        shutil.move(downloaded_path, local_path)
    except Exception:
        local_path = downloaded_path

    ext = os.path.splitext(local_path)[1].lower()
    if ext in (".xlsx", ".xls"):
        df = pd.read_excel(local_path)
    elif ext == ".csv":
        df = pd.read_csv(local_path)
    else:
        raise ValueError(f"Unsupported downloaded file type: {ext}")

    normalized = normalize_columns(df)
    normalized = normalized[normalized["icd11_code"].str.len() > 0]

    normalized.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved {len(normalized)} rows to {OUTPUT_CSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
