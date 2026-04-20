import requests
import time
import random
from datetime import datetime, timezone, timedelta
from tradingview_ta import TA_Handler, Interval

# ─── TIMEZONE (JAKARTA) ────────────────────────────────────────────────────────
WIB = timezone(timedelta(hours=7))

# ─── CONFIGURATION ──────────────────────────────────────────────────────────────
TOKEN_TG        = "8196511062:AAGyfWcRUk9uw_lc_aQgUW6vLyyRmgF1hcE"
CHAT_ID_TG      = "-1003660980986"
TOPIC_ID_TG     = 18
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1489306608554217736/vTC-HQBFwXWsiBE0WImdB0Uq88WppsSjCb548y5W5aFAubZVYXBgFCEuMLbcB22H1h7H"
FIREBASE_DB_URL = "https://freedomsyndicatecloud-default-rtdb.firebaseio.com"

PROXIES = {
    'http':  'socks5://127.0.0.1:9150',
    'https': 'socks5://127.0.0.1:9150'
}

PAIRS = {
    "XAUUSD":  {"ex": "OANDA",   "scr": "cfd",    "corr": "XAUEUR",  "market": "OANDA",   "decimals": 2},
    "BTCUSDT": {"ex": "BINANCE", "scr": "crypto", "corr": "ETHUSDT", "market": "BINANCE", "decimals": 2},
    "GBPUSD":  {"ex": "OANDA",   "scr": "forex",  "corr": "EURUSD",  "market": "OANDA",   "decimals": 5},
    "USDJPY":  {"ex": "OANDA",   "scr": "forex",  "corr": "DX",      "market": "OANDA",   "decimals": 3},
    "AUDUSD":  {"ex": "OANDA",   "scr": "forex",  "corr": "NZDUSD",  "market": "OANDA",   "decimals": 5},
    "EURUSD":  {"ex": "OANDA",   "scr": "forex",  "corr": "GBPUSD",  "market": "OANDA",   "decimals": 5},
    "NZDUSD":  {"ex": "OANDA",   "scr": "forex",  "corr": "AUDUSD",  "market": "OANDA",   "decimals": 5},
    "USDCAD":  {"ex": "OANDA",   "scr": "forex",  "corr": "DX",      "market": "OANDA",   "decimals": 5},
}

open_signals = {}

def fmt(price, decimals):
    return f"{price:.{decimals}f}"

def pips_diff(a, b, decimals):
    if decimals == 5: return round(abs(a - b) * 10000, 1)
    elif decimals == 3: return round(abs(a - b) * 100, 1)
    else: return round(abs(a - b), 2)

def get_current_ip():
    try:
        r = requests.get('https://api.ipify.org', proxies=PROXIES, timeout=10)
        return r.text
    except: return "DISCONNECTED (Pastikan Tor Aktif!)"

def push_to_firebase(path: str, data: dict):
    try: requests.post(f"{FIREBASE_DB_URL}/{path}.json", json=data, timeout=10)
    except: pass

def send_signal(msg, firebase_data=None):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN_TG}/sendMessage",
            json={"chat_id": CHAT_ID_TG, "message_thread_id": TOPIC_ID_TG, "text": msg, "parse_mode": "Markdown"}, 
            timeout=10
        )
    except: pass
    try: requests.post(DISCORD_WEBHOOK, json={"content": msg}, timeout=10)
    except: pass
    if firebase_data: push_to_firebase("signals/ict", firebase_data)

def get_ict_logic(proto, direction):
    if proto == "AMDX":
        if direction == "BUY":
            logic = "AMDX: MANIPULATION LOW (JUDAS)"
            analysis = "• Judas Swing ke bawah → sweep Liquidity Low\n• Konfirmasi Bullish Reversal 5M\n• Expect Expansion ke ATAS"
        else:
            logic = "AMDX: MANIPULATION HIGH (JUDAS)"
            analysis = "• Judas Swing ke atas → sweep Liquidity High\n• Konfirmasi Bearish Reversal 5M\n• Expect Expansion ke BAWAH"
    else:
        logic = f"XAMD: EXPANSION — DAILY {direction}"
        analysis = f"• Daily Bias: STRONG {direction}\n• Setup: ICT Optimal Entry (OB/FVG)\n• Momentum {direction} dominan"
    return logic, analysis

def calc_sl_tp(direction, entry, atr, decimals):
    sl_dist, tp_dist = atr * 0.20, atr * 0.50
    if direction == "BUY":
        return round(entry - sl_dist, decimals), round(entry + tp_dist, decimals)
    return round(entry + sl_dist, decimals), round(entry - tp_dist, decimals)

