import os
import time
import requests
from dotenv import load_dotenv

load_dotenv(override=False)

BLIZZARD_CLIENT_ID = os.environ.get("BLIZZARD_CLIENT_ID")
BLIZZARD_CLIENT_SECRET = os.environ.get("BLIZZARD_CLIENT_SECRET")

REGIONS = {
    "eu": {
        "oauth": "https://oauth.battle.net",
        "api": "https://eu.api.blizzard.com",
        "namespace_profile": "profile-eu",
        "namespace_static": "static-eu",
        "locale": "en_GB",
    },
    "us": {
        "oauth": "https://oauth.battle.net",
        "api": "https://us.api.blizzard.com",
        "namespace_profile": "profile-us",
        "namespace_static": "static-us",
        "locale": "en_US",
    },
    "kr": {
        "oauth": "https://oauth.battle.net",
        "api": "https://kr.api.blizzard.com",
        "namespace_profile": "profile-kr",
        "namespace_static": "static-kr",
        "locale": "ko_KR",
    },
}

_token_cache = {"token": None, "expires_at": 0}

def get_access_token(region="eu"):
    if _token_cache["token"] and time.time() < _token_cache["expires_at"]:
        return _token_cache["token"]

    oauth_url = f"{REGIONS[region]['oauth']}/token"
    r = requests.post(
        oauth_url,
        data={"grant_type": "client_credentials"},
        auth=(BLIZZARD_CLIENT_ID, BLIZZARD_CLIENT_SECRET),
    )
    if r.status_code != 200:
        return None

    data = r.json()
    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = time.time() + data["expires_in"] - 60
    return _token_cache["token"]

def get_character_profile(character, realm, region="eu"):
    token = get_access_token(region)
    if not token:
        return None

    cfg = REGIONS.get(region, REGIONS["eu"])
    realm_slug = realm.lower().replace(" ", "-").replace("'", "")
    char_slug = character.lower()

    url = f"{cfg['api']}/profile/wow/character/{realm_slug}/{char_slug}"
    params = {
        "namespace": cfg["namespace_profile"],
        "locale": cfg["locale"],
    }
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, params=params, headers=headers)
    if r.status_code != 200:
        return None

    data = r.json()
    return {
        "name": data.get("name"),
        "realm": data.get("realm", {}).get("name"),