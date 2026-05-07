import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime, timedelta

from database import init_db, register_game, get_user, get_all_users, delete_user
from apis.riot import get_puuid, get_lol_stats, get_tft_stats
from apis.valorant import get_valorant_stats
from apis.steam import get_cs2_full_stats
from apis.wow import get_wow_stats
from formatter import format_recap, format_stats_embed
from scheduler import setup_scheduler


load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", 0))

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
    setup_scheduler(bot)  # ← ajoute cette ligne
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

@tree.command(name="register", description="Enregistre ton profil de jeu")
@app_commands.describe(
    game="Le jeu à enregistrer (lol, tft, valorant, cs2, wow)",
    username="Ton pseudo (ou Steam URL pour CS2)",
    tag="Ton tag (ex: EUW) — pas nécessaire pour CS2 et WoW",
    realm="Ton royaume WoW (seulement pour WoW)",
    region="Ta région (eu, na, kr) — défaut: eu",
)
async def register(
    interaction: discord.Interaction,
    game: str,
    username: str,
    tag: str = None,
    realm: str = None,
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

        puuid = None
        if game in ("lol", "tft"):
            await interaction.followup.send(
                f"⏳ Vérification de ton compte Riot...", ephemeral=True
            )
            puuid = get_puuid(username, tag, region)
            if not puuid:
                await interaction.followup.send(
                    f"❌ Compte Riot introuvable : `{username}#{tag}`",
                    ephemeral=True
                )
                return

        register_game(
            discord_id, discord_name, game,
            username=username, tag=tag
        )
        await interaction.followup.send(
            f"✅ **{game.upper()}** enregistré : `{username}#{tag}`",
            ephemeral=True
        )

    elif game == "cs2":
        steam_id = username.strip()
        if "steamcommunity.com" in steam_id:
            await interaction.followup.send(
                "❌ Entre ton Steam ID 64 directement (ex: `76561199828743581`)",
                ephemeral=True
            )
            return

        register_game(discord_id, discord_name, game, steam_id=steam_id)
        await interaction.followup.send(
            f"✅ **CS2** enregistré : Steam ID `{steam_id}`",
            ephemeral=True
        )

    elif game == "wow":
        if not realm:
            await interaction.followup.send(
                "❌ Le royaume est requis pour WoW (ex: `/register wow Thrall Dalaran`)",
                ephemeral=True
            )
            return

        register_game(
            discord_id, discord_name, game,
            character=username, realm=realm, region=region
        )
        await interaction.followup.send(
            f"✅ **WoW** enregistré : `{username}` sur `{realm}` ({region.upper()})",
            ephemeral=True
        )

    else:
        await interaction.followup.send(
            "❌ Jeu non reconnu. Choix disponibles : `lol`, `tft`, `valorant`, `cs2`, `wow`",
            ephemeral=True
        )

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
            f"Utilise `/register` pour commencer !",
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
        lines.append(f"⚔️ **WoW** : `{user['wow_character']}` sur `{user['wow_realm']}` ({user['wow_region'].upper()})")

    if len(lines) == 1:
        lines.append("Aucun jeu enregistré. Utilise `/register` !")

    await interaction.response.send_message("\n".join(lines), ephemeral=True)

# ====================
# STATS PAR JEU
# ====================

async def fetch_and_send(interaction, target, game):
    await interaction.response.defer()
    user = get_user(str(target.id))

    if not user:
        await interaction.followup.send(
            f"❌ **{target.display_name}** n'a pas de profil enregistré. "
            f"Utilise `/register` pour commencer !"
        )
        return

    msg = await interaction.followup.send(f"⏳ Récupération des stats **{game.upper()}**...")

    stats = None
    result = None

    try:
        if game == "lol" and user.get("lol_username"):
            puuid = get_puuid(user["lol_username"], user["lol_tag"])
            stats = get_lol_stats(puuid) if puuid else None

        elif game == "tft" and user.get("tft_username"):
            puuid = get_puuid(user["tft_username"], user["tft_tag"])
            stats = get_tft_stats(puuid) if puuid else None

        elif game == "valorant" and user.get("valorant_username"):
            stats = get_valorant_stats(
                user["valorant_username"], user["valorant_tag"]
            )

        elif game == "cs2" and user.get("steam_id"):
            stats = get_cs2_full_stats(user["steam_id"])

        elif game == "wow" and user.get("wow_character"):
            stats = get_wow_stats(
                user["wow_character"], user["wow_realm"], user["wow_region"]
            )

        else:
            await msg.edit(content=f"❌ **{target.display_name}** n'a pas de compte **{game.upper()}** enregistré.")
            return

        result = format_stats_embed(game, stats, target.display_name)

    except Exception as e:
        result = f"❌ Erreur lors de la récupération des stats : {e}"

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
            puuid = get_puuid(user["tft_username"], user["tft_tag"])
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
        message = f"❌ Erreur lors de la génération du recap : {e}"

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

    msg = await interaction.followup.send(f"⏳ Génération du leaderboard **{game.upper()}**...")
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
                            "sort": _rank_to_int(solo["tier"], solo["division"], solo["lp"]),
                        })

            elif game == "tft" and user.get("tft_username"):
                puuid = get_puuid(user["tft_username"], user["tft_tag"])
                if puuid:
                    stats = get_tft_stats(puuid)
                    rank = stats.get("rank", {})
                    if rank and rank.get("tier") != "UNRANKED":
                        entries.append({
                            "name": name,
                            "rank": f"{rank['tier'].capitalize()} {rank['division']}",
                            "lp": rank["lp"],
                            "sort": _rank_to_int(rank["tier"], rank["division"], rank["lp"]),
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

        except Exception:
            continue

    if not entries:
        await msg.edit(content=f"❌ Aucune donnée disponible pour **{game.upper()}**.")
        return

    entries.sort(key=lambda x: x["sort"], reverse=True)

    lines = [f"🏆 **LEADERBOARD {game.upper()}**\n━━━━━━━━━━━━━━━━━━━━━━"]
    medals = ["🥇", "🥈", "🥉"]

    for i, entry in enumerate(entries[:10]):
        medal = medals[i] if i < 3 else f"`{i+1}.`"
        lines.append(f"{medal} **{entry['name']}** — {entry['rank']} ({entry['lp']} LP)")

    await msg.edit(content="\n".join(lines))

def _rank_to_int(tier, division, lp):
    tiers = ["IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM", "EMERALD", "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER"]
    divisions = {"IV": 0, "III": 1, "II": 2, "I": 3}
    tier_val = tiers.index(tier.upper()) * 400 if tier.upper() in tiers else 0
    div_val = divisions.get(division, 0) * 100
    return tier_val + div_val + lp

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