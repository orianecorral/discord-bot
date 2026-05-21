import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime, timedelta

from database import init_db, register_game, get_user, get_all_users, delete_user
from apis.riot_base import get_puuid
from apis.lol import get_lol_stats
from apis.tft import get_tft_stats
from apis.valorant import get_valorant_stats
from apis.steam import get_cs2_full_stats
from apis.wow import get_wow_stats
from formatter import format_recap, format_stats_embed, format_wow

load_dotenv(override=False)

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
DISCORD_GUILD_ID = int(os.environ.get("DISCORD_GUILD_ID", 0))

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ====================
# EVENTS
# ====================

@bot.event
async def on_ready():
    init_db()
    from scheduler import setup_scheduler
    setup_scheduler(bot)
    print(f"✅ Bot connecté : {bot.user}")
    try:
        if DISCORD_GUILD_ID:
            guild = discord.Object(id=DISCORD_GUILD_ID)
            tree.copy_global_to(guild=guild)
            await tree.sync(guild=guild)
        else:
            await tree.sync()
        print("✅ Slash commands synchronisées")
    except Exception as e:
        print(f"❌ Erreur sync commands : {e}")

# ====================
# REGISTER
# ====================

@tree.command(name="register", description="Enregistre un jeu sur ton profil")
@app_commands.describe(
    game="Le jeu (lol, tft, valorant, cs2, wow)",
    username="Ton pseudo (ou Steam ID 64 pour CS2, personnage pour WoW)",
    tag="Ton tag (ex: EUW) ou royaume pour WoW",
    region="Ta région (eu, na, kr) — défaut: eu",
)
async def register(
    interaction: discord.Interaction,
    game: str,
    username: str,
    tag: str = None,
    region: str = "eu",
):
    await interaction.response.defer(ephemeral=True)
    game = game.lower()
    discord_id = str(interaction.user.id)
    discord_name = interaction.user.display_name

    if game in ("lol", "tft", "valorant"):
        if not tag:
            await interaction.followup.send(
                "❌ Le tag est requis pour LoL, TFT et Valorant (ex: `EUW`)",
                ephemeral=True
            )
            return

        if game == "lol":
            puuid = get_puuid(username, tag, region)
            if not puuid:
                await interaction.followup.send(
                    f"❌ Compte Riot introuvable : `{username}#{tag}`",
                    ephemeral=True
                )
                return

        if game == "tft":
            puuid = get_puuid(username, tag, region, use_tft_key=True)
            if not puuid:
                await interaction.followup.send(
                    f"❌ Compte Riot introuvable : `{username}#{tag}`",
                    ephemeral=True
                )
                return

        register_game(discord_id, discord_name, game, username=username, tag=tag)
        await interaction.followup.send(
            f"✅ **{game.upper()}** enregistré : `{username}#{tag}`",
            ephemeral=True
        )

    elif game == "cs2":
        register_game(discord_id, discord_name, game, steam_id=username)
        await interaction.followup.send(
            f"✅ **CS2** enregistré : Steam ID `{username}`",
            ephemeral=True
        )

    elif game == "wow":
        if not tag:
            await interaction.followup.send(
                "❌ Le royaume est requis pour WoW. "
                "Utilise `/register wow <personnage> <royaume>`",
                ephemeral=True
            )
            return
        register_game(
            discord_id, discord_name, game,
            character=username, realm=tag, region=region
        )
        await interaction.followup.send(
            f"✅ **WoW** enregistré : `{username}` sur `{tag}` ({region.upper()})",
            ephemeral=True
        )

    else:
        await interaction.followup.send(
            "❌ Jeu non reconnu. Choix disponibles : `lol`, `tft`, `valorant`, `cs2`, `wow`",
            ephemeral=True
        )

