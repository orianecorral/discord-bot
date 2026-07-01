import os
import requests
from datetime import datetime, timedelta
from apis.riot_base import REGIONS, safe_json
from dotenv import load_dotenv

load_dotenv(override=False)

TFT_API_KEY = os.environ.get("TFT_API_KEY") or os.environ.get("RIOT_API_KEY")

def get_tft_headers():
    return {"X-Riot-Token": TFT_API_KEY}

def get_tft_rank(puuid, region="euw"):
    platform = REGIONS.get(region, REGIONS["euw"])["platform"]

    # Cherche d'abord dans les hautes elos
    high_elo_endpoints = [
        f"https://{platform}.api.riotgames.com/tft/league/v1/challenger",
        f"https://{platform}.api.riotgames.com/tft/league/v1/grandmaster",
        f"https://{platform}.api.riotgames.com/tft/league/v1/master",
    ]

    for url in high_elo_endpoints:
        r = requests.get(url, headers=get_tft_headers())
        if r.status_code == 200:
            entries = r.json().get("entries", [])
            player = next((e for e in entries if e.get("puuid") == puuid), None)
            if player:
                tier = url.split("/")[-1].upper()
                return {
                    "tier": tier,
                    "division": "I",
                    "lp": player.get("leaguePoints", 0),
                    "wins": player.get("wins", 0),
                    "losses": player.get("losses", 0),
                    "hot_streak": player.get("hotStreak", False),
                }

    # Cherche dans les tiers normaux
    tiers = ["DIAMOND", "EMERALD", "PLATINUM", "GOLD", "SILVER", "BRONZE", "IRON"]
    divisions = ["I", "II", "III", "IV"]

    for tier in tiers:
        for division in divisions:
            url = f"https://{platform}.api.riotgames.com/tft/league/v1/entries/{tier}/{division}"
            params = {"page": 1}
            r = requests.get(url, headers=get_tft_headers(), params=params)
            if r.status_code != 200:
                continue
            entries = r.json()
            player = next((e for e in entries if e.get("puuid") == puuid), None)
            if player:
                return {
                    "tier": tier,
                    "division": division,
                    "lp": player.get("leaguePoints", 0),
                    "wins": player.get("wins", 0),
                    "losses": player.get("losses", 0),
                    "hot_streak": player.get("hotStreak", False),
                }

    return {"tier": "UNRANKED", "division": "", "lp": 0}

def get_tft_matches(puuid, region="euw", days=7):
    regional = REGIONS.get(region, REGIONS["euw"])["regional"]
    start_time = int((datetime.now() - timedelta(days=days)).timestamp())

    url = f"https://{regional}.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids"
    params = {"start": 0, "count": 20, "startTime": start_time}
    r = requests.get(url, headers=get_tft_headers(), params=params)
    if r.status_code != 200:
        return []

    match_ids = r.json()
    matches = []

    for match_id in match_ids:
        url = f"https://{regional}.api.riotgames.com/tft/match/v1/matches/{match_id}"
        r = requests.get(url, headers=get_tft_headers())
        if r.status_code != 200:
            continue
        data = safe_json(r)
        if not data:
            continue

        participants = data.get("info", {}).get("participants", [])
        player = next((p for p in participants if p.get("puuid") == puuid), None)
        if not player:
            continue

        matches.append({
            "placement": player.get("placement"),
            "level": player.get("level"),
            "gold_left": player.get("gold_left"),
            "last_round": player.get("last_round"),
            "augments": player.get("augments", []),
            "timestamp": data.get("info", {}).get("game_datetime"),
        })

    return matches

def get_tft_stats(puuid, region="euw", days=7):
    matches = get_tft_matches(puuid, region, days)
    rank = get_tft_rank(puuid, region)

    if not matches:
        return {"rank": rank, "matches": [], "summary": None}

    placements = [m["placement"] for m in matches]
    avg_placement = round(sum(placements) / len(placements), 2)
    top4 = sum(1 for p in placements if p <= 4)
    top4_rate = round(top4 / len(placements) * 100, 1)
    wins = sum(1 for p in placements if p == 1)
    best_placement = min(placements)
    worst_placement = max(placements)

    return {
        "rank": rank,
        "matches": matches,
        "summary": {
            "games": len(matches),
            "avg_placement": avg_placement,
            "top4_rate": top4_rate,
            "wins": wins,
            "best_placement": best_placement,
            "worst_placement": worst_placement,
        }
    }