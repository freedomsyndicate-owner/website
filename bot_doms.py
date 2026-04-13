import requests
import time
from datetime import datetime
from deep_translator import GoogleTranslator

# --- CONFIGURATION (FREEDOM SYNDICATE V10) ---
TOKEN_TG = "8196511062:AAGyfWcRUk9uw_lc_aQgUW6vLyyRmgF1hcE"
CHAT_ID_TG = "-1003660980986"
TOPIC_ID_TG = 18
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1489314765074595840/BRby0L3L4cfUUGyDpihSBjRlHPpNutFiZWF5mFYU6CpCkjoEA9Hw1A2W0c6LEUgO30i7"

last_titles = []
translator = GoogleTranslator(source='auto', target='id')

def kirim_update(judul, isi, status="HIGH VOLATILITY ⚠️"):
    format_pesan = f"🚨 **{judul}** 🚨\n\n{isi}\n\n📊 **Status:** {status}\n\n#FreedomSyndicate #DomsV10 #Predator"
    
    payload_tg = {"chat_id": CHAT_ID_TG, "message_thread_id": TOPIC_ID_TG, "text": format_pesan, "parse_mode": "Markdown"}
    payload_dc = {"content": format_pesan, "username": "Doms Predator Intelligence"}

    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN_TG}/sendMessage", json=payload_tg)
        requests.post(DISCORD_WEBHOOK, json=payload_dc)
        print(f"✅ Terkirim: {judul}")
    except: pass

def patroli_doms():
    global last_titles
    try:
        res = requests.get("https://cryptopanic.com/api/v1/posts/?kind=news&filter=hot").json()
        for post in res['results'][:5]:
            title_en = post['title']
            url = post['url']
            
            # RADAR: Trump, Fed, War, Whale, BTC, Gold
            keywords = ['trump', 'fed', 'powell', 'war', 'missile', 'iran', 'israel', 'whale', 'dump', 'pump', 'btc', 'gold', 'xau']
            
            if any(word in title_en.lower() for word in keywords) and title_en not in last_titles:
                # 1. Terjemahkan Judul Otomatis
                try:
                    title_id = translator.translate(title_en)
                except:
                    title_id = title_en

                # 2. Tentukan Kategori
                kategori = "MARKET ALERT"
                if 'trump' in title_en.lower(): kategori = "TRUMP EFFECT 🇺🇸"
                elif 'war' in title_en.lower() or 'missile' in title_en.lower(): kategori = "GEOPOLITICAL WAR 🌍"
                elif 'whale' in title_en.lower(): kategori = "WHALE MOVEMENT 🐳"
                elif 'fed' in title_en.lower() or 'powell' in title_en.lower(): kategori = "FED FUNDAMENTAL 🏦"

                isi = f"🔔 **{kategori}**\n\n🇮🇩 **Berita (Terjemahan):**\n{title_id}\n\n🇺🇸 **Original:**\n_{title_en}_\n\n🔗 Sumber: {url}\n\n⚠️ *Waspada BTC & XAUUSD bisa gonjang-ganjing!*"
                kirim_update("DOMS PREDATOR INTEL", isi)
                
                last_titles.append(title_en)
                if len(last_titles) > 100: last_titles.pop(0)
    except: pass

# Start
kirim_update("DOMS V10 ONLINE: THE PREDATOR", "Sistem Intelligence V10 Aktif!\n✅ Auto-Translate Bahasa Indonesia\n✅ Trump & Fed Watcher\n✅ Geopolitical & Whale Radar", "Monitoring Market... 🦅")

while True:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Doms Predator sedang patroli...")
    patroli_doms()
    time.sleep(300) # Cek setiap 5 menit

