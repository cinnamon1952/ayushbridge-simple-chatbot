import os
import sys
import asyncio
from typing import List, Tuple
import csv

import aiohttp
import requests
from dotenv import load_dotenv
from tqdm import tqdm

TOKEN_URL = "https://icdaccessmanagement.who.int/connect/token"
CODEINFO_BASE = "https://id.who.int/icd/release/11/2025-01/mms/codeinfo/"
SEARCH_URL_MMS = "https://id.who.int/icd/release/11/2025-01/mms/search"
SEARCH_URL_GENERIC = "https://id.who.int/icd/release/11/2025-01/search"
ENTITY_GENERIC_BASE = "https://id.who.int/icd/entity/"

CONCURRENCY = 20
TIMEOUT = aiohttp.ClientTimeout(total=60)
OUTPUT_CSV = "icd11_bulk_codes.csv"
CODES_FILE = "codes.txt"  # one code per line


def get_token() -> str:
    load_dotenv()
    client_id = os.getenv("ICD_API_CLIENT_ID")
    client_secret = os.getenv("ICD_API_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("Missing ICD_API_CLIENT_ID or ICD_API_CLIENT_SECRET")
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "icdapi_access",
        "grant_type": "client_credentials",
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = requests.post(TOKEN_URL, data=data, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def build_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Accept-Language": "en",
        "API-Version": "v2",
    }


async def fetch_json(session: aiohttp.ClientSession, url: str, params: dict | None = None) -> dict | None:
    for _ in range(3):
        try:
            async with session.get(url, params=params) as resp:
                if resp.status == 429:
                    await asyncio.sleep(1.0)
                    continue
                if resp.status != 200:
                    return None
                return await resp.json()
        except Exception:
            await asyncio.sleep(0.3)
    return None


def _extract_text(obj) -> str:
    if isinstance(obj, dict):
        return obj.get("value") or obj.get("@value") or ""
    if isinstance(obj, list) and obj:
        first = obj[0]
        if isinstance(first, dict):
            return first.get("value") or first.get("@value") or ""
        if isinstance(first, str):
            return first
    if isinstance(obj, str):
        return obj
    return ""


def extract_title(data: dict) -> str:
    t = data.get("title")
    txt = _extract_text(t)
    if txt:
        return txt
    # fallbacks
    bt = _extract_text(data.get("browserTitle"))
    if bt:
        return bt
    fsn = _extract_text(data.get("fullySpecifiedName"))
    if fsn:
        return fsn
    # sometimes synonyms carry a sensible label
    syn = _extract_text(data.get("synonym")) or _extract_text(data.get("synonyms"))
    if syn:
        return syn
    return ""


def extract_definition(data: dict) -> str:
    d = data.get("definition")
    txt = _extract_text(d)
    if txt:
        return txt
    # fallback to longDefinition
    ld = _extract_text(data.get("longDefinition"))
    if ld:
        return ld
    # try inclusion/exclusion text as a last resort
    inc = _extract_text(data.get("inclusion")) or _extract_text(data.get("includes"))
    if inc:
        return inc
    return ""


async def search_entity_id(session: aiohttp.ClientSession, code: str) -> str | None:
    # Try MMS search (sf=code), then generic search
    for url, params in [
        (SEARCH_URL_MMS, {"q": code, "sf": "code"}),
        (SEARCH_URL_GENERIC, {"q": code, "sf": "code", "linearization": "mms"}),
        (SEARCH_URL_MMS, {"q": code, "sf": "all"}),
        (SEARCH_URL_GENERIC, {"q": code, "sf": "all", "linearization": "mms"}),
    ]:
        data = await fetch_json(session, url, params)
        if not data or not isinstance(data, dict):
            continue
        dest = data.get("destinationEntities")
        if isinstance(dest, list) and dest:
            first = dest[0]
            if isinstance(first, dict) and first.get("id"):
                return first["id"]
        res = data.get("results")
        if isinstance(res, list) and res:
            first = res[0]
            if isinstance(first, dict) and first.get("id"):
                return first["id"]
    return None


def to_generic_entity_url(release_entity_url: str) -> str | None:
    # Convert .../release/11/2025-01/mms/<id> -> .../entity/<id>
    try:
        parts = release_entity_url.rstrip("/").split("/")
        last = parts[-1]
        if last.isdigit():
            return ENTITY_GENERIC_BASE + last
    except Exception:
        pass
    return None


async def process_code(session: aiohttp.ClientSession, code: str) -> Tuple[str, str, str]:
    code = code.strip()
    if not code:
        return code, "", ""
    # 1) codeinfo -> stemId
    codeinfo_url = CODEINFO_BASE + code
    ci = await fetch_json(session, codeinfo_url)
    entity_url = None
    if ci and isinstance(ci, dict):
        entity_url = ci.get("stemId")
    # 1b) fallback to search
    if not entity_url:
        entity_url = await search_entity_id(session, code)
    if not entity_url:
        return code, "", ""
    # 2) entity details (release)
    # request expanded fields for better coverage
    expand_params = {"expand": "title,definition,longDefinition,fullySpecifiedName,browserTitle"}
    ent = await fetch_json(session, entity_url, expand_params)
    title = extract_title(ent) if ent else ""
    definition = extract_definition(ent) if ent else ""
    if (not title or not definition):
        # 2b) fallback to generic entity endpoint
        gen_url = to_generic_entity_url(entity_url)
        if gen_url:
            ent2 = await fetch_json(session, gen_url, expand_params)
            if ent2:
                if not title:
                    title = extract_title(ent2)
                if not definition:
                    definition = extract_definition(ent2)
    if (not title or not definition):
        # 2c) try flat view
        ent3 = await fetch_json(session, entity_url, {"flat": "1"})
        if ent3:
            if not title:
                title = extract_title(ent3)
            if not definition:
                definition = extract_definition(ent3)
    return code, title, definition


async def main_async(codes: List[str], token: str) -> List[Tuple[str, str, str]]:
    headers = build_headers(token)
    connector = aiohttp.TCPConnector(limit_per_host=CONCURRENCY, ssl=False)
    async with aiohttp.ClientSession(headers=headers, timeout=TIMEOUT, connector=connector) as session:
        sem = asyncio.Semaphore(CONCURRENCY)

        async def bounded(code: str):
            async with sem:
                return await process_code(session, code)

        tasks = [asyncio.create_task(bounded(c)) for c in codes]
        results: List[Tuple[str, str, str]] = []
        with tqdm(total=len(tasks), desc="Fetching", unit="code") as pbar:
            for coro in asyncio.as_completed(tasks):
                res = await coro
                results.append(res)
                pbar.update(1)
        return results


def read_codes(path: str) -> List[str]:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Codes file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def write_csv(rows: List[Tuple[str, str, str]], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["icd11_code", "disease_name", "disease_description"])
        for code, title, definition in rows:
            w.writerow([code, title, definition])


def write_missing(rows: List[Tuple[str, str, str]], path: str) -> None:
    missing = [(c, t, d) for c, t, d in rows if not t or not d]
    if not missing:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["icd11_code", "disease_name", "disease_description"])
        for row in missing:
            w.writerow(list(row))


if __name__ == "__main__":
    token = get_token()
    print("✅ Access token received")
    codes = read_codes(CODES_FILE)
    print(f"Processing {len(codes)} codes asynchronously...")
    results = asyncio.run(main_async(codes, token))
    write_csv(results, OUTPUT_CSV)
    write_missing(results, OUTPUT_CSV.replace(".csv", "_missing.csv"))
    print(f"Saved {len(results)} rows to {OUTPUT_CSV}")
