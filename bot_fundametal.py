import requests
import time
from datetime import datetime, timezone, timedelta
from deep_translator import GoogleTranslator

# --- CONFIGURATION (SYNDICATE SUPREME FULL DATA) ---
TOKEN_TG = "8196511062:AAGyfWcRUk9uw_lc_aQgUW6vLyyRmgF1hcE"
CHAT_ID_TG = "-1003660980986"
TOPIC_ID_TG = 18
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1489314765074595840/BRby0L3L4cfUUGyDpihSBjRlHPpNutFiZWF5mFYU6CpCkjoEA9Hw1A2W0c6LEUgO30i7"

reported_alerts = set()
translator = GoogleTranslator(source='auto', target='id')

def send_alert(judul, isi, icon="🚨", image_url=None, impact="LOW"):
    msg = f"{icon} **{judul}** {icon}\n\n{isi}\n\n#FreedomSyndicate #FullDataV10 #Doms"
    try:
        # Telegram
        tg_url = f"https://api.telegram.org/bot{TOKEN_TG}/"
        if image_url:
            requests.post(tg_url + "sendPhoto", json={"chat_id": CHAT_ID_TG, "message_thread_id": TOPIC_ID_TG, "photo": image_url, "caption": msg, "parse_mode": "Markdown"}, timeout=10)
        else:
            requests.post(tg_url + "sendMessage", json={"chat_id": CHAT_ID_TG, "message_thread_id": TOPIC_ID_TG, "text": msg, "parse_mode": "Markdown"}, timeout=10)
        
        # Discord Webhook (Tag everyone HANYA untuk HIGH, tapi SEMUA lapor)
        tag = "@traders" if impact == "HIGH" else ""
        color = 15158332 if impact == "HIGH" else 15844367 if impact == "MEDIUM" else 3066993
        payload = {"content": tag, "embeds": [{"title": judul, "description": isi, "color": color}]}
        if image_url: payload["embeds"][0]["image"] = {"url": image_url}
        requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)
    except: pass

def check_economic_calendar():
    """RADAR KOMPLIT: ALARM & LIVE RESULT SEMUA IMPACT (🟢🟡🔴)"""
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    try:
        events = requests.get(url, timeout=10).json()
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        
        for event in events:
            e_time = datetime.strptime(event['date'], '%Y-%m-%dT%H:%M:%S%z').replace(tzinfo=None)
            diff = (e_time - now_utc).total_seconds() / 60
            impact = event['impact'].upper()
            
            # 1. TRIGGER ALARM SEMUA IMPACT (H-5 & H-1)
            if (1 <= diff <= 1.5) or (5 <= diff <= 5.5):
                alert_id = f"ALARM_{event['title']}_{event['date']}_{int(diff)}"
                if alert_id not in reported_alerts:
                    wib = (e_time + timedelta(hours=7)).strftime('%H:%M')
                    icon = "🔴" if "HIGH" in impact else "🟡" if "MEDIUM" in impact else "🟢"
                    txt = f"⚡ **NEWS ALARM: {int(diff)} MENIT LAGI**\n\n🔥 **DATA:** {event['title']}\n🏛️ **CURR:** {event['country']} | **IMPACT:** {impact}\n🕒 **WAKTU WIB:** {wib}\n\n⚠️ *SYNDICATE READY!*"
                    send_alert("OMNISCIENCE RADAR", txt, icon, impact=impact)
                    reported_alerts.add(alert_id)

            # 2. TRIGGER LIVE RESULT SEMUA IMPACT (ACTUAL DATA)
            # Dicek dari menit ke-0 sampai 5 menit setelah rilis
            if (-5 <= diff <= 0):
                res_id = f"RESULT_{event['title']}_{event['date']}"
                if res_id not in reported_alerts:
                    # Hanya kirim jika data 'actual' sudah keluar dari server
                    actual = event.get('actual')
                    if actual:
                        forecast = event.get('forecast', 'N/A')
                        previous = event.get('previous', 'N/A')
                        icon = "📊"
                        
                        txt = (f"📈 **DATA RELEASED: {event['title']}**\n"
                               f"━━━━━━━━━━━━━━━━━━━━\n"
                               f"📌 **Actual:** `{actual}`\n"
                               f"🎯 **Forecast:** {forecast}\n"
                               f"📜 **Previous:** {previous}\n"
                               f"━━━━━━━━━━━━━━━━━━━━\n"
                               f"🏛️ **Curr:** {event['country']} | **Impact:** {impact}\n"
                               f"#{event['country']} #Gold #Forex")
                        send_alert("SUPREME DATA RESULT", txt, icon, impact=impact)
                        reported_alerts.add(res_id)
    except: pass

def check_global_intel():
    """RADAR GEOPOLITIK BRUTAL"""
    url = "https://cryptopanic.com/api/v1/posts/?kind=news"
    try:
        res = requests.get(url, timeout=10).json()
        for post in res['results'][:15]:
            if post['id'] not in reported_alerts:
                title_en = post['title']
                keys = ['trump', 'war', 'iran', 'israel', 'oil', 'fed', 'fomc', 'cpi', 'ppi', 'missile', 'nuclear', 'attack', 'china', 'russia', 'gold', 'xau']
                
                if any(k in title_en.lower() for k in keys):
                    try: indo = translator.translate(title_en)
                    except: indo = title_en
                    img = post.get('metadata', {}).get('image')
                    
                    pesan = (f"🌍 **BREAKING GLOBAL NEWS**\n\n"
                             f"🇮🇩 **INDO:** {indo}\n\n"
                             f"🇺🇸 **ORIG:** {title_en}\n\n"
                             f"🔗 [BACA DETAIL]({post['url']})")
                    
                    send_alert("MARKET BREAKER", pesan, "💥", image_url=img, impact="HIGH")
                    reported_alerts.add(post['id'])
    except: pass

if __name__ == "__main__":
    send_alert("SYSTEM SUPREME ONLINE", "V10 FULL DATA AKTIF!\n\n✅ Alarm 🟢🟡🔴 (H-5 & H-1)\n✅ Live Result (Actual/Forecast/Prev)\n✅ Geopolitik Visual\n✅ Auto-Clean Memory", "🦅", impact="MEDIUM")
    while True:
        check_economic_calendar()
        check_global_intel()
        if len(reported_alerts) > 2000: reported_alerts.clear()
        time.sleep(30)
