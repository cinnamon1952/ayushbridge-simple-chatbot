import requests

# ==========================================
# CONFIG - Put your WHO API credentials here
# ==========================================
CLIENT_ID = "f18c275e-167f-49c3-81bb-fcfcc1e77344_ae1eaf94-1f4c-4a9f-8b4f-e7306b8e566b"
CLIENT_SECRET = "bvqtw5VYEF7kX/XkvyteXE/MEfQT0Slj0DZaUWIch9M="

TOKEN_URL = "https://icdaccessmanagement.who.int/connect/token"
SEARCH_URL_MMS = "https://id.who.int/icd/release/11/2025-01/mms/search"
SEARCH_URL_GENERIC = "https://id.who.int/icd/release/11/2025-01/search"
CODEINFO_BASE = "https://id.who.int/icd/release/11/2025-01/mms/codeinfo/"
ENTITY_URL = "https://id.who.int/icd/entity/"

# ==========================================
# Step 1: Get OAuth2 Access Token
# ==========================================

def get_token():
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "icdapi_access",
        "grant_type": "client_credentials",
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(TOKEN_URL, data=data, headers=headers)

    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception(f"Token request failed: {response.text}")


def auth_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Accept-Language": "en",
        "API-Version": "v2",
    }

# ==========================================
# Step 2: Resolve ICD-11 Code → Entity stemId (preferred over search)
# ==========================================

def resolve_code_to_entity(icd_code: str, token: str) -> str | None:
    headers = auth_headers(token)
    url = CODEINFO_BASE + icd_code
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        return None
    data = r.json()
    return data.get("stemId")

# ==========================================
# Step 3: Fetch ICD Entity Details
# ==========================================

def get_icd_details(entity_id, token):
    headers = auth_headers(token)
    response = requests.get(entity_id, headers=headers)

    if response.status_code == 200:
        data = response.json()
        title_val = ""
        title_obj = data.get("title")
        if isinstance(title_obj, dict):
            title_val = title_obj.get("value") or title_obj.get("@value") or ""
        elif isinstance(title_obj, str):
            title_val = title_obj

        def_val = ""
        def_obj = data.get("definition")
        if isinstance(def_obj, dict):
            def_val = def_obj.get("value") or def_obj.get("@value") or ""
        elif isinstance(def_obj, list) and def_obj:
            first = def_obj[0]
            if isinstance(first, dict):
                def_val = first.get("value") or first.get("@value") or ""

        return {
            "title": title_val or "No title",
            "definition": def_val or "No definition available",
        }
    else:
        raise Exception(f"Entity fetch failed: {response.text}")

# ==========================================
# Main Function
# ==========================================
if __name__ == "__main__":
    try:
        token = get_token()
        print("✅ Access token received")

        # Example lookups
        icd_code = "JB04"   # example code
        entity_id = resolve_code_to_entity(icd_code, token)

        if entity_id:
            details = get_icd_details(entity_id, token)
            print(f"\nICD-11 Code: {icd_code}")
            print(f"Title: {details['title']}")
            print(f"Definition: {details['definition']}")
        else:
            print(f"❌ Could not resolve code {icd_code} via codeinfo")

    except Exception as e:
        print("Error:", e)