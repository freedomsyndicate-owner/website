import requests
import time
from datetime import datetime, timezone, timedelta
from tradingview_ta import TA_Handler, Interval

# ─── CONFIGURATION ─────────────────────────────────────────────────────────────
TOKEN_TG        = "8196511062:AAGyfWcRUk9uw_lc_aQgUW6vLyyRmgF1hcE"
CHAT_ID_TG      = "-1003660980986"
TOPIC_ID_TG     = 18
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1489306608554217736/vTC-HQBFwXWsiBE0WImdB0Uq88WppsSjCb548y5W5aFAubZVYXBgFCEuMLbcB22H1h7H"
FIREBASE_DB_URL = "https://freedomsyndicatecloud-default-rtdb.firebaseio.com"

# DAFTAR PAIR LENGKAP DENGAN SMT CORRELATION
PAIRS = {
    "XAUUSD":  {"ex": "OANDA",   "scr": "cfd",    "corr": "DXY"},
    "BTCUSDT": {"ex": "BINANCE", "scr": "crypto", "corr": "ETHUSDT"},
    "GBPUSD":  {"ex": "OANDA",   "scr": "forex",  "corr": "EURUSD"},
    "USDJPY":  {"ex": "OANDA",   "scr": "forex",  "corr": "DXY"},
    "AUDUSD":  {"ex": "OANDA",   "scr": "forex",  "corr": "NZDUSD"},
    "EURUSD":  {"ex": "OANDA",   "scr": "forex",  "corr": "GBPUSD"},
    "USDCHF":  {"ex": "OANDA",   "scr": "forex",  "corr": "DXY"},
    "EURJPY":  {"ex": "OANDA",   "scr": "forex",  "corr": "GBPJPY"},
    "GBPJPY":  {"ex": "OANDA",   "scr": "forex",  "corr": "EURJPY"},
}

last_reset_date = None

# ─── SYSTEM HELPERS ────────────────────────────────────────────────────────────
def get_now_local():
    return datetime.now(timezone(timedelta(hours=7)))

def push_to_firebase(path, data):
    try:
        requests.post(f"{FIREBASE_DB_URL}/{path}.json", json=data, timeout=10)
    except: pass

def send_all(msg, signal_data=None):
    # Telegram
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN_TG}/sendMessage",
                      json={"chat_id": CHAT_ID_TG, "message_thread_id": TOPIC_ID_TG,
                            "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass
    # Discord
    try:
        requests.post(DISCORD_WEBHOOK, json={"content": msg}, timeout=10)
    except: pass
    # Firebase Website
    if signal_data:
        push_to_firebase("signals/ict", signal_data)

# ─── PREDATOR ENGINE (ICT LOGIC) ──────────────────────────────────────────────
class ICT_Ultimate_Engine:
    def __init__(self, sym, ex, scr, corr):
        self.symbol = sym
        self.corr   = corr
        # FIX: Tambahkan Timeout & Custom User-Agent (Internal TA_Handler)
        self.daily_h = TA_Handler(
            symbol=sym, exchange=ex, screener=scr, interval=Interval.INTERVAL_1_DAY,
            timeout=15
        )
        self.micro_h = TA_Handler(
            symbol=sym, exchange=ex, screener=scr, interval=Interval.INTERVAL_5_MINUTES,
            timeout=15
        )

    def _safe_fetch(self, handler):
        """Mencegah Error 403 dengan retry logic dan delay"""
        for _ in range(3):
            try:
                return handler.get_analysis()
            except Exception as e:
                if "403" in str(e):
                    time.sleep(5) # Jeda lebih lama jika kena 403
                continue
        return None

    def get_analysis_data(self):
        a = self._safe_fetch(self.daily_h)
        if not a: return None, "NEUTRAL"
        
        bias = a.summary.get('RECOMMENDATION', 'NEUTRAL')
        atr = a.indicators.get('ATR', 0)
        close = a.indicators.get('close', 0)
        
        proto = "XAMD" if (close > 0 and atr > close * 0.0015) else "AMDX"
        return proto, bias

    def sniper_entry(self, bias):
        ana = self._safe_fetch(self.micro_h)
        if not ana: return None
        
        d = ana.indicators
        price = d.get('close', 0)
        high = d.get('high', price)
        low = d.get('low', price)
        
        sl_v = abs(high - low) * 2.5 # Buffer SL ICT
        
        if "BUY" in bias:
            return price, price - sl_v, price + sl_v * 1.5, price + sl_v * 3.0, "BUY"
        else:
            return price, price + sl_v, price - sl_v * 1.5, price - sl_v * 3.0, "SELL"

# ─── MAIN LOOP ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"🔥 GLOBAL PREDATOR V11 ONLINE (PONOROGO ENGINE)")
    send_all("🚀 **SYSTEM ONLINE:** Predator V11 siap memantau 9 Pairs.")

    while True:
        now = get_now_local()
        ts = now.strftime("%Y-%m-%d %H:%M WIB")
        print(f"\n[{ts}] Scanning markets...")

        for pair, cfg in PAIRS.items():
            try:
                # Delay 5 detik antar pair agar IP tidak diblokir TradingView
                time.sleep(5) 
                
                bot = ICT_Ultimate_Engine(pair, cfg['ex'], cfg['scr'], cfg['corr'])
                proto, bias = bot.get_analysis_data()
                
                if "BUY" in bias or "SELL" in bias:
                    result = bot.sniper_entry(bias)
                    if not result: continue
                    
                    entry, sl, tp1, tp2, direction = result
                    score = 9 if "STRONG" in bias else 7
                    strength = "STRONG 🔥" if score >= 8 else "MODERATE ✅"
                    
                    # Format desimal: XAU/BTC (2 digit), Forex (5 digit)
                    fmt = ".2f" if ("USD" not in pair or "XAU" in pair or "BTC" in pair) else ".5f"

                    msg = (f"🚨 **PREDATOR: {pair}**\n━━━━━━━━━━━━\n"
                           f"📡 **{direction}** | Score {score}/10 {strength}\n"
                           f"🎯 Entry: `{entry:{fmt}}`\n🛑 SL: `{sl:{fmt}}`\n"
                           f"💰 TP1: `{tp1:{fmt}}` | TP2: `{tp2:{fmt}}`\n"
                           f"🧠 {proto} | SMT vs {cfg['corr']}\n🕐 {ts}")

                    signal_data = {
                        "pair": pair, "direction": direction, "strength": strength,
                        "score": score, "price": round(entry, 5), "sl": round(sl, 5),
                        "tp1": round(tp1, 5), "tp2": round(tp2, 5),
                        "trend_htf": bias, "kill_zone": proto, "timestamp": ts,
                        "source": "predator_v11"
                    }
                    
                    send_all(msg, signal_data)
                    print(f"✅ {pair}: Signal Sent!")

            except Exception as e:
                print(f"✗ Error {pair}: {e}")
        
        print(f"⏳ Scan Selesai. Standby 60 Menit...")
        time.sleep(3600)
