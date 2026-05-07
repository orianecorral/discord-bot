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
    if r.status_code == 400:
        return None, "no_game"
    if r.status_code != 200:
        return None, "error"
    stats_list = r.json().get("playerstats", {}).get("stats", [])
    stats = {s["name"]: s["value"] for s in stats_list}
    return stats, "ok"

def get_cs2_stats_csstats(steam_id):
    url = f"https://csstats.gg/player/{steam_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        return None

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r.text, "html.parser")

        kd = soup.find("div", {"title": "K/D Ratio"})
        winrate = soup.find("div", {"title": "Win Rate"})
        rating = soup.find("div", {"title": "Rating"})
        hs = soup.find("div", {"title": "Headshot %"})
        adr = soup.find("div", {"title": "ADR"})

        return {
            "kd": kd.text.strip() if kd else "N/A",
            "winrate": winrate.text.strip() if winrate else "N/A",
            "rating": rating.text.strip() if rating else "N/A",
            "hs_percent": hs.text.strip() if hs else "N/A",
            "adr": adr.text.strip() if adr else "N/A",
            "source": "csstats"
        }
    except Exception:
        return None

def get_cs2_full_stats(steam_id):
    recent = get_recently_played(steam_id)
    stats, status = get_cs2_stats(steam_id)

    hours_2weeks = None
    played_this_week = False
    if recent:
        hours_2weeks = round(recent.get("playtime_2weeks", 0) / 60, 1)
        played_this_week = hours_2weeks > 0

    # Profil privé ou pas de stats Steam → fallback csstats.gg
    if status in ("private", "no_game", "error"):
        csstats = get_cs2_stats_csstats(steam_id)
        if csstats:
            return {
                "error": None,
                "hours_2weeks": hours_2weeks,
                "played_this_week": played_this_week,
                "kd": csstats.get("kd", "N/A"),
                "hs_percent": csstats.get("hs_percent", "N/A"),
                "win_rate": csstats.get("winrate", "N/A"),
                "rating": csstats.get("rating", "N/A"),
                "adr": csstats.get("adr", "N/A"),
                "total_matches": "N/A",
                "total_matches_won": "N/A",
                "source": "csstats",
            }
        # Pas de fallback possible
        if status == "private":
            return {
                "error": "private",
                "hours_2weeks": hours_2weeks,
                "played_this_week": played_this_week,
            }
        if status == "no_game":
            return {"error": "no_game"}
        return {"error": "error"}

    if not stats:
        return {"error": "no_data"}

    total_kills = stats.get("total_kills", 0)
    total_deaths = stats.get("total_deaths", 1) or 1
    total_headshots = stats.get("total_kills_headshot", 0)
    total_matches = stats.get("total_matches_played", 0)
    total_matches_won = stats.get("total_matches_won", 0)
    total_shots_fired = stats.get("total_shots_fired", 1) or 1
    total_shots_hit = stats.get("total_shots_hit", 0)
    total_mvps = stats.get("total_mvps", 0)
    total_knife_kills = stats.get("total_kills_knife", 0)
    total_bomb_planted = stats.get("total_planted_bombs", 0)
    total_bomb_defused = stats.get("total_defused_bombs", 0)

    kd = round(total_kills / total_deaths, 2)
    hs_percent = round(total_headshots / total_kills * 100, 1) if total_kills > 0 else 0
    accuracy = round(total_shots_hit / total_shots_fired * 100, 1)
    win_rate = round(total_matches_won / total_matches * 100, 1) if total_matches > 0 else 0

    # Map préférée
    map_stats = {}
    for key, value in stats.items():
        if key.startswith("total_rounds_map_"):
            map_name = key.replace("total_rounds_map_", "").replace("de_", "").capitalize()
            map_stats[map_name] = value
    favorite_map = max(map_stats, key=map_stats.get) if map_stats else "N/A"

    return {
        "error": None,
        "hours_2weeks": hours_2weeks,
        "played_this_week": played_this_week,
        "kd": kd,
        "hs_percent": hs_percent,
        "accuracy": accuracy,
        "win_rate": win_rate,
        "total_kills": total_kills,
        "total_deaths": total_deaths,
        "total_matches": total_matches,
        "total_matches_won": total_matches_won,
        "total_mvps": total_mvps,
        "total_knife_kills": total_knife_kills,
        "total_bomb_planted": total_bomb_planted,
        "total_bomb_defused": total_bomb_defused,
        "favorite_map": favorite_map,
        "source": "steam",
    }