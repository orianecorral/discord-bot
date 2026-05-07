import os
import requests
from datetime import datetime, timedelta
from apis.riot_base import REGIONS, safe_json, get_headers

QUEUE_RANKED_SOLO = 420
QUEUE_RANKED_FLEX = 440
QUEUE_NORMAL = 400
QUEUE_ARAM = 450
QUEUE_ARENA = 1700

def get_lol_rank(puuid, region="euw"):
    platform = REGIONS.get(region, REGIONS["euw"])["platform"]

    url = f"https://{platform}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
    r = requests.get(url, headers=get_headers())
    if r.status_code != 200:
        return None

    url_summoner = f"https://{platform}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    r_summoner = requests.get(url_summoner, headers=get_headers())
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
            "hot_streak": entry.get("hotStreak", False),
            "veteran": entry.get("veteran", False),
        }
        if queue == "RANKED_SOLO_5x5":
            result["solo"] = info
        elif queue == "RANKED_FLEX_SR":
            result["flex"] = info

    return result

def get_lol_matches(puuid, region="euw", days=7, queue=QUEUE_RANKED_SOLO, count=20):
    regional = REGIONS.get(region, REGIONS["euw"])["regional"]
    start_time = int((datetime.now() - timedelta(days=days)).timestamp())

    url = f"https://{regional}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
    params = {"start": 0, "count": count, "startTime": start_time, "queue": queue}
    r = requests.get(url, headers=get_headers(), params=params)
    if r.status_code != 200:
        return []

    match_ids = r.json()
    matches = []

    for match_id in match_ids:
        url = f"https://{regional}.api.riotgames.com/lol/match/v5/matches/{match_id}"
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

        deaths = player.get("deaths", 1) or 1
        kills = player.get("kills", 0)
        assists = player.get("assists", 0)
        total_damage = player.get("totalDamageDealtToChampions", 0)
        vision_score = player.get("visionScore", 0)
        cs = player.get("totalMinionsKilled", 0) + player.get("neutralMinionsKilled", 0)
        game_duration = data.get("info", {}).get("gameDuration", 1)
        game_duration_min = game_duration / 60

        matches.append({
            "match_id": match_id,
            "champion": player.get("championName"),
            "win": player.get("win"),
            "kills": kills,
            "deaths": player.get("deaths", 0),
            "assists": assists,
            "kda": round((kills + assists) / deaths, 2),
            "kda_str": f"{kills}/{player.get('deaths', 0)}/{assists}",
            "total_damage": total_damage,
            "vision_score": vision_score,
            "cs": cs,
            "cs_per_min": round(cs / game_duration_min, 1) if game_duration_min > 0 else 0,
            "gold": player.get("goldEarned", 0),
            "double_kills": player.get("doubleKills", 0),
            "triple_kills": player.get("tripleKills", 0),
            "quadra_kills": player.get("quadraKills", 0),
            "penta_kills": player.get("pentaKills", 0),
            "first_blood": player.get("firstBloodKill", False),
            "turret_kills": player.get("turretKills", 0),
            "duration_min": round(game_duration_min, 1),
            "timestamp": data.get("info", {}).get("gameStartTimestamp"),
            "queue": data.get("info", {}).get("queueId"),
        })

    return matches

def get_lol_stats(puuid, region="euw", days=7):
    ranked_matches = get_lol_matches(puuid, region, days, QUEUE_RANKED_SOLO)
    aram_matches = get_lol_matches(puuid, region, days, QUEUE_ARAM, count=10)
    rank = get_lol_rank(puuid, region)

    all_matches = ranked_matches + aram_matches

    if not ranked_matches and not aram_matches:
        return {"rank": rank, "matches": [], "aram_matches": [], "summary": None}

    # Stats ranked
    ranked_summary = None
    if ranked_matches:
        wins = sum(1 for m in ranked_matches if m["win"])
        losses = len(ranked_matches) - wins
        winrate = round(wins / len(ranked_matches) * 100, 1)
        avg_kda = round(sum(m["kda"] for m in ranked_matches) / len(ranked_matches), 2)
        avg_damage = round(sum(m["total_damage"] for m in ranked_matches) / len(ranked_matches))
        avg_vision = round(sum(m["vision_score"] for m in ranked_matches) / len(ranked_matches), 1)
        avg_cs_min = round(sum(m["cs_per_min"] for m in ranked_matches) / len(ranked_matches), 1)

        # Champion le plus joué
        champion_count = {}
        for m in ranked_matches:
            champ = m["champion"]
            champion_count[champ] = champion_count.get(champ, 0) + 1
        most_played = max(champion_count, key=champion_count.get)

        # Meilleure game (par KDA)
        best_game = max(ranked_matches, key=lambda m: m["kda"])

        # Pires et meilleures stats
        total_pentas = sum(m["penta_kills"] for m in ranked_matches)
        total_quadras = sum(m["quadra_kills"] for m in ranked_matches)
        total_triples = sum(m["triple_kills"] for m in ranked_matches)
        total_doubles = sum(m["double_kills"] for m in ranked_matches)

        # Streak actuel
        streak = _calculate_streak(ranked_matches)

        ranked_summary = {
            "wins": wins,
            "losses": losses,
            "winrate": winrate,
            "avg_kda": avg_kda,
            "avg_damage": avg_damage,
            "avg_vision": avg_vision,
            "avg_cs_min": avg_cs_min,
            "most_played": most_played,
            "most_played_count": champion_count[most_played],
            "best_game": best_game,
            "total_pentas": total_pentas,
            "total_quadras": total_quadras,
            "total_triples": total_triples,
            "total_doubles": total_doubles,
            "streak": streak,
            "champion_stats": _champion_stats(ranked_matches),
        }

    # Stats ARAM
    aram_summary = None
    if aram_matches:
        aram_wins = sum(1 for m in aram_matches if m["win"])
        aram_summary = {
            "games": len(aram_matches),
            "wins": aram_wins,
            "losses": len(aram_matches) - aram_wins,
            "winrate": round(aram_wins / len(aram_matches) * 100, 1),
            "avg_kda": round(sum(m["kda"] for m in aram_matches) / len(aram_matches), 2),
        }

    return {
        "rank": rank,
        "matches": ranked_matches,
        "aram_matches": aram_matches,
        "summary": ranked_summary,
        "aram_summary": aram_summary,
    }

def _calculate_streak(matches):
    if not matches:
        return {"type": None, "count": 0}
    sorted_matches = sorted(matches, key=lambda m: m["timestamp"] or 0, reverse=True)
    streak_type = "win" if sorted_matches[0]["win"] else "loss"
    count = 0
    for m in sorted_matches:
        if (m["win"] and streak_type == "win") or (not m["win"] and streak_type == "loss"):
            count += 1
        else:
            break
    return {"type": streak_type, "count": count}

def _champion_stats(matches):
    stats = {}
    for m in matches:
        champ = m["champion"]
        if champ not in stats:
            stats[champ] = {"games": 0, "wins": 0, "kills": 0, "deaths": 0, "assists": 0}
        stats[champ]["games"] += 1
        if m["win"]:
            stats[champ]["wins"] += 1
        stats[champ]["kills"] += m["kills"]
        stats[champ]["deaths"] += m["deaths"]
        stats[champ]["assists"] += m["assists"]

    for champ in stats:
        g = stats[champ]
        g["winrate"] = round(g["wins"] / g["games"] * 100, 1)
        deaths = g["deaths"] or 1
        g["kda"] = round((g["kills"] + g["assists"]) / deaths, 2)

    return dict(sorted(stats.items(), key=lambda x: x[1]["games"], reverse=True))