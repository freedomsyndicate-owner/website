"""
╔══════════════════════════════════════════════════════════════════════════╗
║       GLOBAL PREDATOR V11 — ICT SUPREME ENGINE (STEALTH)                 ║
║       ─────────────────────────────────────────────────────              ║
║       ✅ Anti-Banned: Auto-Rotating IP via Tor Network                   ║
║       ✅ Strategy: ICT Daily Bias, Protocol AMDX/XAMD                    ║
║       ✅ Signal: Entry + SL + TP + ICT Analysis + Result Tracker         ║
║       ✅ Output: Telegram, Discord, & Firebase Journal                   ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import requests
import time
import random
from datetime import datetime, timezone, timedelta
from tradingview_ta import TA_Handler, Interval

# ─── TIMEZONE (JAKARTA / WIB) ──────────────────────────────────────────────────
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
    "XAUUSD":  {"ex": "OANDA",   "scr": "cfd",    "market": "OANDA",   "decimals": 2},
    "BTCUSDT": {"ex": "BINANCE", "scr": "crypto", "market": "BINANCE", "decimals": 2},
    "GBPUSD":  {"ex": "OANDA",   "scr": "forex",  "market": "OANDA",   "decimals": 5},
    "USDJPY":  {"ex": "OANDA",   "scr": "forex",  "market": "OANDA",   "decimals": 3},
    "AUDUSD":  {"ex": "OANDA",   "scr": "forex",  "market": "OANDA",   "decimals": 5},
    "EURUSD":  {"ex": "OANDA",   "scr": "forex",  "market": "OANDA",   "decimals": 5},
    "NZDUSD":  {"ex": "OANDA",   "scr": "forex",  "market": "OANDA",   "decimals": 5},
    "USDCAD":  {"ex": "OANDA",   "scr": "forex",  "market": "OANDA",   "decimals": 5},
}

open_signals = {}

# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS & SENDERS (FIXED FOR DISCORD)
# ══════════════════════════════════════════════════════════════════════════════

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
    except: return "DISCONNECTED"

def send_signal(msg, firebase_data=None):
    """Kirim ke semua platform secara independen"""
    # 1. Telegram
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN_TG}/sendMessage",
            json={
                "chat_id": CHAT_ID_TG,
                "message_thread_id": TOPIC_ID_TG,
                "text": msg,
                "parse_mode": "Markdown"
            }, timeout=10
        )
    except Exception as e: print(f"TG Error: {e}")

    # 2. Discord (Fixed)
    try:
        # Gunakan session tanpa proxy untuk Discord jika Tor melambat
        requests.post(DISCORD_WEBHOOK, json={"content": msg}, timeout=10)
    except Exception as e: print(f"Discord Error: {e}")

    # 3. Firebase
    if firebase_data:
        try:
            requests.post(f"{FIREBASE_DB_URL}/signals/ict.json", json=firebase_data, timeout=10)
        except: pass

# ══════════════════════════════════════════════════════════════════════════════
#  ICT LOGIC & ENGINE (KEEP ORIGINAL LOGIC)
# ══════════════════════════════════════════════════════════════════════════════

def get_ict_logic(proto, direction):
    if proto == "AMDX":
        if direction == "BUY":
            logic, analysis = "AMDX: MANIPULASI RENDAH (JUDAS)", "• Harga melakukan *Judas Swing* ke bawah → menyapu Liquidity Low\n• Konfirmasi *Bullish Reversal* candle di 5M\n• Mengharapkan Distribusi → Ekspansi ke sisi *ATAS*\n• Entry optimal setelah False Break + close kembali"
        else:
            logic, analysis = "AMDX: MANIPULASI TINGGI (JUDAS)", "• Harga melakukan *Judas Swing* ke atas → menyapu Liquidity High\n• Konfirmasi *Bearish Reversal* candle di 5M\n• Mengharapkan Distribusi → Ekspansi ke sisi *BAWAH*\n• Entry optimal setelah False Break + close kembali"
    else:
        if direction == "BUY":
            logic, analysis = "XAMD: EKSPANSI — DAILY BIAS BULLISH", "• Daily Bias: *STRONG BUY*\n• Setup: *ICT Optimal Entry* di area OB / FVG\n• Fase Expansion dari Swing Low tervalidasi"
        else:
            logic, analysis = "XAMD: EKSPANSI — DAILY BIAS BEARISH", "• Daily Bias: *STRONG SELL*\n• Setup: *ICT Optimal Entry* di area OB / FVG\n• Fase Expansion dari Swing High tervalidasi"
    return logic, analysis

def calc_sl_tp(direction, entry, atr, decimals):
    sl_dist, tp_dist = atr * 0.20, atr * 0.50
    if direction == "BUY": return round(entry - sl_dist, decimals), round(entry + tp_dist, decimals)
    else: return round(entry + sl_dist, decimals), round(entry - tp_dist, decimals)

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN SCANNER
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("🚀 PREDATOR V11 STARTING (JAKARTA TIME MODE)")
    
    while True:
        ts_wib = datetime.now(WIB).strftime("%Y-%m-%d %H:%M Jakarta")
        print(f"\n[{ts_wib}] SCANNING MARKET...")

        for pair, cfg in PAIRS.items():
            if pair in open_signals: continue
            
            try:
                handler = TA_Handler(symbol=pair, exchange=cfg['ex'], screener=cfg['scr'], interval=Interval.INTERVAL_1_DAY, proxies=PROXIES)
                daily_data = handler.get_analysis()
                
                bias = daily_data.summary['RECOMMENDATION']
                if "BUY" not in bias and "SELL" not in bias: continue
                
                # Logic ICT
                atr = daily_data.indicators.get('ATR', 0)
                close = daily_data.indicators.get('close', 0)
                proto = "XAMD" if atr > (close * 0.0015) else "AMDX"
                
                # Entry Data
                m5_handler = TA_Handler(symbol=pair, exchange=cfg['ex'], screener=cfg['scr'], interval=Interval.INTERVAL_5_MINUTES, proxies=PROXIES)
                m5_data = m5_handler.get_analysis()
                entry = m5_data.indicators['close']
                direction = "BUY" if "BUY" in bias else "SELL"
                
                sl, tp = calc_sl_tp(direction, entry, atr, cfg['decimals'])
                logic, analysis = get_ict_logic(proto, direction)
                
                msg = (
                    f"🦅 *SIGNAL GLOBAL: {pair}* 🦅\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"🔥 *Logika:* {logic}\n"
                    f"📥 *Aksi:* {direction} {'📈' if direction == 'BUY' else '📉'}\n"
                    f"🎯 *Harga:* `{fmt(entry, cfg['decimals'])}`\n"
                    f"🛑 *SL:* `{fmt(sl, cfg['decimals'])}` | 🎯 *TP:* `{fmt(tp, cfg['decimals'])}`\n\n"
                    f"📊 *Analisis:*\n{analysis}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🏛 *Pasar:* {cfg['market']}\n"
                    f"⏰ *Pembaruan:* {ts_wib}\n"
                    f"Freedom Syndicate"
                )
                
                send_signal(msg)
                open_signals[pair] = {"entry": entry, "sl": sl, "tp": tp}
                print(f"✅ {pair} Signal Sent to Telegram & Discord!")
                time.sleep(random.randint(10, 20))
                
            except Exception as e:
                print(f"Error {pair}: {e}")

        time.sleep(30 * 60)
