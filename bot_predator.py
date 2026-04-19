“””
╔══════════════════════════════════════════════════════════════╗
║    GLOBAL PREDATOR V10 — ICT SIGNAL BOT + FIREBASE PUSH     ║
║    Sinyal otomatis → Telegram + Discord + Website Journal    ║
╚══════════════════════════════════════════════════════════════╝
Install: pip install requests tradingview_ta
“””

import requests
import time
from datetime import datetime, timezone

TOKEN_TG        = “8196511062:AAGyfWcRUk9uw_lc_aQgUW6vLyyRmgF1hcE”
CHAT_ID_TG      = “-1003660980986”
TOPIC_ID_TG     = 18
DISCORD_WEBHOOK = “https://discord.com/api/webhooks/1489306608554217736/vTC-HQBFwXWsiBE0WImdB0Uq88WppsSjCb548y5W5aFAubZVYXBgFCEuMLbcB22H1h7H”
FIREBASE_DB_URL = “https://freedomsyndicatecloud-default-rtdb.firebaseio.com”

# ── Firebase REST Push ──────────────────────────────────────────────────

def push_to_firebase(path, data):
try:
r = requests.post(f”{FIREBASE_DB_URL}/{path}.json”, json=data, timeout=10)
if r.status_code == 200:
key = r.json().get(“name”, “”)
print(f”  ✅ Firebase → /{path}/{key}”)
return key
except Exception as e:
print(f”  ✗ Firebase: {e}”)
return None

def trim_old_signals(path, keep=50):
try:
r = requests.get(f”{FIREBASE_DB_URL}/{path}.json”, timeout=10)
if r.status_code == 200 and r.json():
keys = list(r.json().keys())
for old in keys[:max(0, len(keys)-keep)]:
requests.delete(f”{FIREBASE_DB_URL}/{path}/{old}.json”, timeout=5)
except: pass

# ── Send All ────────────────────────────────────────────────────────────

def send_all(msg, signal_data=None):
try:
requests.post(
f”https://api.telegram.org/bot{TOKEN_TG}/sendMessage”,
data={“chat_id”: CHAT_ID_TG, “message_thread_id”: TOPIC_ID_TG,
“text”: msg, “parse_mode”: “Markdown”}, timeout=10)
except: pass
try:
requests.post(DISCORD_WEBHOOK, json={“content”: msg}, timeout=10)
except: pass
if signal_data:
push_to_firebase(“signals/ict”, signal_data)
trim_old_signals(“signals/ict”)

# ── ICT Engine ──────────────────────────────────────────────────────────

try:
from tradingview_ta import TA_Handler, Interval
TV_AVAILABLE = True
except ImportError:
TV_AVAILABLE = False
print(“⚠️  pip install tradingview_ta”)

PAIRS = {
“XAUUSD”:  {“ex”: “OANDA”,   “scr”: “cfd”,    “corr”: “XAUEUR”},
“BTCUSDT”: {“ex”: “BINANCE”, “scr”: “crypto”,  “corr”: “ETHUSDT”},
“GBPUSD”:  {“ex”: “OANDA”,   “scr”: “forex”,   “corr”: “EURUSD”},
“USDJPY”:  {“ex”: “OANDA”,   “scr”: “forex”,   “corr”: “DX”},
“AUDUSD”:  {“ex”: “OANDA”,   “scr”: “forex”,   “corr”: “NZDUSD”},
“EURUSD”:  {“ex”: “OANDA”,   “scr”: “forex”,   “corr”: “GBPUSD”},
“NZDUSD”:  {“ex”: “OANDA”,   “scr”: “forex”,   “corr”: “AUDUSD”},
“USDCAD”:  {“ex”: “OANDA”,   “scr”: “forex”,   “corr”: “DX”},
}

class ICT_Ultimate_Engine:
def **init**(self, sym, ex, scr, corr):
self.symbol = sym
self.corr   = corr
self.daily_h = TA_Handler(symbol=sym, exchange=ex, screener=scr, interval=Interval.INTERVAL_1_DAY)
self.micro_h = TA_Handler(symbol=sym, exchange=ex, screener=scr, interval=Interval.INTERVAL_5_MINUTES)

```
def get_protocol(self):
    a     = self.daily_h.get_analysis()
    bias  = a.summary['RECOMMENDATION']
    atr   = a.indicators['ATR']
    close = a.indicators['close']
    proto = "XAMD" if atr > close * 0.0015 else "AMDX"
    return proto, bias

def sniper_entry(self, bias):
    d     = self.micro_h.get_analysis().indicators
    price = d['close']
    sl_v  = abs(d['high'] - d['low']) * 2.0
    if "BUY" in bias:
        return price, price-sl_v, price+sl_v*1.5, price+sl_v*2.5, price+sl_v*3.5, "BUY"
    return price, price+sl_v, price-sl_v*1.5, price-sl_v*2.5, price-sl_v*3.5, "SELL"

def get_score(self, bias):
    return 9 if bias in ("STRONG_BUY","STRONG_SELL") else 7
```

if **name** == “**main**”:
send_all(“🔥 **GLOBAL PREDATOR V10** AKTIF\n📡 Sinyal → Telegram + Discord + Website Journal\n_Pure Institution Logic._”)
while True:
ts = datetime.now(timezone.utc).strftime(”%Y-%m-%d %H:%M UTC”)
print(f”\n[{ts}] Scanning {len(PAIRS)} pairs…”)
for pair, cfg in PAIRS.items():
if not TV_AVAILABLE: break
try:
bot = ICT_Ultimate_Engine(pair, cfg[‘ex’], cfg[‘scr’], cfg[‘corr’])
proto, bias = bot.get_protocol()
if “BUY” in bias or “SELL” in bias:
entry, sl, tp1, tp2, tp3, direction = bot.sniper_entry(bias)
score    = bot.get_score(bias)
strength = “STRONG 🔥” if score >= 8 else “MODERATE ✅”
reasons  = [f”📊 Daily Bias: {bias}”, f”🔄 Protocol: {proto}”, f”⚡ SMT vs {cfg[‘corr’]} | CISD”]

```
                msg = (f"🚨 **PREDATOR: {pair}**\n━━━━━━━━━━━━\n"
                       f"📡 **{direction}** | Score {score}/10 {strength}\n"
                       f"🎯 Entry: `{entry:.5f}`\n🛑 SL: `{sl:.5f}`\n"
                       f"💰 TP1: `{tp1:.5f}` | TP2: `{tp2:.5f}`\n"
                       f"🧠 {proto} | SMT vs {cfg['corr']}\n🕐 {ts}")

                signal_data = {
                    "pair": pair, "direction": direction, "strength": strength,
                    "score": score, "price": round(entry,5), "sl": round(sl,5),
                    "tp1": round(tp1,5), "tp2": round(tp2,5), "tp3": round(tp3,5),
                    "trend_htf": bias, "kill_zone": proto, "reasons": reasons,
                    "timestamp": ts, "source": "predator_v10"
                }
                send_all(msg, signal_data)
                print(f"  🚨 {pair} {direction} → sent!")
                time.sleep(15)
        except Exception as e:
            print(f"  ✗ {pair}: {e}")
    print("  ⏳ Next scan in 60 min...")
    time.sleep(3600)
```
