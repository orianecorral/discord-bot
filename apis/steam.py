import os
import requests
from dotenv import load_dotenv

load_dotenv(override=False)

STEAM_API_KEY = os.environ.get("STEAM_API_KEY")
CS2_APP_ID = 730

def get_recently_played(steam_id):
    url = "https://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v0001/"
    params = {"key": STEAM_API_KEY, "steamid": steam_id, "format": "json"}
    r = requests.get(url, params=params)
    if r.status_code != 200:
        return None
    games = r.json().get("response", {}).get("games", [])
    return next((g for g in games if g.get("appid") == CS2_APP_ID), None)

def get_cs2_stats(steam_id):
    url = "https://api.steampowered.com/ISteamUserStats/GetUserStatsForGame/v0002/"
    params = {"appid": CS2_APP_ID, "key": STEAM_API_KEY, "steamid": steam_id, "format": "json"}
    r = requests.get(url, params=params)
    if r.status_code in (401, 403):
        return None, "private"
    if r.status_code != 200:
        return None, "error"
    stats_list = r.json().get("playerstats", {}).get("stats", [])
    stats = {s["name"]: s["value"] for s in stats_list}
    return stats, "ok"

def get_cs2_full_stats(steam_id):
    recent = get_recently_played(steam_id)
    stats, status = get_cs2_stats(steam_id)

    hours_2weeks = None
    played_this_week = False
    if recent:
        hours_2weeks = round(recent.get("playtime_2weeks", 0) / 60, 1)
        played_this_week = hours_2weeks > 0

    if status == "private":
        return {"error": "private", "hours_2weeks": hours_2weeks, "played_this_week": played_this_week}

    if not stats:
        return {"error": "no_data"}

    total_kills = stats.get("total_kills", 0)
    total_deaths = stats.get("total_deaths", 1) or 1
    total_headshots = stats.get("total_kills_headshot", 0)
    total_matches = stats.get("total_matches_played", 0)
    total_matches_won = stats.get("total_matches_won", 0)

    kd = round(total_kills / total_deaths, 2)
    hs_percent = round(total_headshots / total_kills * 100, 1) if total_kills > 0 else 0
    win_rate = round(total_matches_won / total_matches * 100, 1) if total_matches > 0 else 0

    return {
        "error": None,
        "hours_2weeks": hours_2weeks,
        "played_this_week": played_this_week,
        "kd": kd,
        "hs_percent": hs_percent,
        "total_kills": total_kills,
        "total_deaths": total_deaths,
        "total_matches": total_matches,
        "total_matches_won": total_matches_won,
        "win_rate": win_rate,
    }