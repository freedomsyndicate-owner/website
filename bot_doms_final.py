import requests
import time
from datetime import datetime

# --- FREEDOM SYNDICATE: ICT SUPREME PREDATOR V5 (FULLY SYNCED & UPDATED) ---
TOKEN_TG = "8196511062:AAGyfWcRUk9uw_lc_aQgUW6vLyyRmgF1hcE"
CHAT_ID_TG = "-1003660980986" 
TOPIC_ID_TG = 18
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1489306608554217736/vTC-HQBFwXWsiBE0WImdB0Uq88WppsSjCb548y5W5aFAubZVYXBgFCEuMLbcB22Hlh7H"

def get_market_data():
    url = "https://api.binance.com/api/v3/ticker/24hr?symbol=PAXGUSDT"
    try:
        res = requests.get(url, timeout=5).json()
        return {'last': float(res['lastPrice']), 'open': float(res['openPrice']), 'h': float(res['highPrice']), 'l': float(res['lowPrice'])}
    except: return None

def monitor():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🛡️ ICT SUPREME V5 ONLINE & SYNCED.")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔗 DESTINATION: Telegram & Discord #signal-market")
    last_signal_time = 0

    while True:
        d = get_market_data()
        if d:
            curr, d_open, d_high, d_low = d['last'], d['open'], d['h'], d['l']
            now_dt = datetime.now()
            m = now_dt.minute
            h = now_dt.hour

            # --- 1. QUARTERLY THEORY PHASE (90-MIN MICRO CYCLES) ---
            if 0 <= m < 15: q_phase = "Q1 - ACCUMULATION"
            elif 15 <= m < 30: q_phase = "Q2 - MANIPULATION (JUDAS)"
            elif 30 <= m < 45: q_phase = "Q3 - DISTRIBUTION (EXPANSION)"
            else: q_phase = "Q4 - REVERSAL / X-EXPANSION"

            # --- 2. MACRO WINDOWS (UTC+8 / MALAYSIA TIME) ---
            is_macro = (15 <= h <= 16) or (20 <= h <= 22) or (0 <= h <= 1)
            macro_status = "⚡ MACRO ACTIVE" if is_macro else "💤 OFF-MACRO"

            # --- 3. BIAS DAILY & PO3 LOGIC ---
            bias = "BULLISH" if curr > d_open else "BEARISH"
            
            # Eksekusi Sniper (Cooldown 20 Menit agar High Quality)
            if time.time() - last_signal_time > 1200: 
                side, setup = "", ""
                
                # Logic: Entry di Q3/Macro setelah pembersihan Liquidity (Sweep)
                if q_phase.startswith("Q3") or is_macro:
                    if bias == "BEARISH" and curr > d_open: # Premium Sell
                        side = "SELL 📉"
                        setup = "ICT INTRADAY (PREMIUM REJECTION)"
                    elif bias == "BULLISH" and curr < d_open: # Discount Buy
                        side = "BUY 📈"
                        setup = "ICT INTRADAY (DISCOUNT REJECTION)"

                if side:
                    tp = curr + 4.5 if "BUY" in side else curr - 4.5
                    sl = curr - 1.8 if "BUY" in side else curr + 1.8
                    
                    msg = (f"🛡️ **DOMS SUPREME PREDATOR** 🛡️\n"
                           f"━━━━━━━━━━━━━━━━━━━━\n"
                           f"🔥 **Setup:** {setup}\n"
                           f"📥 **Action:** {side}\n"
                           f"🎯 **Price:** {curr:,.2f}\n"
                           f"🛑 **SL:** {sl:,.2f} | 🎯 **TP:** {tp:,.2f}\n"
                           f"━━━━━━━━━━━━━━━━━━━━\n"
                           f"🏛️ **Phase:** {q_phase}\n"
                           f"🕒 **Time:** {macro_status}\n"
                           f"🧠 **Bias:** {bias} | Daily Open Filter Locked.\n"
                           f"⏰ **Update:** {now_dt.strftime('%H:%M:%S')} MYT")

                    # BROADCAST KE TELEGRAM
                    requests.post(f"https://api.telegram.org/bot{TOKEN_TG}/sendMessage", 
                                  json={"chat_id": CHAT_ID_TG, "message_thread_id": TOPIC_ID_TG, "text": msg.replace("**", "*"), "parse_mode": "Markdown"})
                    
                    # BROADCAST KE DISCORD (DENGAN IDENTITAS BARU)
                    requests.post(DISCORD_WEBHOOK, json={
                        "content": msg,
                        "username": "DOMS SUPREME PREDATOR",
                        "avatar_url": "https://i.imgur.com/8nNf669.png"
                    })
                    
                    print(f"[{now_dt.strftime('%H:%M:%S')}] {side} Sent to Telegram & Discord!")
                    last_signal_time = time.time()

        time.sleep(10) # Hunting Mode

if __name__ == "__main__":
    monitor()
