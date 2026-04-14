import requests
import time
from datetime import datetime
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
        # Kirim ke Telegram Topic
        requests.post(f"https://api.telegram.org/bot{TOKEN_TG}/sendMessage", 
                      json={"chat_id": CHAT_ID_TG, "message_thread_id": TOPIC_ID_TG, "text": msg, "parse_mode": "Markdown"}, timeout=15)
        # Kirim ke Discord
        requests.post(DISCORD_WEBHOOK, json={"content": msg, "username": "DOMS OMNISCIENCE FINAL"}, timeout=15)
    except Exception as e:
        print(f"Error sending message: {e}")

def check_economic_calendar():
    """MATA-MATA KALENDER: HIJAU, KUNING, MERAH SEMUA MASUK!"""
    global reported_ids
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    try:
        events = requests.get(url, timeout=15).json()
        now_utc = datetime.utcnow()
        for event in events:
            # Pantau Major Currency (USD, EUR, GBP, JPY, AUD)
            if event['country'] in ['USD', 'EUR', 'GBP', 'JPY', 'AUD']:
                e_time = datetime.strptime(event['date'], '%Y-%m-%dT%H:%M:%S%z').replace(tzinfo=None)
                diff = (e_time - now_utc).total_seconds() / 60
                id_cal = f"CAL_{event['title']}_{event['date']}"
                
                # ALERTA 45 MENIT SEBELUM DATA KELUAR
                if 0 < diff <= 45 and id_cal not in reported_ids:
                    impact_label = "🔴 HIGH (MERAH)" if event['impact'] == 'High' else \
                                   "🟡 MEDIUM (KUNING)" if event['impact'] == 'Medium' else \
                                   "🟢 LOW (HIJAU)"
                    
                    txt = (f"📅 **ECONOMIC CALENDAR RADAR**\n"
                           f"━━━━━━━━━━━━━━━━━━━━\n"
                           f"🔥 **Event:** {event['title']}\n"
                           f"🏛️ **Currency:** {event['country']}\n"
                           f"📊 **Impact:** {impact_label}\n"
                           f"🕒 **Countdown:** {int(diff)} Menit Lagi\n"
                           f"━━━━━━━━━━━━━━━━━━━━\n"
                           f"⚠️ *Siapkan Margin, Market Mau Goyang!*")
                    
                    send_alert("ECONOMIC RADAR", txt, "📢")
                    reported_ids.append(id_cal)
    except: pass

def check_global_intel():
    """INTELIJEN DUNIA: TRUMP, PERANG, MINYAK, HORMUZ"""
    global reported_ids
    url = "https://cryptopanic.com/api/v1/posts/?kind=news&filter=hot"
    try:
        res = requests.get(url, timeout=15).json()
        for post in res['results'][:7]:
            title_en = post['title']
            url_news = post['url']
            
            # KEYWORDS RADAR GEOPOLITIK
            keywords = ['trump', 'war', 'iran', 'israel', 'hormuz', 'oil', 'gold', 'fed', 'powell', 'missile', 'attack', 'nuclear', 'biden', 'china']
            
            if any(key in title_en.lower() for key in keywords) and title_en not in reported_ids:
                try: 
                    title_id = translator.translate(title_en)
                except: 
                    title_id = title_en

                cat = "GLOBAL INTEL"
                if any(w in title_en.lower() for w in ['war', 'missile', 'attack', 'nuclear']): cat = "WAR ALERT 🛡️"
                elif 'trump' in title_en.lower(): cat = "TRUMP EFFECT 🇺🇸"
                elif 'oil' in title_en.lower() or 'hormuz' in title_en.lower(): cat = "ENERGY CRISIS 🛢️"

                pesan = (f"🌍 **{cat}**\n\n"
                         f"🇮🇩 **INDO:** {title_id}\n\n"
                         f"🇺🇸 **ORIG:** _{title_en}_\n\n"
                         f"🔗 [Link Detail]({url_news})")
                
                send_alert("GLOBAL MARKET BREAKER", pesan, "💥")
                reported_ids.append(title_en)
    except: pass

if __name__ == "__main__":
    send_alert("SYSTEM ONLINE", "DOMS OMNISCIENCE V10 FINAL AKTIF!\n\n✅ Semua News (Hijau/Kuning/Merah)\n✅ Radar Perang & Geopolitik\n✅ Radar Trump & Minyak\n✅ Auto-Translate Bahasa Indonesia\n\nSelamat berjuang, Freedom Syndicate! 🦅", "🛡️")
    
    while True:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Doms Intelligence Patroli...")
        check_economic_calendar()
        check_global_intel()
        
        # Jaga list biar gak bengkak
        if len(reported_ids) > 400: reported_ids = reported_ids[200:]
        
        time.sleep(120) # Patroli tiap 2 menit
