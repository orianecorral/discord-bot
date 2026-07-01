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
        game_duration_min = game_duration / 60 or 1

        team_id = player.get("teamId")
        team_damage = sum(
            p.get("totalDamageDealtToChampions", 0)
            for p in participants
            if p.get("teamId") == team_id
        ) or 1
        damage_share = round(total_damage / team_damage * 100, 1)

        team_gold = sum(
            p.get("goldEarned", 0)
            for p in participants
            if p.get("teamId") == team_id
        ) or 1
        gold_share = round(player.get("goldEarned", 0) / team_gold * 100, 1)

        matches.append({
            "match_id": match_id,
            "champion": player.get("championName"),
            "champion_id": player.get("championId"),
            "position": player.get("teamPosition", "UNKNOWN"),
            "win": player.get("win"),
            "kills": kills,
            "deaths": player.get("deaths", 0),
            "assists": assists,
            "kda": round((kills + assists) / deaths, 2),
            "kda_str": f"{kills}/{player.get('deaths', 0)}/{assists}",
            "total_damage": total_damage,
            "damage_per_min": round(total_damage / game_duration_min),
            "damage_share": damage_share,
            "vision_score": vision_score,
            "vision_per_min": round(vision_score / game_duration_min, 2),
            "cs": cs,
            "cs_per_min": round(cs / game_duration_min, 1),
            "gold": player.get("goldEarned", 0),
            "gold_per_min": round(player.get("goldEarned", 0) / game_duration_min),
            "gold_share": gold_share,
            "double_kills": player.get("doubleKills", 0),
            "triple_kills": player.get("tripleKills", 0),
            "quadra_kills": player.get("quadraKills", 0),
            "penta_kills": player.get("pentaKills", 0),
            "first_blood": player.get("firstBloodKill", False),
            "first_blood_assist": player.get("firstBloodAssist", False),
            "turret_kills": player.get("turretKills", 0),
            "inhibitor_kills": player.get("inhibitorKills", 0),
            "wards_placed": player.get("wardsPlaced", 0),
            "wards_killed": player.get("wardsKilled", 0),
            "control_wards": player.get("visionWardsBoughtInGame", 0),
            "duration_min": round(game_duration_min, 1),
            "game_ended_early": data.get("info", {}).get("gameEndedInEarlySurrender", False),
            "timestamp": data.get("info", {}).get("gameStartTimestamp"),
            "queue": data.get("info", {}).get("queueId"),
        })

    return matches

