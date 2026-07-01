from datetime import datetime


def format_rank(rank_data):
    if not rank_data:
        return "Non ranké"
    tier = rank_data.get("tier", "UNRANKED").capitalize()
    division = rank_data.get("division", "")
    lp = rank_data.get("lp", 0)
    hot_streak = " 🔥" if rank_data.get("hot_streak") else ""
    if tier.upper() == "UNRANKED":
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
        if aram_summary:
            lines.append(
                f"- ARAM : {aram_summary.get('wins', 0)}W / "
                f"{aram_summary.get('losses', 0)}L "
                f"({aram_summary.get('winrate', 0)}% WR) | "
                f"KDA {aram_summary.get('avg_kda', 'N/A')}"
            )
        result = "\n".join(lines)
        return result if result.strip() else "❌ Données LoL indisponibles"

    streak = summary.get("streak", {})
    streak_str = ""
    if streak and streak.get("count", 0) >= 2:
        emoji = "🔥" if streak.get("type") == "win" else "❄️"
        label = "Winstreak" if streak.get("type") == "win" else "Losestreak"
        streak_str = f" | {emoji} {label} x{streak['count']}"

    lines.append(
        f"- Games : {summary.get('wins', 0)}W / {summary.get('losses', 0)}L "
        f"({summary.get('winrate', 0)}% WR){streak_str}"
    )
    lines.append(
        f"- Champion le + joué : {summary.get('most_played', 'N/A')} "
        f"({summary.get('most_played_count', 0)} games)"
    )
    lines.append(f"- KDA moyen : {summary.get('avg_kda', 'N/A')}")
    lines.append(f"- Dégâts moyens : {summary.get('avg_damage', 0):,}")
    lines.append(
        f"- CS/min moyen : {summary.get('avg_cs_min', 'N/A')} | "
        f"Vision score moyen : {summary.get('avg_vision', 'N/A')}"
    )

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

    best = summary.get("best_game")
    if best:
        lines.append(
            f"- 🏆 Meilleure game : {best.get('champion', 'N/A')} "
            f"{best.get('kda_str', 'N/A')} (KDA {best.get('kda', 'N/A')})"
        )

    champ_stats = summary.get("champion_stats", {})
    if champ_stats and len(champ_stats) > 1:
        lines.append("- Stats champions :")
        for champ, s in list(champ_stats.items())[:3]:
            lines.append(
                f"  • {champ} — {s.get('games', 0)}G "
                f"{s.get('winrate', 0)}% WR "
                f"KDA {s.get('avg_kda', 'N/A')}"
            )

    if aram_summary:
        lines.append(
            f"- ARAM : {aram_summary.get('wins', 0)}W / "
            f"{aram_summary.get('losses', 0)}L "
            f"({aram_summary.get('winrate', 0)}% WR) | "
            f"KDA {aram_summary.get('avg_kda', 'N/A')}"
        )

    result = "\n".join(lines)
    return result if result.strip() else "❌ Données LoL indisponibles"


def format_tft(stats):
    if not stats:
        return "❌ Données TFT indisponibles"

    summary = stats.get("summary")

    lines = ["**Teamfight Tactics** 🟪"]

    if not summary:
        lines.append("- Aucune game cette semaine")
    else:
        lines.append(
            f"- Games : {summary.get('games', 0)} | "
            f"Top 4 : {summary.get('top4_rate', 0)}% | "
            f"1ères places : {summary.get('wins', 0)}"
        )
        lines.append(f"- Placement moyen : {summary.get('avg_placement', 'N/A')}")
        lines.append(
            f"- Meilleur : #{summary.get('best_placement', 'N/A')} | "
            f"Pire : #{summary.get('worst_placement', 'N/A')}"
        )

    result = "\n".join(lines)
    return result if result.strip() else "❌ Données TFT indisponibles"


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
            f"- Games : {summary.get('wins', 0)}W / {summary.get('losses', 0)}L "
            f"({summary.get('winrate', 0)}% WR)"
        )
        lines.append(
            f"- Agent le + joué : {summary.get('most_played_agent', 'N/A')} "
            f"({summary.get('most_played_count', 0)} games)"
        )
        lines.append(
            f"- KDA moyen : {summary.get('avg_kda', 'N/A')} | "
            f"ACS moyen : {summary.get('avg_acs', 'N/A')}"
        )

    result = "\n".join(lines)
    return result if result.strip() else "❌ Données Valorant indisponibles"


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
        lines.append(f"- Winrate : {stats.get('win_rate', 'N/A')}")
        if stats.get("rating") and stats.get("rating") != "N/A":
            lines.append(f"- Rating : {stats.get('rating', 'N/A')}")
        if stats.get("adr") and stats.get("adr") != "N/A":
            lines.append(f"- ADR : {stats.get('adr', 'N/A')}")
        lines.append("- *(via csstats.gg)*")

    result = "\n".join(lines)
    return result if result.strip() else "❌ Données CS2 indisponibles"


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
        f"- {profile.get('name', 'N/A')}{guild_str} — "
        f"{profile.get('spec', 'N/A')} {profile.get('class', 'N/A')} | "
        f"ilvl {profile.get('equipped_item_level', '?')} "
        f"({profile.get('item_level', '?')} avg)",
        f"- {profile.get('race', 'N/A')} | {profile.get('faction', 'N/A')} | "
        f"Niveau {profile.get('level', '?')}",
    ]

    rio_score = rio.get("rio_score", "N/A") if rio else "N/A"
    blizz_score = mythic.get("score", "N/A") if mythic else "N/A"
    lines.append(f"- M+ Score : {rio_score} (Raider.IO) | {blizz_score} (Blizzard)")

    if mythic and mythic.get("best_runs"):
        best = mythic["best_runs"][0]
        upgrades_str = "⭐" * best.get("upgrades", 0)
        lines.append(
            f"- Meilleure key : +{best.get('level', '?')} "
            f"{best.get('dungeon', 'N/A')} "
            f"{upgrades_str} ({best.get('duration', '?')}min)"
        )

    if rio and rio.get("recent_runs"):
        runs_str = " | ".join(
            f"+{r.get('level', '?')} {r.get('dungeon', 'N/A')}"
            for r in rio["recent_runs"]
        )
        lines.append(f"- Runs récents : {runs_str}")

    if rio and rio.get("latest_raid"):
        raid = rio["latest_raid"]
        lines.append(
            f"- Raid : {raid.get('name', 'N/A')} — "
            f"{raid.get('normal', 0)}N / {raid.get('heroic', 0)}H / "
            f"{raid.get('mythic', 0)}M (/{raid.get('total', 0)})"
        )

    result = "\n".join(lines)
    return result if result.strip() else "❌ Données WoW indisponibles"


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
        lol_str = format_lol(lol)
        if lol_str:
            sections.append(lol_str)
            sections.append("")

    if tft is not None:
        tft_str = format_tft(tft)
        if tft_str:
            sections.append(tft_str)
            sections.append("")

    if valorant is not None:
        val_str = format_valorant(valorant)
        if val_str:
            sections.append(val_str)
            sections.append("")

    if cs2 is not None:
        cs2_str = format_cs2(cs2)
        if cs2_str:
            sections.append(cs2_str)
            sections.append("")

    if wow is not None:
        wow_str = format_wow(wow)
        if wow_str:
            sections.append(wow_str)
            sections.append("")

    sections.append("━━━━━━━━━━━━━━━━━━━━━━")
    sections.append("*Généré par Gaming Recap Bot*")

    result = "\n".join(sections)
    return result if result.strip() else "❌ Erreur lors de la génération du recap"


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