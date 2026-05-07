import os
import requests
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

RIOT_API_KEY = os.getenv("RIOT_API_KEY")

REGIONS = {
    "euw": {"platform": "euw1", "regional": "europe"},
    "eune": {"platform": "eun1", "regional": "europe"},
    "na": {"platform": "na1", "regional": "americas"},
    "kr": {"platform": "kr", "regional": "asia"},
}

def safe_json(response):
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', response.text)
    try:
        return __import__('json').loads(text)
    except Exception:
        return None

def get_puuid(username, tag, region="euw"):
    regional = REGIONS.get(region, REGIONS["euw"])["regional"]
    url = f"https://{regional}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{username}/{tag}"
    r = requests.get(url, headers={"X-Riot-Token": RIOT_API_KEY})
    if r.status_code == 200:
        return r.json().get("puuid")
    return None

# ====================
# LEAGUE OF LEGENDS
# ====================

def get_lol_rank(puuid, region="euw"):
    platform = REGIONS.get(region, REGIONS["euw"])["platform"]
    
    # Nouvel endpoint direct par PUUID
    url = f"https://{platform}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
    r = requests.get(url, headers={"X-Riot-Token": RIOT_API_KEY})
    
    if r.status_code != 200:
        return None
    
    # Récupérer le level séparément
    url_summoner = f"https://{platform}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    r_summoner = requests.get(url_summoner, headers={"X-Riot-Token": RIOT_API_KEY})
    summoner_level = r_summoner.json().get("summonerLevel") if r_summoner.status_code == 200 else None

    data = r.json()
    result = {"level": summoner_level, "solo": None, "flex": None}

    for entry in data:
        queue = entry.get("queueType")
        info = {
            "tier": entry.get("tier", "UNRANKED"),
            "division": entry.get("rank", ""),
            "lp": entry.get("leaguePoints", 0),
            "wins": entry.get("wins", 0),
            "losses": entry.get("losses", 0),
        }
        if queue == "RANKED_SOLO_5x5":
            result["solo"] = info
        elif queue == "RANKED_FLEX_SR":
            result["flex"] = info

    return result

def get_lol_matches(puuid, region="euw", days=7):
    regional = REGIONS.get(region, REGIONS["euw"])["regional"]
    start_time = int((datetime.now() - timedelta(days=days)).timestamp())
    
    url = f"https://{regional}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
    params = {"start": 0, "count": 20, "startTime": start_time, "queue": 420}
    r = requests.get(url, headers={"X-Riot-Token": RIOT_API_KEY}, params=params)
    if r.status_code != 200:
        return []
    
    match_ids = r.json()
    matches = []
    
    for match_id in match_ids:
        url = f"https://{regional}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        r = requests.get(url, headers={"X-Riot-Token": RIOT_API_KEY})
        if r.status_code != 200:
            continue
        data = safe_json(r)
        if not data:
            continue
        
        participants = data.get("info", {}).get("participants", [])
        player = next((p for p in participants if p.get("puuid") == puuid), None)
        if not player:
            continue
        
        deaths = player.get("deaths", 1) or 1
        matches.append({
            "champion": player.get("championName"),
            "win": player.get("win"),
            "kills": player.get("kills", 0),
            "deaths": player.get("deaths", 0),
            "assists": player.get("assists", 0),
            "kda": round((player.get("kills", 0) + player.get("assists", 0)) / deaths, 2),
            "timestamp": data.get("info", {}).get("gameStartTimestamp"),
        })
    
    return matches

def get_lol_stats(puuid, region="euw", days=7):
    matches = get_lol_matches(puuid, region, days)
    rank = get_lol_rank(puuid, region)
    
    if not matches:
        return {"rank": rank, "matches": [], "summary": None}
    
    wins = sum(1 for m in matches if m["win"])
    losses = len(matches) - wins
    winrate = round(wins / len(matches) * 100, 1)
    avg_kda = round(sum(m["kda"] for m in matches) / len(matches), 2)
    
    champion_count = {}
    for m in matches:
        champ = m["champion"]
        champion_count[champ] = champion_count.get(champ, 0) + 1
    most_played = max(champion_count, key=champion_count.get)
    
    return {
        "rank": rank,
        "matches": matches,
        "summary": {
            "wins": wins,
            "losses": losses,
            "winrate": winrate,
            "avg_kda": avg_kda,
            "most_played": most_played,
            "most_played_count": champion_count[most_played],
        }
    }

# ====================
# TEAMFIGHT TACTICS
# ====================

def get_tft_rank(puuid, region="euw"):
    platform = REGIONS.get(region, REGIONS["euw"])["platform"]

    url = f"https://{platform}.api.riotgames.com/tft/league/v1/entries/by-puuid/{puuid}"
    r = requests.get(url, headers={"X-Riot-Token": RIOT_API_KEY})
    print("TFT Rank status:", r.status_code)
    print("TFT Rank data:", r.json())

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
    }
    

def get_tft_matches(puuid, region="euw", days=7):
    regional = REGIONS.get(region, REGIONS["euw"])["regional"]
    start_time = int((datetime.now() - timedelta(days=days)).timestamp())
    
    url = f"https://{regional}.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids"
    params = {"start": 0, "count": 20, "startTime": start_time}
    r = requests.get(url, headers={"X-Riot-Token": RIOT_API_KEY}, params=params)
    if r.status_code != 200:
        return []
    
    match_ids = r.json()
    matches = []
    
    for match_id in match_ids:
        url = f"https://{regional}.api.riotgames.com/tft/match/v1/matches/{match_id}"
        r = requests.get(url, headers={"X-Riot-Token": RIOT_API_KEY})
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
    
    return {
        "rank": rank,
        "matches": matches,
        "summary": {
            "games": len(matches),
            "avg_placement": avg_placement,
            "top4_rate": top4_rate,
        }
    }