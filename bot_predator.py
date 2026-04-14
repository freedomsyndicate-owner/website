import requests
import time
from datetime import datetime
from tradingview_ta import TA_Handler, Interval

# --- FREEDOM SYNDICATE: GLOBAL PREDATOR V10 (PURE XAMD EDITION) ---
TOKEN_TG = "8196511062:AAGyfWcRUk9uw_lc_aQgUW6vLyyRmgF1hcE"
CHAT_ID_TG = "-1003660980986" 
TOPIC_ID_TG = 18
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1489306608554217736/vTC-HQBFwXWsiBE0WImdB0Uq88WppsSjCb548y5W5aFAubZVYXBgFCEuMLbcB22Hlh7H"

# DAFTAR PAIR HIGH PROBABILITY (OANDA & BINANCE)
PAIRS = {
    "XAUUSD": {"ex": "OANDA", "scr": "cfd", "tp": 5.0, "sl": 2.0},
    "BTCUSDT": {"ex": "BINANCE", "scr": "crypto", "tp": 500.0, "sl": 200.0},
    "USDJPY": {"ex": "OANDA", "scr": "forex", "tp": 0.350, "sl": 0.150},
    "GBPUSD": {"ex": "OANDA", "scr": "forex", "tp": 0.0045, "sl": 0.0015},
    "EURUSD": {"ex": "OANDA", "scr": "forex", "tp": 0.0040, "sl": 0.0012},
    "USDCHF": {"ex": "OANDA", "scr": "forex", "tp": 0.0035, "sl": 0.0012},
    "AUDUSD": {"ex": "OANDA", "scr": "forex", "tp": 0.0040, "sl": 0.0015},
    "NZDUSD": {"ex": "OANDA", "scr": "forex", "tp": 0.0040, "sl": 0.0015}
}

def send_to_syndicate(msg):
    try:
        # Kirim ke Telegram (Topic Syndicate)
        requests.post(f"https://api.telegram.org/bot{TOKEN_TG}/sendMessage", 
                      json={"chat_id": CHAT_ID_TG, "message_thread_id": TOPIC_ID_TG, 
                            "text": msg.replace("**", "*"), "parse_mode": "Markdown"}, timeout=10)
        # Kirim ke Discord Webhook
        requests.post(DISCORD_WEBHOOK, json={"content": msg, "username": "DOMS PREDATOR FINAL"}, timeout=10)
    except: pass

def get_data(symbol, exchange, screener):
    try:
        handler = TA_Handler(symbol=symbol, screener=screener, exchange=exchange, interval=Interval.INTERVAL_1_MINUTE)
        analysis = handler.get_analysis()
        return {
            'last': analysis.indicators['close'],
            'open': analysis.indicators['open'], # Midnight Open
            'high': analysis.indicators['high'],
            'low': analysis.indicators['low']
        }
    except: return None

def monitor():
    startup_time = datetime.now().strftime('%H:%M:%S')
    startup_msg = ("🔥 **DOMS PREDATOR V10: THE GODFATHER ONLINE** 🔥\n"
                   "━━━━━━━━━━━━━━━━━━━━\n"
                   "💻 **Mode:** LAPTOP ENGINE (PONOROGO SYNC)\n"
                   "🎯 **Assets:** XAU, BTC, UJ, GU, EU, UCHF, AU, NU\n"
                   "🧠 **Logic:** PURE XAMD / AMDX / JUDAS SWING\n"
                   "⏰ **Time:** " + startup_time + " WIB\n"
                   "━━━━━━━━━━━━━━━━━━━━\n"
                   "Gak usah debat lagi, Predator sudah standby. Sukses buat kita, Cok! 🚀")
    
    send_to_syndicate(startup_msg)
    print(f"[{startup_time}] PREDATOR V10 FINAL ONLINE. Monitoring 8 Pairs...")
    
    last_signals = {pair: 0 for pair in PAIRS}

    while True:
        for pair, config in PAIRS.items():
            data = get_data(pair, config['ex'], config['scr'])
            if data:
                curr, m_open = data['last'], data['open']
                now = datetime.now()
                h = now.hour

                # MACRO WINDOWS WIB (Time is the filter!)
                is_macro = (7 <= h <= 9) or (14 <= h <= 16) or (19 <= h <= 21)
                
                side, cycle = "", ""
                
                # SIKLUS XAMD / AMDX (JUDAS SWING DETECTION)
                if is_macro:
                    # AMDX SELL: Harga di atas Open & Nge-grab High harian
                    if curr > m_open and curr >= data['high']:
                        side, cycle = "SELL 📉", "AMDX: MANIPULATION HIGH (JUDAS)"
                    # AMDX BUY: Harga di bawah Open & Nge-grab Low harian
                    elif curr < m_open and curr <= data['low']:
                        side, cycle = "BUY 📈", "AMDX: MANIPULATION LOW (JUDAS)"

                # Execution dengan Cooldown 30 Menit biar gak nyepam
                if side and (time.time() - last_signals[pair] > 1800):
                    tp = curr + config['tp'] if "BUY" in side else curr - config['tp']
                    sl = curr - config['sl'] if "BUY" in side else curr + config['sl']
                    
                    msg = (f"🦅 **GLOBAL SIGNAL: {pair}** 🦅\n"
                           f"━━━━━━━━━━━━━━━━━━━━\n"
                           f"🔥 **Logic:** {cycle}\n"
                           f"📥 **Action:** {side}\n"
                           f"🎯 **Price:** {curr:,.4f}\n"
                           f"🛑 **SL:** {sl:,.4f} | 🎯 **TP:** {tp:,.2f}\n"
                           f"━━━━━━━━━━━━━━━━━━━━\n"
                           f"🏛️ **Market:** {config['ex']}\n"
                           f"🕒 **Macro Status:** ACTIVE\n"
                           f"⏰ **Update:** {now.strftime('%H:%M:%S')} WIB")

                    send_to_syndicate(msg)
                    last_signals[pair] = time.time()
                    print(f"[{now.strftime('%H:%M:%S')}] Signal Sent: {pair} {side}")
        
        time.sleep(15) # Scan all 8 pairs every 15 seconds

if __name__ == "__main__":
    monitor()
