import os
import re
import json
import requests
from dotenv import load_dotenv

load_dotenv(override=False)

RIOT_API_KEY = os.environ.get("RIOT_API_KEY")

REGIONS = {
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

def get_puuid(username, tag, region="euw"):
    regional = REGIONS.get(region, REGIONS["euw"])["regional"]
    url = f"https://{regional}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{username}/{tag}"
    r = requests.get(url, headers={"X-Riot-Token": RIOT_API_KEY})
    if r.status_code == 200:
        return r.json().get("puuid")
    return None

def get_headers():
    return {"X-Riot-Token": RIOT_API_KEY}