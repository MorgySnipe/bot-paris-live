import asyncio
import aiohttp
from datetime import datetime
from telegram import Bot
import functools
print = functools.partial(print, flush=True)

# --- CONFIGURATION ---
API_KEY = "eeeb45c4722cf452501e32088ed5d8a6"
TELEGRAM_TOKEN = "8145523841:AAERJE40C_QVac0ZAzW--9J8_dLKW3_5Mac"
CHAT_ID = 969925512
CHECK_INTERVAL = 60  # secondes

alertes_envoyees = set()
matchs_surveilles = {}
bot = Bot(token=TELEGRAM_TOKEN)
dernier_heartbeat = datetime.now()

# ✅ Liste blanche des ligues fiables
ligues_autorisees = {
    "UEFA Champions League"
}

def envoyer_message(msg):
    try:
        bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
        print("✅ Message envoyé.")
    except Exception as e:
        print(f"❌ Erreur envoi message Telegram: {e}")

async def get_matchs_live():
    print("📡 Appel API : récupération des matchs live...")
    url = "https://v3.football.api-sports.io/fixtures?live=all"
    headers = {"x-apisports-key": API_KEY}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                return data.get("response", [])
        except Exception as e:
            print(f"❌ Erreur récupération API: {e}")
            return []

def bonnes_conditions(stats):
    shots_on_target = stats.get("Shots on Goal", 0)
    dangerous_attacks = stats.get("Dangerous Attacks", 0)
    corners = stats.get("Corner Kicks", 0)
    attacks = stats.get("Attacks", 0)
    print(f"Stats reçues: SoG={shots_on_target}, DA={dangerous_attacks}, CK={corners}, ATT={attacks}")
    return (
        shots_on_target >= 1 and
        dangerous_attacks >= 15 and
        corners >= 1 and
        attacks >= 30
    )

async def analyser_match(match):
    fixture = match["fixture"]
    teams = match["teams"]
    match_id = fixture["id"]
    minute = fixture["status"]["elapsed"]
    score = match["goals"]
    home = teams["home"]["name"]
    away = teams["away"]["name"]
    league = match["league"]["name"]
    key = f"{match_id}-{minute}"

    if league not in ligues_autorisees:
        print(f"⏭️ Ligue ignorée : {league}")
        return

    stats = await get_stats(match_id)
    print(f"⏱️ {minute}′ {home} vs {away} ({league})")

    if not stats or key in alertes_envoyees:
        return

    total_goals = score["home"] + score["away"]

    if 30 <= minute <= 60 and total_goals == 0 and bonnes_conditions(stats):
        alertes_envoyees.add(key)
        matchs_surveilles[match_id] = {"mi_temps": False, "pleine": True}
        envoyer_message(
            f"✨ *PRONOSTIC LIVE : +0.5 BUT (Fin de match)*\n"
            f"📍 {league} | {home} vs {away}\n"
            f"⏱️ {minute}′ | Score : {score['home']} - {score['away']}\n"
            f"📊 Attaques dangereuses : {stats.get('Dangerous Attacks', 'N/A')}, "
            f"Tirs cadrés : {stats.get('Shots on Goal', 'N/A')}, Corners : {stats.get('Corner Kicks', 'N/A')}"
        )

    elif 20 <= minute <= 30 and total_goals == 0 and bonnes_conditions(stats):
        alertes_envoyees.add(key)
        matchs_surveilles[match_id] = {"mi_temps": True, "pleine": False}
        envoyer_message(
            f"🔮 *PRONOSTIC LIVE : +0.5 BUT À LA MI-TEMPS*\n"

