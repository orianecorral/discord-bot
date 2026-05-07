from datetime import datetime

def format_rank(rank_data):
    if not rank_data:
        return "Non ranké"
    tier = rank_data.get("tier", "UNRANKED").capitalize()
    division = rank_data.get("division", "")
    lp = rank_data.get("lp", 0)
    hot_streak = " 🔥" if rank_data.get("hot_streak") else ""
    if tier == "Unranked":
        return "Non ranké"
    return f"{tier} {division} ({lp} LP){hot_streak}"

def format_lol(stats):
    if not stats:
        return "❌ Données LoL indisponibles"

    rank = stats.get("rank")
    summary = stats.get("summary")
    aram_summary = stats.get("aram_summary")

    solo = format_rank(rank.get("solo") if rank else None)
    flex = format_rank(rank.get("flex") if rank else None)
    level = rank.get("level", "?") if rank else "?"

    lines = [
        "**League of Legends** 🟦",
        f"- Rank Solo : {solo} | Flex : {flex}",
        f"- Level : {level}",
    ]

    if not summary:
        lines.append("- Aucune game ranked cette semaine")
    else:
        # Streak
        streak = summary.get("streak", {})
        streak_str = ""
        if streak and streak.get("count", 0) >= 2:
            emoji = "🔥" if streak["type"] == "win" else "❄️"
            label = "Winstreak" if streak["type"] == "win" else "Losestreak"
            streak_str = f" | {emoji} {label} x{streak['count']}"

        lines.append(
            f"- Games : {summary['wins']}W / {summary['losses']}L "
            f"({summary['winrate']}% WR){streak_str}"
        )
        lines.append(
            f"- Champion le + joué : {summary['most_played']} "
            f"({summary['most_played_count']} games)"
        )
        lines.append(f"- KDA moyen : {summary['avg_kda']}")
        lines.append(f"- Dégâts moyens : {summary['avg_damage']:,}")
        lines.append(
            f"- CS/min moyen : {summary['avg_cs_min']} | "
            f"Vision score moyen : {summary['avg_vision']}"
        )

        # Multikills
        multikills = []
        if summary.get("total_pentas"):
            multikills.append(f"⚔️ Penta x{summary['total_pentas']}")
        if summary.get("total_quadras"):
            multikills.append(f"quadra x{summary['total_quadras']}")
        if summary.get("total_triples"):
            multikills.append(f"triple x{summary['total_triples']}")
        if summary.get("total_doubles"):
            multikills.append(f"double x{summary['total_doubles']}")
        if multikills:
            lines.append(f"- Multikills : {' | '.join(multikills)}")

        # Meilleure game
        best = summary.get("best_game")
        if best:
            lines.append(
                f"- 🏆 Meilleure game : {best['champion']} "
                f"{best['kda_str']} (KDA {best['kda']})"
            )

        # Stats par champion
        champ_stats = summary.get("champion_stats", {})
        if len(champ_stats) > 1:
            lines.append("- Stats champions :")
            for champ, s in list(champ_stats.items())[:3]:
                lines.append(
                    f"  • {champ} — {s['games']}G {s['winrate']}% WR "
                    f"KDA {s['kda']}"
                )

    # ARAM
    if aram_summary:
        lines.append(
            f"- ARAM : {aram_summary['wins']}W / {aram_summary['losses']}L "
            f"({aram_summary['winrate']}% WR) | KDA {aram_summary['avg_kda']}"
        )

    return "\n".join(lines)

def format_tft(stats):
    if not stats:
        return "❌ Données TFT indisponibles"

    rank = stats.get("rank")
    summary = stats.get("summary")
    rank_str = format_rank(rank)

    lines = [
        "**Teamfight Tactics** 🟪",
        f"- Rank : {rank_str}",
    ]

    if not summary:
        lines.append("- Aucune game cette semaine")
    else:
        lines.append(
            f"- Games : {summary['games']} | "
            f"Top 4 : {summary['top4_rate']}% | "
            f"1ères places : {summary['wins']}"
        )
        lines.append(f"- Placement moyen : {summary['avg_placement']}")
        lines.append(
            f"- Meilleur : #{summary['best_placement']} | "
            f"Pire : #{summary['worst_placement']}"
        )

    return "\n".join(lines)

