import requests
import time
from datetime import datetime, timezone
from deep_translator import GoogleTranslator

# --- CONFIGURATION (SYNDICATE OMNISCIENCE V10 FINAL) ---
TOKEN_TG = "8196511062:AAGyfWcRUk9uw_lc_aQgUW6vLyyRmgF1hcE"
CHAT_ID_TG = "-1003660980986"
TOPIC_ID_TG = 18
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1489314765074595840/BRby0L3L4cfUUGyDpihSBjRlHPpNutFiZWF5mFYU6CpCkjoEA9Hw1A2W0c6LEUgO30i7"

reported_ids = []
translator = GoogleTranslator(source='auto', target='id')

def send_alert(judul, isi, icon="🚨"):
    msg = f"{icon} **{judul}** {icon}\n\n{isi}\n\n#FreedomSyndicate #DomsV10 #GlobalIntel"
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN_TG}/sendMessage", 
                      json={"chat_id": CHAT_ID_TG, "message_thread_id": TOPIC_ID_TG, "text": msg, "parse_mode": "Markdown"}, timeout=15)
        requests.post(DISCORD_WEBHOOK, json={"content": msg, "username": "DOMS OMNISCIENCE FINAL"}, timeout=15)
    except: pass

def check_economic_calendar():
    global reported_ids
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    try:
        events = requests.get(url, timeout=15).json()
        # FIX WARNING DISINI:
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        
        for event in events:
            if event['country'] in ['USD', 'EUR', 'GBP', 'JPY', 'AUD']:
                e_time = datetime.strptime(event['date'], '%Y-%m-%dT%H:%M:%S%z').replace(tzinfo=None)
                diff = (e_time - now_utc).total_seconds() / 60
                id_cal = f"CAL_{event['title']}_{event['date']}"
                
                if 0 < diff <= 45 and id_cal not in reported_ids:
                    impact_label = "🔴 HIGH" if event['impact'] == 'High' else "🟡 MED" if event['impact'] == 'Medium' else "🟢 LOW"
                    txt = (f"📅 **ECONOMIC RADAR**\n"
                           f"━━━━━━━━━━━━━━━━━━━━\n"
                           f"🔥 **Event:** {event['title']}\n"
                           f"📊 **Impact:** {impact_label}\n"
                           f"🕒 **In:** {int(diff)} Menit Lagi\n"
                           f"━━━━━━━━━━━━━━━━━━━━")
                    send_alert("ECONOMIC RADAR", txt, "📢")
                    reported_ids.append(id_cal)
    except: pass

def check_global_intel():
    global reported_ids
    url = "https://cryptopanic.com/api/v1/posts/?kind=news&filter=hot"
    try:
        res = requests.get(url, timeout=15).json()
        for post in res['results'][:7]:
            title_en = post['title']
            if any(key in title_en.lower() for key in ['trump', 'war', 'iran', 'israel', 'oil', 'gold', 'fed', 'missile']):
                if title_en not in reported_ids:
                    try: title_id = translator.translate(title_en)
                    except: title_id = title_en
                    pesan = f"🌍 **GLOBAL NEWS**\n\n🇮🇩 **INDO:** {title_id}\n\n🇺🇸 **ORIG:** {title_en}"
                    send_alert("MARKET BREAKER", pesan, "💥")
                    reported_ids.append(title_en)
    except: pass

if __name__ == "__main__":
    while True:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Doms Patroli...")
        check_economic_calendar()
        check_global_intel()
        time.sleep(120)
