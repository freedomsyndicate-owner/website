import requests
import time
from datetime import datetime, timezone, timedelta
from deep_translator import GoogleTranslator

# --- CONFIGURATION (SYNDICATE ETERNAL SYSTEM) ---
TOKEN_TG = "8196511062:AAGyfWcRUk9uw_lc_aQgUW6vLyyRmgF1hcE"
CHAT_ID_TG = "-1003660980986"
TOPIC_ID_TG = 18
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1489314765074595840/BRby0L3L4cfUUGyDpihSBjRlHPpNutFiZWF5mFYU6CpCkjoEA9Hw1A2W0c6LEUgO30i7"

reported_alerts = set()
translator = GoogleTranslator(source='auto', target='id')

def send_alert(judul, isi, icon="🚨"):
    msg = f"{icon} **{judul}** {icon}\n\n{isi}\n\n#FreedomSyndicate #EternalV10 #Doms"
    try:
        # Telegram Post
        requests.post(f"https://api.telegram.org/bot{TOKEN_TG}/sendMessage", 
                      json={"chat_id": CHAT_ID_TG, "message_thread_id": TOPIC_ID_TG, "text": msg, "parse_mode": "Markdown"}, timeout=10)
        # Discord Post
        requests.post(DISCORD_WEBHOOK, json={"content": msg}, timeout=10)
    except: pass

def check_economic_calendar():
    """RADAR SEMUA NEWS: HIJAU, KUNING, MERAH (ALARM H-5 & H-1)"""
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    try:
        events = requests.get(url, timeout=10).json()
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        
        for event in events:
            e_time = datetime.strptime(event['date'], '%Y-%m-%dT%H:%M:%S%z').replace(tzinfo=None)
            diff = (e_time - now_utc).total_seconds() / 60
            
            # TRIGGER ALARM OTOMATIS
            if (1 <= diff <= 1.5) or (5 <= diff <= 5.5):
                alert_id = f"ALARM_{event['title']}_{event['date']}_{int(diff)}"
                
                if alert_id not in reported_alerts:
                    impact = event['impact'].upper()
                    icon = "🔴" if "HIGH" in impact else "🟡" if "MEDIUM" in impact else "🟢"
                    wib = (e_time + timedelta(hours=7)).strftime('%H:%M')
                    
                    txt = (f"{icon} **NEWS ALARM: {int(diff)} MENIT LAGI!**\n"
                           f"━━━━━━━━━━━━━━━━━━━━\n"
                           f"🔥 **DATA:** {event['title']}\n"
                           f"🏛️ **CURR:** {event['country']} | **IMPACT:** {impact}\n"
                           f"🕒 **WAKTU WIB:** {wib}\n"
                           f"━━━━━━━━━━━━━━━━━━━━\n"
                           f"⚠️ *SYNDICATE READY!*")
                    
                    send_alert("OMNISCIENCE RADAR", txt, "📢")
                    reported_alerts.add(alert_id)
    except: pass

def check_global_intel():
    """RADAR SEMUA ISU DUNIA: GEOPOLITIK, MAKRO, BREAKING NEWS"""
    url = "https://cryptopanic.com/api/v1/posts/?kind=news"
    try:
        res = requests.get(url, timeout=10).json()
        for post in res['results'][:15]:
            if post['id'] not in reported_alerts:
                title_en = post['title']
                # Keywords Berita Berpengaruh Market
                keys = ['trump', 'war', 'iran', 'israel', 'oil', 'fed', 'fomc', 'cpi', 'ppi', 'missile', 'nuclear', 'powell', 'rate', 'gold', 'xau', 'russia', 'china', 'inflation', 'attack']
                
                if any(k in title_en.lower() for k in keys):
                    try: indo = translator.translate(title_en)
                    except: indo = title_en
                    
                    pesan = (f"🌍 **BREAKING GLOBAL NEWS**\n\n"
                             f"🇮🇩 **INDO:** {indo}\n\n"
                             f"🇺🇸 **ORIG:** {title_en}\n\n"
                             f"🔗 [DETAIL BERITA]({post['url']})")
                    
                    send_alert("MARKET BREAKER", pesan, "💥")
                    reported_alerts.add(post['id'])
    except: pass

if __name__ == "__main__":
    send_alert("SYSTEM ONLINE", "DOMS OMNISCIENCE V10 ULTRA AKTIF!\n\nPatroli 24/7 Selamanya Tanpa Henti.\nSemua news kalender & Geopolitik masuk radar!", "⚔️")
    
    while True:
        check_economic_calendar()
        check_global_intel()
        # Auto-Clean memory biar gak berat
        if len(reported_alerts) > 1500: reported_alerts.clear()
        time.sleep(30)
