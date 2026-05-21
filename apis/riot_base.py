import os
import re
import json
import requests
from dotenv import load_dotenv

load_dotenv(override=False)

RIOT_API_KEY = os.environ.get("RIOT_API_KEY")
TFT_API_KEY = os.environ.get("TFT_API_KEY") or RIOT_API_KEY

REGIONS = {
    "eu": {"platform": "euw1", "regional": "europe"},
    "euw": {"platform": "euw1", "regional": "europe"},
    "eune": {"platform": "eun1", "regional": "europe"},
    "na": {"platform": "na1", "regional": "americas"},
    "kr": {"platform": "kr", "regional": "asia"},
}

def safe_json(response):
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', response.text)
    try:
        return json.loads(text)
    except Exception:
        return None

def get_headers():
    return {"X-Riot-Token": RIOT_API_KEY}

def get_tft_base_headers():
    return {"X-Riot-Token": TFT_API_KEY}

def get_puuid(username, tag, region="euw", use_tft_key=False):
    regional = REGIONS.get(region, REGIONS["euw"])["regional"]
    url = f"https://{regional}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{username}/{tag}"
    key = TFT_API_KEY if use_tft_key else RIOT_API_KEY
    r = requests.get(url, headers={"X-Riot-Token": key})
    if r.status_code == 200:
        return r.json().get("puuid")
    return None