import os
import requests
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

from database import get_all_users
from apis.riot_base import get_puuid
from apis.lol import get_lol_stats
from apis.tft import get_tft_stats
from apis.valorant import get_valorant_stats
from apis.steam import get_cs2_full_stats
from apis.wow import get_wow_stats
from formatter import format_recap

load_dotenv(override=False)

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

def send_webhook(message):
    if not DISCORD_WEBHOOK_URL:
        print("❌ Pas de webhook Discord configuré")
        return
    chunks = [message[i:i+2000] for i in range(0, len(message), 2000)]
    for chunk in chunks:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": chunk})

async def send_weekly_recaps(bot=None):
    print(f"🕐 Weekly recap démarré : {datetime.now()}")
    users = get_all_users()

    if not users:
        print("❌ Aucun utilisateur enregistré")
        return

    now = datetime.now()
    week_start = (now - timedelta(days=7)).strftime("%d/%m")
    week_end = now.strftime("%d/%m/%Y")

    header = (
        f"📅 **WEEKLY GAMING RECAP** — semaine du {week_start} au {week_end}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Recap automatique de tous les joueurs enregistrés !\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    send_webhook(header)

    for user in users:
        try:
            lol_stats = tft_stats = val_stats = cs2_stats = wow_stats = None

            if user.get("lol_username"):
                puuid = get_puuid(user["lol_username"], user["lol_tag"])
                if puuid:
                    lol_stats = get_lol_stats(puuid)

            if user.get("tft_username"):
                puuid = get_puuid(
                    user["tft_username"], user["tft_tag"], use_tft_key=True
                )
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

            message = format_recap(
                lol=lol_stats,
                tft=tft_stats,
                valorant=val_stats,
                cs2=cs2_stats,
                wow=wow_stats,
                username=user["discord_name"],
                week_start=week_start,
                week_end=week_end,
            )

            send_webhook(message)
            send_webhook("─────────────────────────\n")
            print(f"✅ Recap envoyé pour {user['discord_name']}")

        except Exception as e:
            print(f"❌ Erreur pour {user['discord_name']} : {e}")
            continue

def setup_scheduler(bot=None):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        send_weekly_recaps,
        trigger="cron",
        day_of_week="mon",
        hour=10,
        minute=0,
        kwargs={"bot": bot},
    )
    scheduler.start()
    print("✅ Scheduler démarré — recap tous les lundis à 10h")
    return scheduler