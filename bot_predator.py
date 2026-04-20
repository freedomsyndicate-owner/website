"""
╔══════════════════════════════════════════════════════════════════════════╗
║       GLOBAL PREDATOR V11 — ICT SUPREME ENGINE (FIXED)                  ║
║       ─────────────────────────────────────────────────────             ║
║       FIX: Anti-429 Rate Limit & Stability Patch                         ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import requests
import time
from datetime import datetime, timezone

# ─── CONFIGURATION ─────────────────────────────────────────────────────────────
TOKEN_TG        = "8196511062:AAGyfWcRUk9uw_lc_aQgUW6vLyyRmgF1hcE"
CHAT_ID_TG      = "-1003660980986"
TOPIC_ID_TG     = 18
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1489306608554217736/vTC-HQBFwXWsiBE0WImdB0Uq88WppsSjCb548y5W5aFAubZVYXBgFCEuMLbcB22H1h7H"
FIREBASE_DB_URL = "https://freedomsyndicatecloud-default-rtdb.firebaseio.com"

PAIRS = {
    "XAUUSD":  {"ex": "OANDA",   "scr": "cfd",    "corr": "XAUEUR"},
    "BTCUSDT": {"ex": "BINANCE", "scr": "crypto", "corr": "ETHUSDT"},
    "GBPUSD":  {"ex": "OANDA",   "scr": "forex",  "corr": "EURUSD"},
    "USDJPY":  {"ex": "OANDA",   "scr": "forex",  "corr": "DX"},
    "AUDUSD":  {"ex": "OANDA",   "scr": "forex",  "corr": "NZDUSD"},
    "EURUSD":  {"ex": "OANDA",   "scr": "forex",  "corr": "GBPUSD"},
    "NZDUSD":  {"ex": "OANDA",   "scr": "forex",  "corr": "AUDUSD"},
    "USDCAD":  {"ex": "OANDA",   "scr": "forex",  "corr": "DX"},
}

# ══════════════════════════════════════════════════════════════════════════════
#  FIREBASE HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def push_to_firebase(path: str, data: dict):
    try:
        r = requests.post(f"{FIREBASE_DB_URL}/{path}.json", json=data, timeout=10)
        if r.status_code == 200: return r.json().get("name", "")
    except Exception as e: print(f"    ✗ Firebase: {e}")
    return None

def trim_old_entries(path: str, keep: int = 60):
    try:
        r = requests.get(f"{FIREBASE_DB_URL}/{path}.json", timeout=10)
        if r.status_code == 200 and r.json():
            keys = list(r.json().keys())
            if len(keys) > keep:
                for k in keys[: len(keys) - keep]:
                    requests.delete(f"{FIREBASE_DB_URL}/{path}/{k}.json", timeout=5)
    except: pass

def send_all(msg, signal_data=None):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN_TG}/sendMessage",
            json={"chat_id": CHAT_ID_TG, "message_thread_id": TOPIC_ID_TG,
                  "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass
    
    try:
        requests.post(DISCORD_WEBHOOK, json={"content": msg}, timeout=10)
    except: pass
    
    if signal_data:
        push_to_firebase("signals/ict", signal_data)
        trim_old_entries("signals/ict", keep=60)

# ── ICT Engine ──────────────────────────────────────────────────────────
try:
    from tradingview_ta import TA_Handler, Interval
    TV_AVAILABLE = True
except ImportError:
    TV_AVAILABLE = False

class ICT_Ultimate_Engine:
    def __init__(self, sym, ex, scr, corr):
        self.symbol = sym
        self.daily_h = TA_Handler(symbol=sym, exchange=ex, screener=scr, interval=Interval.INTERVAL_1_DAY)
        self.micro_h = TA_Handler(symbol=sym, exchange=ex, screener=scr, interval=Interval.INTERVAL_5_MINUTES)

    def _safe_get_analysis(self, handler, retries=3):
        for i in range(retries):
            try:
                # Menggunakan timeout internal tradingview_ta jika memungkinkan
                return handler.get_analysis()
            except Exception as e:
                # Jika terkena 429 atau 403, tunggu lebih lama (30 detik)
                print(f"      ! API Error pada {self.symbol}. Re-trying {i+1}/{retries} (Jeda 30s)...")
                time.sleep(30)
                if i == retries - 1: raise e
        return None

    def get_protocol(self):
        analysis = self._safe_get_analysis(self.daily_h)
        if not analysis: return "N/A", "NEUTRAL"
        
        bias  = analysis.summary['RECOMMENDATION']
        atr   = analysis.indicators.get('ATR', 0)
        close = analysis.indicators.get('close', 0)
        proto = "XAMD" if atr > close * 0.0015 else "AMDX"
        return proto, bias

    def sniper_entry(self, bias):
        analysis = self._safe_get_analysis(self.micro_h)
        if not analysis: return 0,0,0,0,0, "WAIT"
        
        d     = analysis.indicators
        price = d['close']
        high  = d['high']
        low   = d['low']
        sl_v  = abs(high - low) * 2.0
        
        if "BUY" in bias:
            return price, price-sl_v, price+sl_v*1.5, price+sl_v*2.5, price+sl_v*3.5, "BUY"
        return price, price+sl_v, price-sl_v*1.5, price-sl_v*2.5, price-sl_v*3.5, "SELL"

if __name__ == "__main__":
    ts_start = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    
    startup_signal = {
        "pair": "SYSTEM", "direction": "ONLINE", "strength": "INFO",
        "score": 10, "price": 0, "sl": 0, "tp1": 0, "tp2": 0, "tp3": 0,
        "trend_htf": "N/A", "kill_zone": "System Check", "reasons": ["Bot Predator Supreme Online"],
        "timestamp": ts_start, "source": "predator_v11"
    }
    send_all("🔥 **GLOBAL PREDATOR V11** AKTIF\n_Sistem stabilisasi API diaktifkan._", startup_signal)
    
    while True:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        print(f"\n[{ts}] Scanning pairs...")
        
        for pair, cfg in PAIRS.items():
            if not TV_AVAILABLE: break
            try:
                # Jeda antar koin ditambah jadi 20 detik agar IP tidak dianggap spam
                print(f"  > Analyzing {pair}...")
                bot = ICT_Ultimate_Engine(pair, cfg['ex'], cfg['scr'], cfg['corr'])
                
                proto, bias = bot.get_protocol()
                time.sleep(15) # Jeda antara Daily fetch dan Micro fetch
                
                if "BUY" in bias or "SELL" in bias:
                    entry, sl, tp1, tp2, tp3, direction = bot.sniper_entry(bias)
                    if entry == 0: continue
                    
                    score    = 9 if "STRONG" in bias else 7
                    strength = "STRONG 🔥" if score >= 8 else "MODERATE ✅"
                    
                    msg = (f"🚨 **PREDATOR: {pair}**\n━━━━━━━━━━━━\n"
                           f"📡 **{direction}** | Score {score}/10\n"
                           f"🎯 Entry: `{entry:.5f}`\n🛑 SL: `{sl:.5f}`\n"
                           f"💰 TP: `{tp1:.5f}`\n"
                           f"🧠 {proto} | {ts}")

                    signal_data = {
                        "pair": pair, "direction": direction, "strength": strength,
                        "score": score, "price": round(entry,5), "sl": round(sl,5),
                        "tp1": round(tp1,5), "tp2": round(tp2,5), "tp3": round(tp3,5),
                        "trend_htf": bias, "kill_zone": proto, "reasons": [f"Bias {bias}"],
                        "timestamp": ts, "source": "predator_v11"
                    }
                    send_all(msg, signal_data)
                    print(f"    ✓ {pair} Signal sent.")
                
                # Jeda wajib setelah satu koin selesai total
                time.sleep(20) 

            except Exception as e:
                print(f"  ✗ {pair} Error: {e}")
                time.sleep(60) # Jika error, istirahat 1 menit

        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Scan Selesai. Istirahat 30 Menit...")
        time.sleep(1800) # Scan setiap 30 menit saja, 60 menit (3600) juga disarankan.