@tree.command(name="register_all", description="Enregistre LoL, TFT et Valorant en une seule commande")
@app_commands.describe(
    riot_username="Ton pseudo Riot (même pour LoL, TFT et Valorant)",
    riot_tag="Ton tag Riot (ex: EUW)",
    steam_id="Ton Steam ID 64 pour CS2 (optionnel)",
    region="Ta région (eu, na, kr) — défaut: eu",
)
async def register_all(
    interaction: discord.Interaction,
    riot_username: str,
    riot_tag: str,
    steam_id: str = None,
    region: str = "eu",
):
    await interaction.response.defer(ephemeral=True)
    discord_id = str(interaction.user.id)
    discord_name = interaction.user.display_name

    # Vérification avec clé LoL
    puuid_lol = get_puuid(riot_username, riot_tag, region)
    if not puuid_lol:
        await interaction.followup.send(
            f"❌ Compte Riot introuvable : `{riot_username}#{riot_tag}`",
            ephemeral=True
        )
        return

    # Vérification avec clé TFT
    puuid_tft = get_puuid(riot_username, riot_tag, region, use_tft_key=True)

    register_game(discord_id, discord_name, "lol", username=riot_username, tag=riot_tag)
    register_game(discord_id, discord_name, "tft", username=riot_username, tag=riot_tag)
    register_game(discord_id, discord_name, "valorant", username=riot_username, tag=riot_tag)

    lines = [
        f"✅ **LoL** : `{riot_username}#{riot_tag}`",
        f"✅ **TFT** : `{riot_username}#{riot_tag}`" + (" ⚠️ clé TFT manquante" if not puuid_tft else ""),
        f"✅ **Valorant** : `{riot_username}#{riot_tag}`",
    ]

    if steam_id:
        register_game(discord_id, discord_name, "cs2", steam_id=steam_id)
        lines.append(f"✅ **CS2** : Steam ID `{steam_id}`")

    lines.append(f"\n👤 Profil enregistré pour **{discord_name}** !")
    await interaction.followup.send("\n".join(lines), ephemeral=True)

# ====================
# PROFILE
# ====================

