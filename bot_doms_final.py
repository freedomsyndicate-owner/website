import requests
import time
from datetime import datetime

# --- FREEDOM SYNDICATE: GOLD PREDATOR V6 (FULL SYNC PONOROGO) ---
TOKEN_TG = "8196511062:AAGyfWcRUk9uw_lc_aQgUW6vLyyRmgF1hcE"
CHAT_ID_TG = "-1003660980986" 
TOPIC_ID_TG = 18
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1489306608554217736/vTC-HQBFwXWsiBE0WImdB0Uq88WppsSjCb548y5W5aFAubZVYXBgFCEuMLbcB22Hlh7H"

def get_gold_price():
    url = "https://query1.finance.yahoo.com/v8/finance/chart/XAUUSD=X?interval=1m&range=1d"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=10).json()
        curr = res['chart']['result'][0]['meta']['regularMarketPrice']
        d_open = res['chart']['result'][0]['meta']['previousClose']
        return {'last': float(curr), 'open': float(d_open)}
    except: return None

def monitor():
    startup_msg = "🛡️ **DOMS PREDATOR V6 PONOROGO AKTIF!**\nSistem standby monitor XAUUSD (Forex Real-time)... 🦅"
    
    # LAPOR DIRI KE TELEGRAM
    requests.post(f"https://api.telegram.org/bot{TOKEN_TG}/sendMessage", 
                  json={"chat_id": CHAT_ID_TG, "message_thread_id": TOPIC_ID_TG, "text": startup_msg.replace("**", "*"), "parse_mode": "Markdown"})
    
    # LAPOR DIRI KE DISCORD
    requests.post(DISCORD_WEBHOOK, json={"content": startup_msg, "username": "DOMS PREDATOR PONOROGO"})
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🦅 DOMS V6 PONOROGO: ONLINE & REPORTED.")
    last_signal_time = 0

    while True:
        d = get_gold_price()
        if d:
            curr, d_open = d['last'], d['open']
            now_dt = datetime.now() 
            m, h = now_dt.minute, now_dt.hour

            # --- QUARTERLY THEORY (WIB) ---
            if 0 <= m < 15: q_phase = "Q1 - ACCUMULATION"
            elif 15 <= m < 30: q_phase = "Q2 - MANIPULATION"
            elif 30 <= m < 45: q_phase = "Q3 - DISTRIBUTION"
            else: q_phase = "Q4 - REVERSAL"

            # --- MACRO WINDOWS WIB ---
            is_macro = (14 <= h <= 15) or (19 <= h <= 21)
            macro_status = "⚡ MACRO ACTIVE" if is_macro else "💤 OFF-MACRO"

            side, setup = "", ""
            if q_phase.startswith("Q3") or is_macro:
                if curr > d_open: 
                    side = "SELL 📉"
                    setup = "ICT PREMIUM REJECTION"
                elif curr < d_open:
                    side = "BUY 📈"
                    setup = "ICT DISCOUNT REJECTION"

            if side and (time.time() - last_signal_time > 1200):
                tp = curr + 3.0 if "BUY" in side else curr - 3.0
                sl = curr - 1.2 if "BUY" in side else curr + 1.2
                
                msg = (f"🦅 **DOMS PREDATOR PONOROGO** 🦅\n"
                       f"━━━━━━━━━━━━━━━━━━━━\n"
                       f"🔥 **Setup:** {setup}\n"
                       f"📥 **Action:** {side}\n"
                       f"🎯 **Price:** {curr:,.2f} (XAUUSD)\n"
                       f"🛑 **SL:** {sl:,.2f} | 🎯 **TP:** {tp:,.2f}\n"
                       f"━━━━━━━━━━━━━━━━━━━━\n"
                       f"🏛️ **Phase:** {q_phase}\n"
                       f"🕒 **Time:** {macro_status}\n"
                       f"🧠 **Bias:** {'BULLISH' if curr > d_open else 'BEARISH'}\n"
                       f"⏰ **Update:** {now_dt.strftime('%H:%M:%S')} WIB")

                try:
                    requests.post(f"https://api.telegram.org/bot{TOKEN_TG}/sendMessage", 
                                  json={"chat_id": CHAT_ID_TG, "message_thread_id": TOPIC_ID_TG, "text": msg.replace("**", "*"), "parse_mode": "Markdown"})
                    requests.post(DISCORD_WEBHOOK, json={"content": msg, "username": "DOMS PREDATOR PONOROGO"})
                    print(f"[{now_dt.strftime('%H:%M:%S')}] Sinyal Terkirim!")
                    last_signal_time = time.time()
                except: pass

        time.sleep(20)

if __name__ == "__main__":
    monitor()
