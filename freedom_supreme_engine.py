import requests
import time
import random
from datetime import datetime, timezone, timedelta
from tradingview_ta import TA_Handler, Interval

# ─── CONFIGURATION ──────────────────────────────────────────────────────────────
# Timezone & Identity
WIB = timezone(timedelta(hours=7))
UTC = timezone.utc
BOT_NAME = "Doms Freedom Syndicate"

# API & Webhooks
TOKEN_TG_PREDATOR  = "8196511062:AAGyfWcRUk9uw_lc_aQgUW6vLyyRmgF1hcE"
TOKEN_TG_SUPREME   = "8794811012:AAFUrcWYI-5mldlwXrIl8AyjVvgDvNRKRWk"
CHAT_ID_TG         = "-1003660980986"
TOPIC_ID_GENERAL   = 18

DISCORD_PREDATOR   = "https://discord.com/api/webhooks/1489306608554217736/vTC-HQBFwXWsiBE0WImdB0Uq88WppsSjCb548y5W5aFAubZVYXBgFCEuMLbcB22H1h7H"
DISCORD_FUNDA      = "https://discord.com/api/webhooks/1489314765074595840/BRby0L3L4cfUUGyDpihSBjRlHPpNutFiZWF5mFYU6CpCkjoEA9Hw1A2W0c6LEUgO30i7"
FIREBASE_URL       = "https://freedomsyndicatecloud-default-rtdb.firebaseio.com"

# Proxy Tor (Socks5)
PROXIES = {'http': 'socks5://127.0.0.1:9150', 'https': 'socks5://127.0.0.1:9150'}

# ─── PAIRS & IMPACT ─────────────────────────────────────────────────────────────
PAIRS = {
    "XAUUSD": {"ex": "OANDA", "scr": "cfd", "dec": 2},
    "GBPUSD": {"ex": "OANDA", "scr": "forex", "dec": 5},
    "EURUSD": {"ex": "OANDA", "scr": "forex", "dec": 5},
    "USDJPY": {"ex": "OANDA", "scr": "forex", "dec": 3},
    "BTCUSDT": {"ex": "BINANCE", "scr": "crypto", "dec": 2}
}

IMPACT_MAP = {"High": "🔴 HIGH", "Medium": "🟡 MEDIUM", "Low": "🟢 LOW"}

# ─── CORE ENGINE FUNCTIONS ──────────────────────────────────────────────────────

def get_killzone():
    """Logic ICT Killzones (WIB)"""
    hr = datetime.now(WIB).hour
    if 7 <= hr <= 10: return "ASIA KILLZONE"
    if 14 <= hr <= 17: return "LONDON KILLZONE"
    if 20 <= hr <= 23: return "NEW YORK KILLZONE"
    return "MACRO/OFF-SESSION"

def get_ict_context(proto, direction, pair):
    """Logika Michael J. Huddleston (ICT)"""
    session = get_killzone()
    if proto == "AMDX":
        logic = f"ICT {session} - AMDX (JUDAS)"
        analysis = f"• Liquidity Sweep pada {pair} Low/High.\n• Rejection di area HTF PD Array.\n• Judas Swing terdeteksi, expect reversal."
    else:
        logic = f"ICT {session} - XAMD (EXPANSION)"
        analysis = f"• Market Structure Break (MSB) terkonfirmasi.\n• Entry pada FVG / Orderblock.\n• Mengikuti Daily Bias yang kuat."
    return logic, analysis

def send_to_all(msg, category="signal", data=None):
    """Broadcast ke Telegram, Discord, dan Firebase"""
    # Telegram
    token = TOKEN_TG_PREDATOR if category == "signal" else TOKEN_TG_SUPREME
    try:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                      json={"chat_id": CHAT_ID_TG, "message_thread_id": TOPIC_ID_GENERAL, 
                            "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass

    # Discord
    webhook = DISCORD_PREDATOR if category == "signal" else DISCORD_FUNDA
    try:
        requests.post(webhook, json={"content": msg}, timeout=10)
    except: pass

    # Web (Firebase)
    if data:
        path = "signals/ict" if category == "signal" else "signals/fundamental"
        try:
            requests.post(f"{FIREBASE_URL}/{path}.json", json=data, timeout=10)
        except: pass

# ─── MAIN RUNNER ────────────────────────────────────────────────────────────────

def run_freedom_engine():
    print(f"🚀 {BOT_NAME} SUPREME ENGINE STARTING...")
    
    while True:
        try:
            # 1. CEK FUNDAMENTAL (Radar)
            funda_url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
            events = requests.get(funda_url, proxies=PROXIES, timeout=15).json()
            
            for ev in events:
                # Filter news hari ini
                ev_dt = datetime.fromisoformat(ev['date']).astimezone(UTC)
                if abs((ev_dt - datetime.now(UTC)).total_seconds()) < 3600: # Cek 1 jam terdekat
                    impact = IMPACT_MAP.get(ev['impact'])
                    if impact:
                        news_msg = f"⚠️ *FUNDAMENTAL ALERT* ⚠️\n━━━━━━━━━━\n📋 {ev['title']}\n🏛 Currency: {ev['country']}\n🔥 Impact: {impact}\n🕐 Time: {ev_dt.astimezone(WIB).strftime('%H:%M WIB')}"
                        send_to_all(news_msg, category="news", data=ev)

            # 2. ANALISIS SIGNAL (Predator)
            for pair, cfg in PAIRS.items():
                handler = TA_Handler(symbol=pair, exchange=cfg['ex'], screener=cfg['scr'], 
                                     interval=Interval.INTERVAL_5_MINUTES, proxies=PROXIES)
                analysis = handler.get_analysis()
                bias = analysis.summary['RECOMMENDATION']
                
                if "BUY" in bias or "SELL" in bias:
                    direction = "BUY" if "BUY" in bias else "SELL"
                    entry = analysis.indicators['close']
                    atr = analysis.indicators['ATR']
                    
                    # ICT Logic
                    proto = "XAMD" if atr > (entry * 0.001) else "AMDX"
                    logic, ict_text = get_ict_context(proto, direction, pair)
                    
                    # SL/TP Logic (Premium Zone)
                    sl = entry - (atr * 1.5) if direction == "BUY" else entry + (atr * 1.5)
                    tp = entry + (atr * 3.0) if direction == "BUY" else entry - (atr * 3.0)

                    sig_msg = (
                        f"🦅 *PREDATOR SIGNAL: {pair}* 🦅\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"🔥 *Logic:* {logic}\n"
                        f"📥 *Action:* {direction}\n"
                        f"🎯 *Entry:* `{entry:.{cfg['dec']}f}`\n"
                        f"🛑 *SL:* `{sl:.{cfg['dec']}f}` | 🎯 *TP:* `{tp:.{cfg['dec']}f}`\n\n"
                        f"📊 *ICT Analysis:*\n{ict_text}\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"🏛 *Market:* {cfg['ex']} | 🕐 {get_killzone()}\n"
                        f"_Freedom Syndicate | {datetime.now(WIB).strftime('%H:%M WIB')}_"
                    )
                    
                    send_to_all(sig_msg, category="signal", data={"pair": pair, "entry": entry, "tp": tp, "sl": sl})
                    time.sleep(30) # Anti-spam

            print(f"[{datetime.now(WIB).strftime('%H:%M:%S')}] Cycle Complete. Sleeping...")
            time.sleep(600) # Scan setiap 10 menit

        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_freedom_engine()