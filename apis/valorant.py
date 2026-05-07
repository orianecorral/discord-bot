import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

VALORANT_API_KEY = os.getenv("VALORANT_API_KEY")

REGIONS = {
    "eu": "eu",
    "na": "na",
    "ap": "ap",
    "kr": "kr",
}

def get_valorant_rank(username, tag, region="eu"):
    url = f"https://api.henrikdev.xyz/valorant/v1/mmr/{region}/{username}/{tag}"
    headers = {"Authorization": VALORANT_API_KEY}
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        return None
    
    data = r.json().get("data", {})
    return {
        "rank": data.get("currenttierpatched", "Unranked"),
        "rr": data.get("ranking_in_tier", 0),
        "elo": data.get("elo", 0),
    }

def get_valorant_matches(username, tag, region="eu", days=7):
    url = f"https://api.henrikdev.xyz/valorant/v2/matches/{region}/{username}/{tag}"
    headers = {"Authorization": VALORANT_API_KEY}
    params = {"filter": "competitive", "size": 20}
    
    r = requests.get(url, headers=headers, params=params)
    if r.status_code != 200:
        return []
    
    matches_data = r.json().get("data", [])
    cutoff = datetime.now() - timedelta(days=days)
    matches = []

    for match in matches_data:
        metadata = match.get("metadata", {})
        timestamp = metadata.get("game_start", 0)
        game_time = datetime.fromtimestamp(timestamp)
        
        if game_time < cutoff:
            continue

        players = match.get("players", {}).get("all_players", [])
        player = next(
            (p for p in players if
             p.get("name", "").lower() == username.lower() and
             p.get("tag", "").lower() == tag.lower()),
            None
        )
        if not player:
            continue

        stats = player.get("stats", {})
        kills = stats.get("kills", 0)
        deaths = stats.get("deaths", 1) or 1
        assists = stats.get("assists", 0)
        score = stats.get("score", 0)
        rounds = metadata.get("rounds_played", 1) or 1

        team = player.get("team", "").lower()
        teams = match.get("teams", {})
        won = teams.get(team, {}).get("has_won", False)

        matches.append({
            "agent": player.get("character", "Unknown"),
            "win": won,
            "kills": kills,
            "deaths": deaths,
            "assists": assists,
            "kda": round((kills + assists) / deaths, 2),
            "acs": round(score / rounds),
            "timestamp": timestamp,
        })

    return matches

def get_valorant_stats(username, tag, region="eu", days=7):
    rank = get_valorant_rank(username, tag, region)
    matches = get_valorant_matches(username, tag, region, days)

    if not matches:
        return {"rank": rank, "matches": [], "summary": None}

    wins = sum(1 for m in matches if m["win"])
    losses = len(matches) - wins
    winrate = round(wins / len(matches) * 100, 1)
    avg_kda = round(sum(m["kda"] for m in matches) / len(matches), 2)
    avg_acs = round(sum(m["acs"] for m in matches) / len(matches))

    agent_count = {}
    for m in matches:
        agent = m["agent"]
        agent_count[agent] = agent_count.get(agent, 0) + 1
    most_played = max(agent_count, key=agent_count.get)

    return {
        "rank": rank,
        "matches": matches,
        "summary": {
            "wins": wins,
            "losses": losses,
            "winrate": winrate,
            "avg_kda": avg_kda,
            "avg_acs": avg_acs,
            "most_played_agent": most_played,
            "most_played_count": agent_count[most_played],
        }
    }