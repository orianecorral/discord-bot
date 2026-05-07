from datetime import datetime

def format_rank(rank_data, game="lol"):
    if not rank_data:
        return "Non ranké"
    
    tier = rank_data.get("tier", "UNRANKED").capitalize()
    division = rank_data.get("division", "")
    lp = rank_data.get("lp", 0)
    
    if tier == "Unranked":
        return "Non ranké"
    return f"{tier} {division} ({lp} LP)"

def format_lol(stats):
    if not stats:
        return "❌ Données LoL indisponibles"

    rank = stats.get("rank")
    summary = stats.get("summary")

    solo = format_rank(rank.get("solo") if rank else None)
    flex = format_rank(rank.get("flex") if rank else None)
    level = rank.get("level", "?") if rank else "?"

    if not summary:
        return (
            f"**League of Legends** 🟦\n"
            f"- Rank Solo : {solo}\n"
            f"- Rank Flex : {flex}\n"
            f"- Level : {level}\n"
            f"- Aucune game cette semaine"
        )

    return (
        f"**League of Legends** 🟦\n"
        f"- Rank Solo : {solo} | Flex : {flex}\n"
        f"- Level : {level}\n"
        f"- Games : {summary['wins']}W / {summary['losses']}L "
        f"({summary['winrate']}% WR)\n"
        f"- Champion le + joué : {summary['most_played']} "
        f"({summary['most_played_count']} games)\n"
        f"- KDA moyen : {summary['avg_kda']}"
    )

def format_tft(stats):
    if not stats:
        return "❌ Données TFT indisponibles"

    rank = stats.get("rank")
    summary = stats.get("summary")

    rank_str = format_rank(rank)

    if not summary:
        return (
            f"**Teamfight Tactics** 🟪\n"
            f"- Rank : {rank_str}\n"
            f"- Aucune game cette semaine"
        )

    return (
        f"**Teamfight Tactics** 🟪\n"
        f"- Rank : {rank_str}\n"
        f"- Games : {summary['games']} | "
        f"Top 4 : {summary['top4_rate']}%\n"
        f"- Placement moyen : {summary['avg_placement']}"
    )

def format_valorant(stats):
    if not stats:
        return "❌ Données Valorant indisponibles"

    rank = stats.get("rank")
    summary = stats.get("summary")

    rank_str = rank.get("rank", "Non ranké") if rank else "Non ranké"
    rr = rank.get("rr", 0) if rank else 0

    if not summary:
        return (
            f"**Valorant** 🟥\n"
            f"- Rank : {rank_str} ({rr} RR)\n"
            f"- Aucune game cette semaine"
        )

    return (
        f"**Valorant** 🟥\n"
        f"- Rank : {rank_str} ({rr} RR)\n"
        f"- Games : {summary['wins']}W / {summary['losses']}L "
        f"({summary['winrate']}% WR)\n"
        f"- Agent le + joué : {summary['most_played_agent']} "
        f"({summary['most_played_count']} games)\n"
        f"- KDA moyen : {summary['avg_kda']} | "
        f"ACS moyen : {summary['avg_acs']}"
    )

def format_cs2(stats):
    if not stats:
        return "❌ Données CS2 indisponibles"

    if stats.get("error") == "private":
        hours = stats.get("hours_2weeks")
        hours_str = f"{hours}h" if hours is not None else "N/A"
        return (
            f"**Counter-Strike 2** 🟩\n"
            f"- Heures cette semaine : {hours_str}\n"
            f"- Stats détaillées : profil Steam privé 🔒"
        )

    if stats.get("error") == "no_data":
        return (
            f"**Counter-Strike 2** 🟩\n"
            f"- Aucune donnée disponible"
        )

    hours = stats.get("hours_2weeks")
    hours_str = f"{hours}h" if hours is not None else "N/A"
    played = stats.get("played_this_week", False)

    if not played:
        return (
            f"**Counter-Strike 2** 🟩\n"
            f"- Aucune game cette semaine\n"
            f"- K/D global : {stats.get('kd', 'N/A')} | "
            f"HS% : {stats.get('hs_percent', 'N/A')}%"
        )

    return (
        f"**Counter-Strike 2** 🟩\n"
        f"- Heures cette semaine : {hours_str}\n"
        f"- K/D ratio : {stats.get('kd', 'N/A')} | "
        f"HS% : {stats.get('hs_percent', 'N/A')}%\n"
        f"- Winrate global : {stats.get('win_rate', 'N/A')}% "
        f"({stats.get('total_matches_won', 0)}W / "
        f"{stats.get('total_matches', 0)} matchs)"
    )

def format_wow(stats):
    if not stats:
        return "❌ Données WoW indisponibles"

    profile = stats.get("profile")
    mythic = stats.get("mythic_plus")
    rio = stats.get("raiderio")

    if not profile:
        return "❌ Personnage WoW introuvable"

    char_info = (
        f"{profile.get('name')} — "
        f"{profile.get('spec')} {profile.get('class')} | "
        f"ilvl {profile.get('equipped_item_level', '?')}"
    )

    rio_score = rio.get("rio_score", "N/A") if rio else "N/A"

    mythic_str = "N/A"
    if mythic and mythic.get("best_runs"):
        best = mythic["best_runs"][0]
        mythic_str = f"+{best['level']} {best['dungeon']}"

    raid_str = "N/A"
    if rio and rio.get("raid_progression"):
        raid = rio["raid_progression"]
        latest = list(raid.values())[-1] if raid else None
        if latest:
            raid_str = f"{latest.get('normal_bosses_killed', 0)}N / {latest.get('heroic_bosses_killed', 0)}H / {latest.get('mythic_bosses_killed', 0)}M"

    return (
        f"**World of Warcraft** ⚔️\n"
        f"- {char_info}\n"
        f"- M+ Score : {rio_score} | "
        f"Best key : {mythic_str}\n"
        f"- Raid : {raid_str}"
    )

def format_recap(lol=None, tft=None, valorant=None, cs2=None, wow=None,
                 username=None, week_start=None, week_end=None):
    now = datetime.now()
    if not week_start:
        week_start = now.strftime("%d/%m")
    if not week_end:
        week_end = now.strftime("%d/%m/%Y")

    sections = [
        f"🎮 **WEEKLY GAMING RECAP** — semaine du {week_start} au {week_end}",
        "━━━━━━━━━━━━━━━━━━━━━━",
    ]

    if username:
        sections.append(f"👤 **{username}**")
        sections.append("")

    if lol is not None:
        sections.append(format_lol(lol))
        sections.append("")

    if tft is not None:
        sections.append(format_tft(tft))
        sections.append("")

    if valorant is not None:
        sections.append(format_valorant(valorant))
        sections.append("")

    if cs2 is not None:
        sections.append(format_cs2(cs2))
        sections.append("")

    if wow is not None:
        sections.append(format_wow(wow))
        sections.append("")

    sections.append("━━━━━━━━━━━━━━━━━━━━━━")
    sections.append("💬 **Analyse de la semaine :**")
    sections.append("*Généré par Gaming Recap Bot*")

    return "\n".join(sections)

def format_stats_embed(game, stats, username):
    if game == "lol":
        return format_lol(stats)
    elif game == "tft":
        return format_tft(stats)
    elif game == "valorant":
        return format_valorant(stats)
    elif game == "cs2":
        return format_cs2(stats)
    elif game == "wow":
        return format_wow(stats)
    return "❌ Jeu non reconnu"