def format_valorant(stats):
    if not stats:
        return "❌ Données Valorant indisponibles"

    rank = stats.get("rank")
    summary = stats.get("summary")
    rank_str = rank.get("rank", "Non ranké") if rank else "Non ranké"
    rr = rank.get("rr", 0) if rank else 0

    lines = [
        "**Valorant** 🟥",
        f"- Rank : {rank_str} ({rr} RR)",
    ]

    if not summary:
        lines.append("- Aucune game cette semaine")
    else:
        lines.append(
            f"- Games : {summary['wins']}W / {summary['losses']}L "
            f"({summary['winrate']}% WR)"
        )
        lines.append(
            f"- Agent le + joué : {summary['most_played_agent']} "
            f"({summary['most_played_count']} games)"
        )
        lines.append(
            f"- KDA moyen : {summary['avg_kda']} | "
            f"ACS moyen : {summary['avg_acs']}"
        )

    return "\n".join(lines)

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

    if stats.get("error") == "no_game":
        return "**Counter-Strike 2** 🟩\n- Aucune partie jouée sur ce compte"

    if stats.get("error") in ("no_data", "error"):
        return "**Counter-Strike 2** 🟩\n- Aucune donnée disponible"

    hours = stats.get("hours_2weeks")
    hours_str = f"{hours}h" if hours is not None else "N/A"
    played = stats.get("played_this_week", False)
    source = stats.get("source", "steam")

    lines = ["**Counter-Strike 2** 🟩"]

    if not played:
        lines.append("- Aucune game cette semaine")
    else:
        lines.append(f"- Heures cette semaine : {hours_str}")

    lines.append(
        f"- K/D ratio : {stats.get('kd', 'N/A')} | "
        f"HS% : {stats.get('hs_percent', 'N/A')}%"
    )

    if source == "steam":
        lines.append(
            f"- Précision : {stats.get('accuracy', 'N/A')}% | "
            f"MVPs : {stats.get('total_mvps', 'N/A')}"
        )
        lines.append(
            f"- Winrate global : {stats.get('win_rate', 'N/A')}% "
            f"({stats.get('total_matches_won', 0)}W / "
            f"{stats.get('total_matches', 0)} matchs)"
        )
        lines.append(
            f"- Carte préférée : {stats.get('favorite_map', 'N/A')} | "
            f"Knife kills : {stats.get('total_knife_kills', 0)}"
        )
        lines.append(
            f"- Bombes posées : {stats.get('total_bomb_planted', 0)} | "
            f"Désamorcées : {stats.get('total_bomb_defused', 0)}"
        )
    else:
        # Source csstats.gg
        lines.append(f"- Winrate : {stats.get('win_rate', 'N/A')}")
        if stats.get("rating") != "N/A":
            lines.append(f"- Rating : {stats.get('rating', 'N/A')}")
        if stats.get("adr") != "N/A":
            lines.append(f"- ADR : {stats.get('adr', 'N/A')}")
        lines.append("- *(via csstats.gg)*")

    return "\n".join(lines)

def format_recap(lol=None, tft=None, valorant=None, cs2=None,
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

    sections.append("━━━━━━━━━━━━━━━━━━━━━━")
    sections.append("*Généré par Gaming Recap Bot*")

    return "\n".join(sections)

def format_wow(stats):
    if not stats:
        return "❌ Données WoW indisponibles"

    profile = stats.get("profile")
    mythic = stats.get("mythic_plus")
    rio = stats.get("raiderio")

    if not profile:
        return "❌ Personnage WoW introuvable"

    guild_str = f" <{profile.get('guild')}>" if profile.get("guild") else ""
    lines = [
        "**World of Warcraft** ⚔️",
        f"- {profile.get('name')}{guild_str} — "
        f"{profile.get('spec')} {profile.get('class')} | "
        f"ilvl {profile.get('equipped_item_level', '?')} "
        f"({profile.get('item_level', '?')} avg)",
        f"- {profile.get('race')} | {profile.get('faction')} | "
        f"Niveau {profile.get('level')}",
    ]

    # Mythic+
    rio_score = rio.get("rio_score", "N/A") if rio else "N/A"
    blizz_score = mythic.get("score", "N/A") if mythic else "N/A"
    lines.append(f"- M+ Score : {rio_score} (Raider.IO) | {blizz_score} (Blizzard)")

    if mythic and mythic.get("best_runs"):
        best = mythic["best_runs"][0]
        upgrades_str = "⭐" * best.get("upgrades", 0)
        lines.append(
            f"- Meilleure key : +{best['level']} {best['dungeon']} "
            f"{upgrades_str} ({best['duration']}min)"
        )

    # Runs récents raider.io
    if rio and rio.get("recent_runs"):
        runs_str = " | ".join(
            f"+{r['level']} {r['dungeon']}"
            for r in rio["recent_runs"]
        )
        lines.append(f"- Runs récents : {runs_str}")

    # Progression raid
    if rio and rio.get("latest_raid"):
        raid = rio["latest_raid"]
        lines.append(
            f"- Raid : {raid['name']} — "
            f"{raid['normal']}N / {raid['heroic']}H / "
            f"{raid['mythic']}M (/{raid['total']})"
        )

    return "\n".join(lines)

def format_stats_embed(game, stats, username):
    if game == "lol":
        return format_lol(stats)
    elif game == "tft":
        return format_tft(stats)
    elif game == "valorant":
        return format_valorant(stats)
    elif game == "cs2":
        return format_cs2(stats)
    return "❌ Jeu non reconnu"