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
        "class": data.get("character_class", {}).get("name"),
        "spec": data.get("active_spec", {}).get("name"),
        "level": data.get("level"),
        "item_level": data.get("average_item_level"),
        "equipped_item_level": data.get("equipped_item_level"),
        "faction": data.get("faction", {}).get("name"),
        "race": data.get("race", {}).get("name"),
        "guild": data.get("guild", {}).get("name"),
    }

def get_mythic_plus(character, realm, region="eu"):
    token = get_access_token(region)
    if not token:
        return None

    cfg = REGIONS.get(region, REGIONS["eu"])
    realm_slug = realm.lower().replace(" ", "-").replace("'", "")
    char_slug = character.lower()

    url = f"{cfg['api']}/profile/wow/character/{realm_slug}/{char_slug}/mythic-keystone-profile"
    params = {
        "namespace": cfg["namespace_profile"],
        "locale": cfg["locale"],
    }
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, params=params, headers=headers)
    if r.status_code != 200:
        return None

    data = r.json()
    rating = data.get("current_mythic_rating", {})
    runs = data.get("current_period", {}).get("best_runs", [])

    best_runs = []
    for run in runs[:5]:
        best_runs.append({
            "dungeon": run.get("dungeon", {}).get("name", "Unknown"),
            "level": run.get("keystone_level", 0),
            "completed": run.get("completed_timestamp"),
            "duration": round(run.get("duration", 0) / 60000, 1),
            "upgrades": run.get("keystone_upgrades", 0),
        })

    return {
        "score": round(rating.get("rating", 0), 1),
        "best_runs": best_runs,
    }

def get_raiderio_stats(character, realm, region="eu"):
    url = "https://raider.io/api/v1/characters/profile"
    params = {
        "region": region,
        "realm": realm,
        "name": character,
        "fields": "mythic_plus_scores_by_season:current,mythic_plus_recent_runs,raid_progression",
    }
    r = requests.get(url, params=params)
    if r.status_code != 200:
        return None

    data = r.json()
    scores = data.get("mythic_plus_scores_by_season", [{}])
    score = scores[0].get("scores", {}).get("all", 0) if scores else 0

    recent_runs = data.get("mythic_plus_recent_runs", [])[:3]
    runs = []
    for run in recent_runs:
        runs.append({
            "dungeon": run.get("dungeon"),
            "level": run.get("mythic_level"),
            "score": run.get("score"),
            "upgrades": run.get("num_keystone_upgrades"),
            "affixes": [a.get("name") for a in run.get("affixes", [])],
        })

    raid = data.get("raid_progression", {})
    latest_raid = None
    if raid:
        latest_raid_key = list(raid.keys())[-1]
        latest = raid[latest_raid_key]
        latest_raid = {
            "name": latest_raid_key.replace("-", " ").title(),
            "normal": latest.get("normal_bosses_killed", 0),
            "heroic": latest.get("heroic_bosses_killed", 0),
            "mythic": latest.get("mythic_bosses_killed", 0),
            "total": latest.get("total_bosses", 0),
        }

    return {
        "rio_score": score,
        "recent_runs": runs,
        "latest_raid": latest_raid,
    }

def get_wow_stats(character, realm, region="eu"):
    if not BLIZZARD_CLIENT_ID or not BLIZZARD_CLIENT_SECRET:
        return None

    profile = get_character_profile(character, realm, region)
    mythic = get_mythic_plus(character, realm, region)
    raiderio = get_raiderio_stats(character, realm, region)

    return {
        "profile": profile,
        "mythic_plus": mythic,
        "raiderio": raiderio,
    }