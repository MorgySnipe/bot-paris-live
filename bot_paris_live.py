import asyncio
import aiohttp
from datetime import datetime
from telegram import Bot

# --- CONFIGURATION ---
API_KEY = "eeeb45c4722cf452501e32088ed5d8a6"
TELEGRAM_TOKEN = "8145523841:AAERJE40C_QVac0ZAzW--9J8_dLKW3_5Mac"
CHAT_ID = 969925512
CHECK_INTERVAL = 60  # en secondes

alertes_envoyees = set()
matchs_surveilles = {}
bot = Bot(token=TELEGRAM_TOKEN)
dernier_heartbeat = datetime.now()


async def envoyer_message(msg):
    try:
        await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
        print("✅ Message envoyé.")
    except Exception as e:
        print(f"❌ Erreur envoi message Telegram: {e}")


async def get_matchs_live():
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
        shots_on_target >= 2 and
        dangerous_attacks >= 20 and
        corners >= 2 and
        attacks >= 40
    )


async def analyser_match(match):
    fixture = match["fixture"]
    teams = match["teams"]
    stats = await get_stats(fixture["id"])
    minute = fixture["status"]["elapsed"]
    match_id = fixture["id"]
    score = match["goals"]
    home = teams["home"]["name"]
    away = teams["away"]["name"]
    league = match["league"]["name"]
    key = f"{match_id}-{minute}"

    print(f"⏱️ {minute}′ {home} vs {away} ({league})")

    if not stats:
        print("❌ Pas assez de stats")
        return

    if key in alertes_envoyees:
        return

    total_goals = score["home"] + score["away"]

    if 30 <= minute <= 60 and total_goals == 0 and bonnes_conditions(stats):
        alertes_envoyees.add(key)
        matchs_surveilles[match_id] = {"mi_temps": False, "pleine": True, "but": False}
        await envoyer_message(
            f"✨ *PRONOSTIC LIVE : +0.5 BUT (Fin de match)*\n"
            f"📍 {league} | {home} vs {away}\n"
            f"⏱️ {minute}′ | Score : {score['home']} - {score['away']}\n"
            f"📊 Attaques dangereuses : {stats.get('Dangerous Attacks', 'N/A')}, "
            f"Tirs cadrés : {stats.get('Shots on Goal', 'N/A')}, Corners : {stats.get('Corner Kicks', 'N/A')}"
        )

    elif 20 <= minute <= 30 and total_goals == 0 and bonnes_conditions(stats):
        alertes_envoyees.add(key)
        matchs_surveilles[match_id] = {"mi_temps": True, "pleine": False, "but": False}
        await envoyer_message(
            f"🔮 *PRONOSTIC LIVE : +0.5 BUT À LA MI-TEMPS*\n"
            f"📍 {league} | {home} vs {away}\n"
            f"⏱️ {minute}′ | Score : {score['home']} - {score['away']}\n"
            f"📊 Attaques dangereuses : {stats.get('Dangerous Attacks', 'N/A')}, "
            f"Tirs cadrés : {stats.get('Shots on Goal', 'N/A')}, Corners : {stats.get('Corner Kicks', 'N/A')}"
        )


async def get_stats(fixture_id):
    url = f"https://v3.football.api-sports.io/fixtures/statistics?fixture={fixture_id}"
    headers = {"x-apisports-key": API_KEY}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                stats = {}
                for team_stats in data.get("response", []):
                    for stat in team_stats.get("statistics", []):
                        name = stat["type"]
                        value = stat["value"] or 0
                        stats[name] = stats.get(name, 0) + (int(value) if isinstance(value, int) else 0)
                return stats
        except Exception as e:
            print(f"❌ Erreur stats: {e}")
            return {}


async def verifier_resultats(matchs):
    for match in matchs:
        fid = match["fixture"]["id"]
        if fid not in matchs_surveilles:
            continue

        status = match["fixture"]["status"]["short"]
        total_goals = match["goals"]["home"] + match["goals"]["away"]
        infos = matchs_surveilles[fid]

        if infos["pleine"] and status == "FT":
            resultat = "✅ *GAGNÉ*" if total_goals > 0 else "❌ *PERDU*"
            await envoyer_message(f"📊 Résultat +0.5 but *Fin de match* : {resultat}")
            del matchs_surveilles[fid]

        elif infos["mi_temps"] and status == "HT":
            resultat = "✅ *GAGNÉ*" if total_goals > 0 else "❌ *PERDU*"
            await envoyer_message(f"📊 Résultat +0.5 but *Mi-temps* : {resultat}")
            del matchs_surveilles[fid]


async def main():
    global dernier_heartbeat
    await envoyer_message("🤖 Bot Paris Live *lancé* et en écoute des matchs...")

    while True:
        matchs = await get_matchs_live()
        print(f"📡 {len(matchs)} match(s) live à {datetime.now().strftime('%H:%M:%S')}")

        for match in matchs:
            await analyser_match(match)

        await verifier_resultats(matchs)

        # Envoyer un message toutes les 6h pour confirmer que le bot tourne
        if (datetime.now() - dernier_heartbeat).total_seconds() >= 21600:
            await envoyer_message("✅ Bot toujours actif !")
            dernier_heartbeat = datetime.now()

        await asyncio.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())

