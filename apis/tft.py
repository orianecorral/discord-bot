import requests
from datetime import datetime, timedelta
from apis.riot_base import REGIONS, safe_json, get_headers

def get_tft_rank(puuid, region="euw"):
    platform = REGIONS.get(region, REGIONS["euw"])["platform"]
    url = f"https://{platform}.api.riotgames.com/tft/league/v1/entries/by-puuid/{puuid}"
    r = requests.get(url, headers=get_headers())
    if r.status_code != 200:
        return {"tier": "UNRANKED", "division": "", "lp": 0}

    data = r.json()
    if not data:
        return {"tier": "UNRANKED", "division": "", "lp": 0}

    entry = data[0]
    return {
        "tier": entry.get("tier", "UNRANKED"),
        "division": entry.get("rank", ""),
        "lp": entry.get("leaguePoints", 0),
        "wins": entry.get("wins", 0),
        "losses": entry.get("losses", 0),
        "hot_streak": entry.get("hotStreak", False),
    }

def get_tft_matches(puuid, region="euw", days=7):
    regional = REGIONS.get(region, REGIONS["euw"])["regional"]
    start_time = int((datetime.now() - timedelta(days=days)).timestamp())

    url = f"https://{regional}.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids"
    params = {"start": 0, "count": 20, "startTime": start_time}
    r = requests.get(url, headers=get_headers(), params=params)
    if r.status_code != 200:
        return []

    match_ids = r.json()
    matches = []

    for match_id in match_ids:
        url = f"https://{regional}.api.riotgames.com/tft/match/v1/matches/{match_id}"
        r = requests.get(url, headers=get_headers())
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