def get_champion_analysis(matches):
    if not matches:
        return {}

    champ_data = {}

    for m in matches:
        champ = m.get("champion")
        if not champ:
            continue
        if champ not in champ_data:
            champ_data[champ] = {
                "games": 0,
                "wins": 0,
                "kills": 0,
                "deaths": 0,
                "assists": 0,
                "total_damage": 0,
                "damage_per_min": 0,
                "damage_share": 0,
                "cs_per_min": 0,
                "vision_per_min": 0,
                "gold_per_min": 0,
                "gold_share": 0,
                "double_kills": 0,
                "triple_kills": 0,
                "quadra_kills": 0,
                "penta_kills": 0,
                "first_bloods": 0,
                "positions": {},
                "durations": [],
                "game_results": [],
            }

        c = champ_data[champ]
        c["games"] += 1
        if m.get("win"):
            c["wins"] += 1
        c["kills"] += m.get("kills", 0)
        c["deaths"] += m.get("deaths", 0)
        c["assists"] += m.get("assists", 0)
        c["total_damage"] += m.get("total_damage", 0)
        c["damage_per_min"] += m.get("damage_per_min", 0)
        c["damage_share"] += m.get("damage_share", 0)
        c["cs_per_min"] += m.get("cs_per_min", 0)
        c["vision_per_min"] += m.get("vision_per_min", 0)
        c["gold_per_min"] += m.get("gold_per_min", 0)
        c["gold_share"] += m.get("gold_share", 0)
        c["double_kills"] += m.get("double_kills", 0)
        c["triple_kills"] += m.get("triple_kills", 0)
        c["quadra_kills"] += m.get("quadra_kills", 0)
        c["penta_kills"] += m.get("penta_kills", 0)
        if m.get("first_blood"):
            c["first_bloods"] += 1
        pos = m.get("position", "UNKNOWN")
        c["positions"][pos] = c["positions"].get(pos, 0) + 1
        c["durations"].append(m.get("duration_min", 0))
        c["game_results"].append(1 if m.get("win") else 0)

    result = {}
    for champ, c in champ_data.items():
        g = c["games"]
        deaths = c["deaths"] or 1
        avg_kda = round((c["kills"] + c["assists"]) / deaths, 2)
        winrate = round(c["wins"] / g * 100, 1)
        avg_duration = round(sum(c["durations"]) / g, 1)

        main_pos = max(c["positions"], key=c["positions"].get) if c["positions"] else "UNKNOWN"

        results = c["game_results"]
        if len(results) >= 4:
            first_half = sum(results[:len(results)//2]) / (len(results)//2)
            second_half = sum(results[len(results)//2:]) / (len(results) - len(results)//2)
            trend = round((second_half - first_half) * 100, 1)
        else:
            trend = 0

        short_games = [r for r, d in zip(c["game_results"], c["durations"]) if d < 25]
        long_games = [r for r, d in zip(c["game_results"], c["durations"]) if d >= 35]
        short_wr = round(sum(short_games) / len(short_games) * 100, 1) if short_games else None
        long_wr = round(sum(long_games) / len(long_games) * 100, 1) if long_games else None

        result[champ] = {
            "games": g,
            "wins": c["wins"],
            "losses": g - c["wins"],
            "winrate": winrate,
            "avg_kda": avg_kda,
            "avg_kills": round(c["kills"] / g, 1),
            "avg_deaths": round(c["deaths"] / g, 1),
            "avg_assists": round(c["assists"] / g, 1),
            "avg_damage": round(c["total_damage"] / g),
            "avg_damage_per_min": round(c["damage_per_min"] / g),
            "avg_damage_share": round(c["damage_share"] / g, 1),
            "avg_cs_per_min": round(c["cs_per_min"] / g, 1),
            "avg_vision_per_min": round(c["vision_per_min"] / g, 2),
            "avg_gold_per_min": round(c["gold_per_min"] / g),
            "avg_gold_share": round(c["gold_share"] / g, 1),
            "double_kills": c["double_kills"],
            "triple_kills": c["triple_kills"],
            "quadra_kills": c["quadra_kills"],
            "penta_kills": c["penta_kills"],
            "first_bloods": c["first_bloods"],
            "main_position": main_pos,
            "avg_duration": avg_duration,
            "trend": trend,
            "short_game_wr": short_wr,
            "long_game_wr": long_wr,
        }

    return dict(sorted(result.items(), key=lambda x: x[1]["games"], reverse=True))

def get_lol_stats(puuid, region="euw", days=7):
    ranked_matches = get_lol_matches(puuid, region, days, QUEUE_RANKED_SOLO)
    aram_matches = get_lol_matches(puuid, region, days, QUEUE_ARAM, count=10)
    rank = get_lol_rank(puuid, region)

    if not ranked_matches and not aram_matches:
        return {"rank": rank, "matches": [], "aram_matches": [], "summary": None}

    ranked_summary = None
    if ranked_matches:
        wins = sum(1 for m in ranked_matches if m.get("win"))
        losses = len(ranked_matches) - wins
        winrate = round(wins / len(ranked_matches) * 100, 1)
        avg_kda = round(sum(m.get("kda", 0) for m in ranked_matches) / len(ranked_matches), 2)
        avg_damage = round(sum(m.get("total_damage", 0) for m in ranked_matches) / len(ranked_matches))
        avg_vision = round(sum(m.get("vision_score", 0) for m in ranked_matches) / len(ranked_matches), 1)
        avg_cs_min = round(sum(m.get("cs_per_min", 0) for m in ranked_matches) / len(ranked_matches), 1)
        avg_damage_share = round(sum(m.get("damage_share", 0) for m in ranked_matches) / len(ranked_matches), 1)

        champion_count = {}
        for m in ranked_matches:
            champ = m.get("champion")
            if champ:
                champion_count[champ] = champion_count.get(champ, 0) + 1
        most_played = max(champion_count, key=champion_count.get) if champion_count else "N/A"

        best_game = max(ranked_matches, key=lambda m: m.get("kda", 0))

        total_pentas = sum(m.get("penta_kills", 0) for m in ranked_matches)
        total_quadras = sum(m.get("quadra_kills", 0) for m in ranked_matches)
        total_triples = sum(m.get("triple_kills", 0) for m in ranked_matches)
        total_doubles = sum(m.get("double_kills", 0) for m in ranked_matches)

        streak = _calculate_streak(ranked_matches)
        champion_analysis = get_champion_analysis(ranked_matches)

        ranked_summary = {
            "wins": wins,
            "losses": losses,
            "winrate": winrate,
            "avg_kda": avg_kda,
            "avg_damage": avg_damage,
            "avg_vision": avg_vision,
            "avg_cs_min": avg_cs_min,
            "avg_damage_share": avg_damage_share,
            "most_played": most_played,
            "most_played_count": champion_count.get(most_played, 0),
            "best_game": best_game,
            "total_pentas": total_pentas,
            "total_quadras": total_quadras,
            "total_triples": total_triples,
            "total_doubles": total_doubles,
            "streak": streak,
            "champion_stats": champion_analysis,
        }

    aram_summary = None
    if aram_matches:
        aram_wins = sum(1 for m in aram_matches if m.get("win"))
        aram_summary = {
            "games": len(aram_matches),
            "wins": aram_wins,
            "losses": len(aram_matches) - aram_wins,
            "winrate": round(aram_wins / len(aram_matches) * 100, 1),
            "avg_kda": round(sum(m.get("kda", 0) for m in aram_matches) / len(aram_matches), 2),
        }

    return {
        "rank": rank,
        "matches": ranked_matches,
        "aram_matches": aram_matches,
        "summary": ranked_summary,
        "aram_summary": aram_summary,
    }

def get_lol_insights(puuid, region="euw", days=30):
    matches = get_lol_matches(puuid, region, days, QUEUE_RANKED_SOLO, count=50)
    rank = get_lol_rank(puuid, region)

    if not matches:
        return {"rank": rank, "matches": [], "champion_analysis": {}, "total_games": 0}

    champion_analysis = get_champion_analysis(matches)

    return {
        "rank": rank,
        "total_games": len(matches),
        "matches": matches,
        "champion_analysis": champion_analysis,
    }

def _calculate_streak(matches):
    if not matches:
        return {"type": None, "count": 0}
    sorted_matches = sorted(matches, key=lambda m: m.get("timestamp") or 0, reverse=True)
    streak_type = "win" if sorted_matches[0].get("win") else "loss"
    count = 0
    for m in sorted_matches:
        if (m.get("win") and streak_type == "win") or (not m.get("win") and streak_type == "loss"):
            count += 1
        else:
            break
    return {"type": streak_type, "count": count}