@tree.command(name="profile", description="Affiche ton profil enregistré")
@app_commands.describe(member="Membre du serveur (optionnel)")
async def profile(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    user = get_user(str(target.id))

    if not user:
        await interaction.response.send_message(
            f"❌ Aucun profil enregistré pour **{target.display_name}**. "
            f"Utilise `/register_all` pour commencer !",
            ephemeral=True
        )
        return

    lines = [f"👤 **Profil de {target.display_name}**\n"]
    if user.get("lol_username"):
        lines.append(f"🟦 **LoL** : `{user['lol_username']}#{user['lol_tag']}`")
    if user.get("tft_username"):
        lines.append(f"🟪 **TFT** : `{user['tft_username']}#{user['tft_tag']}`")
    if user.get("valorant_username"):
        lines.append(f"🟥 **Valorant** : `{user['valorant_username']}#{user['valorant_tag']}`")
    if user.get("steam_id"):
        lines.append(f"🟩 **CS2** : Steam ID `{user['steam_id']}`")
    if user.get("wow_character"):
        lines.append(
            f"⚔️ **WoW** : `{user['wow_character']}` sur "
            f"`{user['wow_realm']}` ({user['wow_region'].upper()})"
        )
    if len(lines) == 1:
        lines.append("Aucun jeu enregistré. Utilise `/register_all` !")

    await interaction.response.send_message("\n".join(lines), ephemeral=True)

# ====================
# STATS PAR JEU
# ====================

async def fetch_and_send(interaction, target, game):
    print(f"DEBUG - Discord ID cherché: {str(target.id)}")
    print(f"DEBUG - Discord name: {target.display_name}")
    await interaction.response.defer()
    user = get_user(str(target.id))

    if not user:
        await interaction.followup.send(
            f"❌ **{target.display_name}** n'a pas de profil enregistré. "
            f"Utilise `/register_all` pour commencer !"
        )
        return

    msg = await interaction.followup.send(
        f"⏳ Récupération des stats **{game.upper()}** de **{target.display_name}**..."
    )
    result = None

    try:
        if game == "lol" and user.get("lol_username"):
            puuid = get_puuid(user["lol_username"], user["lol_tag"])
            stats = get_lol_stats(puuid) if puuid else None
            result = format_stats_embed(game, stats, target.display_name)

        elif game == "tft" and user.get("tft_username"):
            puuid = get_puuid(user["tft_username"], user["tft_tag"], use_tft_key=True)
            stats = get_tft_stats(puuid) if puuid else None
            result = format_stats_embed(game, stats, target.display_name)

        elif game == "valorant" and user.get("valorant_username"):
            stats = get_valorant_stats(
                user["valorant_username"], user["valorant_tag"]
            )
            result = format_stats_embed(game, stats, target.display_name)

        elif game == "cs2" and user.get("steam_id"):
            stats = get_cs2_full_stats(user["steam_id"])
            result = format_stats_embed(game, stats, target.display_name)

        elif game == "wow" and user.get("wow_character"):
            stats = get_wow_stats(
                user["wow_character"], user["wow_realm"], user["wow_region"]
            )
            result = format_wow(stats)

        else:
            result = (
                f"❌ **{target.display_name}** n'a pas de compte "
                f"**{game.upper()}** enregistré."
            )

    except Exception as e:
        result = f"❌ Erreur : {e}"

    await msg.edit(content=result)

@tree.command(name="lol", description="Stats League of Legends d'un joueur")
@app_commands.describe(member="Membre du serveur (optionnel)")
async def lol(interaction: discord.Interaction, member: discord.Member = None):
    await fetch_and_send(interaction, member or interaction.user, "lol")

@tree.command(name="tft", description="Stats Teamfight Tactics d'un joueur")
@app_commands.describe(member="Membre du serveur (optionnel)")
async def tft(interaction: discord.Interaction, member: discord.Member = None):
    await fetch_and_send(interaction, member or interaction.user, "tft")

@tree.command(name="valorant", description="Stats Valorant d'un joueur")
@app_commands.describe(member="Membre du serveur (optionnel)")
async def valorant(interaction: discord.Interaction, member: discord.Member = None):
    await fetch_and_send(interaction, member or interaction.user, "valorant")

@tree.command(name="cs2", description="Stats CS2 d'un joueur")
@app_commands.describe(member="Membre du serveur (optionnel)")
async def cs2(interaction: discord.Interaction, member: discord.Member = None):
    await fetch_and_send(interaction, member or interaction.user, "cs2")

@tree.command(name="wow", description="Stats World of Warcraft d'un joueur")
@app_commands.describe(member="Membre du serveur (optionnel)")
async def wow(interaction: discord.Interaction, member: discord.Member = None):
    await fetch_and_send(interaction, member or interaction.user, "wow")

# ====================
# RECAP
# ====================

@tree.command(name="recap", description="Weekly recap complet d'un joueur")
@app_commands.describe(member="Membre du serveur (optionnel)")
async def recap(interaction: discord.Interaction, member: discord.Member = None):
    await interaction.response.defer()
    target = member or interaction.user
    user = get_user(str(target.id))

    if not user:
        await interaction.followup.send(
            f"❌ **{target.display_name}** n'a pas de profil enregistré."
        )
        return

    msg = await interaction.followup.send("⏳ Génération du recap en cours...")
    lol_stats = tft_stats = val_stats = cs2_stats = wow_stats = None

    try:
        if user.get("lol_username"):
            puuid = get_puuid(user["lol_username"], user["lol_tag"])
            if puuid:
                lol_stats = get_lol_stats(puuid)

        if user.get("tft_username"):
            puuid = get_puuid(user["tft_username"], user["tft_tag"], use_tft_key=True)
            if puuid:
                tft_stats = get_tft_stats(puuid)

        if user.get("valorant_username"):
            val_stats = get_valorant_stats(
                user["valorant_username"], user["valorant_tag"]
            )

        if user.get("steam_id"):
            cs2_stats = get_cs2_full_stats(user["steam_id"])

        if user.get("wow_character"):
            wow_stats = get_wow_stats(
                user["wow_character"], user["wow_realm"], user["wow_region"]
            )

        now = datetime.now()
        week_start = (now - timedelta(days=7)).strftime("%d/%m")
        week_end = now.strftime("%d/%m/%Y")

        message = format_recap(
            lol=lol_stats,
            tft=tft_stats,
            valorant=val_stats,
            cs2=cs2_stats,
            wow=wow_stats,
            username=target.display_name,
            week_start=week_start,
            week_end=week_end,
        )

    except Exception as e:
        message = f"❌ Erreur : {e}"

    await msg.edit(content=message)

# ====================
# LEADERBOARD
# ====================

@tree.command(name="leaderboard", description="Classement du serveur par jeu")
@app_commands.describe(game="Le jeu (lol, tft, valorant, cs2, wow)")
async def leaderboard(interaction: discord.Interaction, game: str):
    await interaction.response.defer()
    game = game.lower()
    users = get_all_users()

    if not users:
        await interaction.followup.send("❌ Aucun joueur enregistré sur ce serveur.")
        return

    msg = await interaction.followup.send(
        f"⏳ Génération du leaderboard **{game.upper()}**..."
    )
    entries = []

    for user in users:
        try:
            member = interaction.guild.get_member(int(user["discord_id"]))
            name = member.display_name if member else user["discord_name"]

            if game == "lol" and user.get("lol_username"):
                puuid = get_puuid(user["lol_username"], user["lol_tag"])
                if puuid:
                    stats = get_lol_stats(puuid)
                    rank = stats.get("rank", {})
                    solo = rank.get("solo") if rank else None
                    if solo:
                        entries.append({
                            "name": name,
                            "rank": f"{solo['tier'].capitalize()} {solo['division']}",
                            "lp": solo["lp"],
                            "sort": _rank_to_int(
                                solo["tier"], solo["division"], solo["lp"]
                            ),
                        })

            elif game == "tft" and user.get("tft_username"):
                puuid = get_puuid(user["tft_username"], user["tft_tag"], use_tft_key=True)
                if puuid:
                    stats = get_tft_stats(puuid)
                    rank = stats.get("rank", {})
                    if rank and rank.get("tier") != "UNRANKED":
                        entries.append({
                            "name": name,
                            "rank": f"{rank['tier'].capitalize()} {rank['division']}",
                            "lp": rank["lp"],
                            "sort": _rank_to_int(
                                rank["tier"], rank["division"], rank["lp"]
                            ),
                        })

            elif game == "cs2" and user.get("steam_id"):
                stats = get_cs2_full_stats(user["steam_id"])
                if stats and not stats.get("error"):
                    entries.append({
                        "name": name,
                        "rank": f"K/D {stats['kd']}",
                        "lp": stats["kd"],
                        "sort": stats["kd"],
                    })

            elif game == "wow" and user.get("wow_character"):
                stats = get_wow_stats(
                    user["wow_character"], user["wow_realm"], user["wow_region"]
                )
                if stats and stats.get("raiderio"):
                    score = stats["raiderio"].get("rio_score", 0)
                    entries.append({
                        "name": name,
                        "rank": f"Rio {score}",
                        "lp": score,
                        "sort": score,
                    })

        except Exception:
            continue

    if not entries:
        await msg.edit(
            content=f"❌ Aucune donnée disponible pour **{game.upper()}**."
        )
        return

    entries.sort(key=lambda x: x["sort"], reverse=True)
    lines = [f"🏆 **LEADERBOARD {game.upper()}**\n━━━━━━━━━━━━━━━━━━━━━━"]
    medals = ["🥇", "🥈", "🥉"]

    for i, entry in enumerate(entries[:10]):
        medal = medals[i] if i < 3 else f"`{i+1}.`"
        lines.append(
            f"{medal} **{entry['name']}** — {entry['rank']} ({entry['lp']} LP)"
        )

    await msg.edit(content="\n".join(lines))

def _rank_to_int(tier, division, lp):
    tiers = [
        "IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM",
        "EMERALD", "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER"
    ]
    divisions = {"IV": 0, "III": 1, "II": 2, "I": 3}
    tier_val = tiers.index(tier.upper()) * 400 if tier.upper() in tiers else 0
    div_val = divisions.get(division, 0) * 100
    return tier_val + div_val + lp

# ====================
# HELP
# ====================

@tree.command(name="help", description="Affiche toutes les commandes du bot")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎮 Gaming Recap Bot — Aide",
        color=0x5865F2
    )

    embed.add_field(
        name="📝 Enregistrement",
        value=(
            "`/register_all <pseudo> <tag>` — Enregistre LoL, TFT et Valorant\n"
            "`/register_all <pseudo> <tag> <steam_id>` — Avec CS2\n"
            "`/register <jeu> <pseudo> <tag>` — Enregistre un seul jeu\n"
            "`/register wow <personnage> <royaume>` — Enregistre WoW\n"
            "`/unregister` — Supprime ton profil\n"
            "`/profile` — Affiche ton profil enregistré"
        ),
        inline=False
    )

    embed.add_field(
        name="📊 Stats",
        value=(
            "`/lol [@membre]` — Stats League of Legends\n"
            "`/tft [@membre]` — Stats Teamfight Tactics\n"
            "`/valorant [@membre]` — Stats Valorant\n"
            "`/cs2 [@membre]` — Stats Counter-Strike 2\n"
            "`/wow [@membre]` — Stats World of Warcraft\n"
            "`/recap [@membre]` — Recap complet de la semaine"
        ),
        inline=False
    )

    embed.add_field(
        name="🏆 Classement",
        value=(
            "`/leaderboard lol` — Classement LoL du serveur\n"
            "`/leaderboard tft` — Classement TFT du serveur\n"
            "`/leaderboard cs2` — Classement CS2 du serveur\n"
            "`/leaderboard wow` — Classement WoW (score M+)"
        ),
        inline=False
    )

    embed.add_field(
        name="🔑 Trouver son Riot ID",
        value=(
            "Ton Riot ID c'est ton **pseudo#TAG** visible en haut\n"
            "à droite du client Riot.\n"
            "Exemple : `LimingZhang#EUW`"
        ),
        inline=False
    )

    embed.add_field(
        name="🔑 Trouver son Steam ID 64",
        value=(
            "1. Va sur [steamid.io](https://steamid.io)\n"
            "2. Entre ton pseudo Steam\n"
            "3. Copie la valeur **steamID64**\n\n"
            "⚠️ Ton profil Steam doit être **public** :\n"
            "Steam → Profil → Modifier → Confidentialité\n"
            "→ Profil : Public + Détails des jeux : Public"
        ),
        inline=False
    )

    embed.add_field(
        name="📅 Weekly Recap Automatique",
        value=(
            "Chaque **lundi à 10h**, le bot envoie le recap de tous\n"
            "les membres enregistrés dans `#gaming-stats`.\n"
            "Tu peux aussi le déclencher avec `/recap`."
        ),
        inline=False
    )

    embed.add_field(
        name="🎮 Jeux supportés",
        value=(
            "🟦 **LoL** — Rank, winrate, champion, KDA, dégâts, CS/min, vision, streak\n"
            "🟪 **TFT** — Rank, placement moyen, top 4 rate\n"
            "🟥 **Valorant** — Rank, winrate, agent, KDA, ACS\n"
            "🟩 **CS2** — K/D, HS%, précision, winrate, carte préférée\n"
            "⚔️ **WoW** — ilvl, M+ score, progression raid"
        ),
        inline=False
    )

    embed.set_footer(text="Gaming Recap Bot • Recap automatique tous les lundis à 10h")
    await interaction.response.send_message(embed=embed)
    