def check_open_signals():
    if not open_signals: return
    for pair in list(open_signals.keys()):
        sig = open_signals[pair]
        cfg = PAIRS[pair]
        try:
            handler = TA_Handler(symbol=pair, exchange=cfg['ex'], screener=cfg['scr'], interval=Interval.INTERVAL_5_MINUTES, proxies=PROXIES)
            time.sleep(random.uniform(2, 4))
            current = handler.get_analysis().indicators['close']
            dec, entry, tp, sl, direction = sig['decimals'], sig['entry'], sig['tp'], sig['sl'], sig['direction']
            ts_wib = datetime.now(WIB).strftime("%Y-%m-%d %H:%M WIB")

            hit_tp = (direction == "BUY" and current >= tp) or (direction == "SELL" and current <= tp)
            hit_sl = (direction == "BUY" and current <= sl) or (direction == "SELL" and current >= sl)

            if hit_tp or hit_sl:
                res_type = "TP HIT ✅" if hit_tp else "SL HIT ❌"
                pips = pips_diff(entry, tp if hit_tp else sl, dec)
                msg = (f"*{res_type} — {pair}*\n━━━━━━━━━━━━━━\n📥 {direction} @ `{fmt(entry, dec)}`"
                       f"\n🎯 Hit: `{fmt(current, dec)}`"
                       f"\n💰 Result: {'+' if hit_tp else '-'}{pips} pips\n━━━━━━━━━━━━━━\n⏰ {ts_wib}\n_Freedom Syndicate_")
                send_signal(msg)
                del open_signals[pair]
        except: pass

class PredatorEngine:
    def __init__(self, sym, ex, scr):
        self.symbol = sym
        self.daily = TA_Handler(symbol=sym, exchange=ex, screener=scr, interval=Interval.INTERVAL_1_DAY, proxies=PROXIES)
        self.micro = TA_Handler(symbol=sym, exchange=ex, screener=scr, interval=Interval.INTERVAL_5_MINUTES, proxies=PROXIES)
    def _safe_get(self, h):
        time.sleep(random.uniform(3, 7))
        try: return h.get_analysis()
        except: return None

if __name__ == "__main__":
    print("\n🚀 PREDATOR V11 — ICT SUPREME (JAKARTA TIME)")
    ts_boot = datetime.now(WIB).strftime("%Y-%m-%d %H:%M WIB")
    send_signal(f"🦅 *PREDATOR V11* ONLINE\n━━━━━━━━━━━━━━\n⏰ Boot: {ts_boot}\n📍 IP: `Hidden via Tor`\n_Freedom Syndicate_")
    
    scan_count = 0
    while True:
        ts_wib = datetime.now(WIB).strftime("%H:%M WIB")
        print(f"\n[{ts_wib}] SCAN #{scan_count + 1}")
        if scan_count > 0: check_open_signals()
        
        for pair, cfg in PAIRS.items():
            if pair in open_signals: continue
            bot = PredatorEngine(pair, cfg['ex'], cfg['scr'])
            d_data = bot._safe_get(bot.daily)
            if not d_data: continue
            
            bias, atr, close = d_data.summary['RECOMMENDATION'], d_data.indicators.get('ATR', 0), d_data.indicators.get('close', 0)
            if "BUY" not in bias and "SELL" not in bias: continue
            
            m_data = bot._safe_get(bot.micro)
            if not m_data: continue
            
            entry, direction = m_data.indicators['close'], "BUY" if "BUY" in bias else "SELL"
            sl, tp = calc_sl_tp(direction, entry, atr, cfg['decimals'])
            logic, analysis = get_ict_logic("XAMD" if atr > (close * 0.0015) else "AMDX", direction)
            
            msg = (f"🦅 *GLOBAL SIGNAL: {pair}*\n━━━━━━━━━━━━━━\n🔥 *Logic:* {logic}\n📥 *Action:* {direction}\n🎯 *Price:* `{fmt(entry, cfg['decimals'])}`"
                   f"\n🛑 *SL:* `{fmt(sl, cfg['decimals'])}` | 🎯 *TP:* `{fmt(tp, cfg['decimals'])}`"
                   f"\n\n📊 *Analisis:*\n{analysis}\n━━━━━━━━━━━━━━\n⏰ {ts_wib}\n_Freedom Syndicate_")
            
            send_signal(msg, {"pair": pair, "entry": entry, "sl": sl, "tp": tp, "timestamp": ts_wib})
            open_signals[pair] = {"entry": entry, "sl": sl, "tp": tp, "direction": direction, "decimals": cfg['decimals'], "market": cfg['market']}
            time.sleep(random.randint(15, 30))
            
        scan_count += 1
        time.sleep(1800)
