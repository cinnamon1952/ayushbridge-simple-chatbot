import os
import sys
import time
from typing import Dict, List, Optional, Set

import requests
import pandas as pd
from urllib.parse import urljoin
from dataclasses import dataclass
from dotenv import load_dotenv


API_TOKEN_URL = "https://icdaccessmanagement.who.int/connect/token"
API_BASE_RELEASE = "https://id.who.int/icd/release/11/2025-01/tm2"
API_ROOT_URL = None  # will be discovered
# Alternative root for traversal (entity endpoints)
ACCEPT_JSON = "application/json"
ACCEPT_LANGUAGE = "en"

REQUEST_TIMEOUT = 30
MAX_RETRIES = 5
SLEEP_BETWEEN = 0.5
OUTPUT_CSV = "icd11_tm2_2025-01.csv"


@dataclass
class Entity:
    code: str
    title: str
    definition: str


class ICD11Client:
    def __init__(self, client_id: str, client_secret: str, language: str = ACCEPT_LANGUAGE):
        self.client_id = client_id
        self.client_secret = client_secret
        self.language = language
        self.session = requests.Session()
        self.access_token: Optional[str] = None

    def authenticate(self) -> None:
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "icdapi_access",
            "grant_type": "client_credentials",
        }
        for attempt in range(MAX_RETRIES):
            try:
                resp = self.session.post(API_TOKEN_URL, data=data, timeout=REQUEST_TIMEOUT)
                resp.raise_for_status()
                self.access_token = resp.json().get("access_token")
                if not self.access_token:
                    raise RuntimeError("No access_token in token response")
                return
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                time.sleep(1.0 + attempt * 0.5)

    def _headers(self) -> Dict[str, str]:
        if not self.access_token:
            raise RuntimeError("Not authenticated")
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": ACCEPT_JSON,
            "Accept-Language": self.language,
            "API-Version": "v2",
        }

    def get_json(self, url: str) -> Dict:
        for attempt in range(MAX_RETRIES):
            try:
                r = self.session.get(url, headers=self._headers(), timeout=REQUEST_TIMEOUT)
                if r.status_code == 429:
                    time.sleep(2.0 + attempt)
                    continue
                r.raise_for_status()
                return r.json()
            except Exception:
                if attempt == MAX_RETRIES - 1:
                    raise
                time.sleep(1.0 + attempt * 0.5)
        raise RuntimeError("Failed to GET after retries")

    def try_get_json(self, url: str) -> Optional[Dict]:
        try:
            r = self.session.get(url, headers=self._headers(), timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                return r.json()
            return None
        except Exception:
            return None


def collect_entities(client: ICD11Client, root_url: str) -> List[Entity]:
    results: List[Entity] = []
    visited: Set[str] = set()

    def visit(url: str) -> None:
        if url in visited:
            return
        visited.add(url)
        data = client.get_json(url)
        code = data.get("code") or ""
        title = ""
        definition = ""

        title_obj = data.get("title") or {}
        if isinstance(title_obj, dict):
            title = title_obj.get("value") or ""
        elif isinstance(title_obj, str):
            title = title_obj

        def_obj = data.get("definition") or {}
        if isinstance(def_obj, dict):
            definition = def_obj.get("value") or ""
        elif isinstance(def_obj, str):
            definition = def_obj

        if code or title or definition:
            results.append(Entity(code=code, title=title, definition=definition))

        # Traverse children
        children = data.get("child") or []
        for child in children:
            child_url = child.get("@id") or child.get("id")
            if child_url:
                visit(child_url)

    visit(root_url)
    return results


def discover_root_url(client: ICD11Client) -> str:
    candidates = [
        f"{API_BASE_RELEASE}/root",
        f"{API_BASE_RELEASE}/roots",
        f"{API_BASE_RELEASE}/tree/roots",
        f"{API_BASE_RELEASE}/linearization/root",
        f"{API_BASE_RELEASE}?flat=1",
    ]
    for url in candidates:
        data = client.try_get_json(url)
        if not data:
            continue
        # Accept both object and array forms
        if isinstance(data, dict) and ("child" in data or "title" in data or "code" in data):
            return url
        if isinstance(data, list) and len(data) > 0:
            # If list of roots, return the first element's @id if present
            first = data[0]
            if isinstance(first, dict) and first.get("@id"):
                return first["@id"]
    raise RuntimeError("Could not discover TM2 root endpoint. Please verify API endpoints for TM2.")


def main() -> int:
    load_dotenv()
    client_id = os.getenv("ICD_API_CLIENT_ID")
    client_secret = os.getenv("ICD_API_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("Missing ICD_API_CLIENT_ID or ICD_API_CLIENT_SECRET in environment.")
        print("Please provide credentials and rerun.")
        return 2

    client = ICD11Client(client_id=client_id, client_secret=client_secret, language=ACCEPT_LANGUAGE)
    client.authenticate()

    root_url = discover_root_url(client)
    entities = collect_entities(client, root_url)

    df = pd.DataFrame({
        "icd11_code": [e.code for e in entities],
        "disease_name": [e.title for e in entities],
        "disease_description": [e.definition for e in entities],
    })

    # Deduplicate by code + name to be safe
    if not df.empty:
        df.drop_duplicates(subset=["icd11_code", "disease_name"], inplace=True)

    df.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved {len(df)} rows to {OUTPUT_CSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