from apis.lol import get_lol_stats, get_lol_insights

@tree.command(name="insights", description="Analyse détaillée par champion sur 30 jours")
@app_commands.describe(
    member="Membre du serveur (optionnel)",
    champion="Filtre sur un champion spécifique (optionnel)",
)
async def insights(
    interaction: discord.Interaction,
    member: discord.Member = None,
    champion: str = None,
):
    await interaction.response.defer()
    target = member or interaction.user
    user = get_user(str(target.id))

    if not user or not user.get("lol_username"):
        await interaction.followup.send(
            f"❌ **{target.display_name}** n'a pas de compte LoL enregistré."
        )
        return

    msg = await interaction.followup.send(
        f"⏳ Analyse des 30 derniers jours de **{target.display_name}**..."
    )

    try:
        puuid = get_puuid(user["lol_username"], user["lol_tag"])
        if not puuid:
            await msg.edit(content="❌ PUUID introuvable.")
            return

        data = get_lol_insights(puuid)
        champ_analysis = data.get("champion_analysis", {})

        if not champ_analysis:
            await msg.edit(content="❌ Aucune game ranked trouvée sur 30 jours.")
            return

        # Filtre sur un champion si demandé
        if champion:
            champ_key = next(
                (k for k in champ_analysis if k.lower() == champion.lower()),
                None
            )
            if not champ_key:
                await msg.edit(
                    content=f"❌ Aucune game ranked trouvée sur **{champion}** ces 30 derniers jours."
                )
                return
            champ_analysis = {champ_key: champ_analysis[champ_key]}

        rank = data.get("rank", {})
        solo = rank.get("solo") if rank else None
        rank_str = f"{solo['tier'].capitalize()} {solo['division']} ({solo['lp']} LP)" if solo else "Non ranké"

        lines = [
            f"🔍 **INSIGHTS LOL — {target.display_name}**",
            f"━━━━━━━━━━━━━━━━━━━━━━",
            f"📊 {data['total_games']} games ranked sur 30 jours | {rank_str}",
            f"━━━━━━━━━━━━━━━━━━━━━━",
            "",
        ]

        for champ, s in list(champ_analysis.items())[:5]:
            # Tendance
            if s["trend"] > 5:
                trend_str = f"📈 +{s['trend']}%"
            elif s["trend"] < -5:
                trend_str = f"📉 {s['trend']}%"
            else:
                trend_str = "➡️ stable"

            # Multikills
            multikills = []
            if s.get("penta_kills"):
                multikills.append(f"⚔️ Penta x{s['penta_kills']}")
            if s.get("quadra_kills"):
                multikills.append(f"Quadra x{s['quadra_kills']}")
            if s.get("triple_kills"):
                multikills.append(f"Triple x{s['triple_kills']}")
            if s.get("double_kills"):
                multikills.append(f"Double x{s['double_kills']}")
            multikill_str = " | ".join(multikills) if multikills else None

            # Winrate court/long
            wr_detail = []
            if s.get("short_game_wr") is not None:
                wr_detail.append(f"<25min: {s['short_game_wr']}%")
            if s.get("long_game_wr") is not None:
                wr_detail.append(f">35min: {s['long_game_wr']}%")

            pos_map = {
                "TOP": "Top", "JUNGLE": "Jungle", "MIDDLE": "Mid",
                "BOTTOM": "ADC", "UTILITY": "Support", "UNKNOWN": "?"
            }
            pos = pos_map.get(s.get("main_position", "UNKNOWN"), "?")

            lines.append(f"**{champ}** ({pos}) — {s['games']}G {s['winrate']}% WR {trend_str}")
            lines.append(
                f"  KDA : {s['avg_kda']} ({s['avg_kills']}/{s['avg_deaths']}/{s['avg_assists']}) "
                f"| First blood : {s['first_bloods']}x"
            )
            lines.append(
                f"  Dégâts : {s['avg_damage_per_min']:,}/min ({s['avg_damage_share']}% équipe) "
                f"| CS : {s['avg_cs_per_min']}/min"
            )
            lines.append(
                f"  Gold : {s['avg_gold_per_min']:,}/min ({s['avg_gold_share']}% équipe) "
                f"| Vision : {s['avg_vision_per_min']}/min"
            )
            if wr_detail:
                lines.append(f"  Durée : {' | '.join(wr_detail)}")
            if multikill_str:
                lines.append(f"  {multikill_str}")
            lines.append("")

        await msg.edit(content="\n".join(lines))

    except Exception as e:
        await msg.edit(content=f"❌ Erreur : {e}")



# ====================
# UNREGISTER
# ====================

@tree.command(name="unregister", description="Supprime ton profil du bot")
async def unregister(interaction: discord.Interaction):
    delete_user(str(interaction.user.id))
    await interaction.response.send_message(
        "✅ Ton profil a été supprimé.", ephemeral=True
    )

# ====================
# MAIN
# ====================

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)