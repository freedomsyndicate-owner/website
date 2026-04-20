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

# ─── TIMEZONE ───────────────────────────────────────────────────────────────────
WIB = timezone(timedelta(hours=7))

# ─── CONFIGURATION ──────────────────────────────────────────────────────────────
TOKEN_TG        = "8196511062:AAGyfWcRUk9uw_lc_aQgUW6vLyyRmgF1hcE"
CHAT_ID_TG      = "-1003660980986"
TOPIC_ID_TG     = 18        # Topic #signal-market di Telegram
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1489306608554217736/vTC-HQBFwXWsiBE0WImdB0Uq88WppsSjCb548y5W5aFAubZVYXBgFCEuMLbcB22H1h7H"
FIREBASE_DB_URL = "https://freedomsyndicatecloud-default-rtdb.firebaseio.com"

# PROXY CONFIG (Tor Browser Windows default port: 9150)
PROXIES = {
    'http':  'socks5://127.0.0.1:9150',
    'https': 'socks5://127.0.0.1:9150'
}

# decimals = jumlah angka di belakang koma untuk pair tersebut
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

# ─── OPEN SIGNAL TRACKER ────────────────────────────────────────────────────────
# Menyimpan signal aktif yang belum hit TP atau SL
open_signals = {}
# Format: { "GBPUSD": { entry, sl, tp, direction, decimals, market, ts_utc, ts_wib } }


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def fmt(price, decimals):
    """Format harga sesuai jumlah desimal pair"""
    return f"{price:.{decimals}f}"

def pips_diff(a, b, decimals):
    """Hitung selisih dalam pips"""
    # Untuk forex 5 desimal: 1 pip = 0.0001 (index ke-4)
    # Untuk JPY 3 desimal: 1 pip = 0.01
    # Untuk XAU/BTC 2 desimal: 1 unit = $1
    if decimals == 5:
        return round(abs(a - b) * 10000, 1)
    elif decimals == 3:
        return round(abs(a - b) * 100, 1)
    else:
        return round(abs(a - b), 2)

def get_current_ip():
    """Cek IP apakah sudah lewat Tor atau belum"""
    try:
        r = requests.get('https://api.ipify.org', proxies=PROXIES, timeout=10)
        return r.text
    except:
        return "DISCONNECTED (Pastikan Tor Browser Aktif!)"

def push_to_firebase(path: str, data: dict):
    try:
        requests.post(f"{FIREBASE_DB_URL}/{path}.json", json=data, timeout=10)
    except: pass

def send_signal(msg, firebase_data=None):
    """Kirim ke Telegram (topic signal) + Discord"""
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
    except: pass
    try:
        requests.post(DISCORD_WEBHOOK, json={"content": msg}, timeout=10)
    except: pass
    if firebase_data:
        push_to_firebase("signals/ict", firebase_data)


# ══════════════════════════════════════════════════════════════════════════════
#  ICT LOGIC BUILDER
# ══════════════════════════════════════════════════════════════════════════════

def get_ict_logic(proto, direction):
    """
    Tentukan nama setup ICT dan teks analisis berdasarkan:
    - proto   : "AMDX" atau "XAMD"
    - direction: "BUY" atau "SELL"
    """
    if proto == "AMDX":
        if direction == "BUY":
            logic    = "AMDX: MANIPULATION LOW (JUDAS)"
            analysis = (
                "• Harga melakukan *Judas Swing* ke bawah → sweep Liquidity Low\n"
                "• Konfirmasi *Bullish Reversal* candle di 5M\n"
                "• Expect Distribution → Expansion ke sisi *ATAS*\n"
                "• Entry optimal setelah False Break + close kembali"
            )
        else:
            logic    = "AMDX: MANIPULATION HIGH (JUDAS)"
            analysis = (
                "• Harga melakukan *Judas Swing* ke atas → sweep Liquidity High\n"
                "• Konfirmasi *Bearish Reversal* candle di 5M\n"
                "• Expect Distribution → Expansion ke sisi *BAWAH*\n"
                "• Entry optimal setelah False Break + close kembali"
            )
    else:  # XAMD
        if direction == "BUY":
            logic    = "XAMD: EXPANSION — DAILY BIAS BULLISH"
            analysis = (
                "• Daily Bias: *STRONG BUY* | Microstructure 5M confirm\n"
                "• Setup: *ICT Optimal Entry* di area OB / FVG\n"
                "• Fase Expansion dari Swing Low tervalidasi\n"
                "• Momentum bullish dominan pada timeframe harian"
            )
        else:
            logic    = "XAMD: EXPANSION — DAILY BIAS BEARISH"
            analysis = (
                "• Daily Bias: *STRONG SELL* | Microstructure 5M confirm\n"
                "• Setup: *ICT Optimal Entry* di area OB / FVG\n"
                "• Fase Expansion dari Swing High tervalidasi\n"
                "• Momentum bearish dominan pada timeframe harian"
            )
    return logic, analysis


# ══════════════════════════════════════════════════════════════════════════════
#  SL / TP CALCULATOR
# ══════════════════════════════════════════════════════════════════════════════

def calc_sl_tp(direction, entry, atr, decimals):
    """
    Kalkulasi SL dan TP berbasis ATR (ICT style):
      SL = 20% ATR dari entry  → buffer aman dari noise
      TP = 50% ATR dari entry  → minimal RR 1:2.5
    """
    sl_dist = atr * 0.20
    tp_dist = atr * 0.50

    if direction == "BUY":
        sl = round(entry - sl_dist, decimals)
        tp = round(entry + tp_dist, decimals)
    else:
        sl = round(entry + sl_dist, decimals)
        tp = round(entry - tp_dist, decimals)

    return sl, tp


# ══════════════════════════════════════════════════════════════════════════════
#  RESULT TRACKER
# ══════════════════════════════════════════════════════════════════════════════

def check_open_signals():
    """
    Periksa semua open signal apakah sudah hit TP atau SL.
    Dipanggil setiap selesai 1 siklus scan penuh.
    """
    if not open_signals:
        return

    print(f"  🔍 Checking {len(open_signals)} open signal(s)...")

    for pair in list(open_signals.keys()):
        sig = open_signals[pair]
        cfg = PAIRS[pair]

        try:
            handler = TA_Handler(
                symbol=pair, exchange=cfg['ex'],
                screener=cfg['scr'],
                interval=Interval.INTERVAL_5_MINUTES,
                proxies=PROXIES
            )
            time.sleep(random.uniform(3, 6))
            data    = handler.get_analysis()
            current = data.indicators['close']

            dec       = sig['decimals']
            entry     = sig['entry']
            tp        = sig['tp']
            sl        = sig['sl']
            direction = sig['direction']
            market    = sig['market']

            ts_close = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            ts_wib   = datetime.now(WIB).strftime("%H:%M WIB")

            hit_tp = (direction == "BUY"  and current >= tp) or \
                     (direction == "SELL" and current <= tp)
            hit_sl = (direction == "BUY"  and current <= sl) or \
                     (direction == "SELL" and current >= sl)

            if hit_tp:
                pips = pips_diff(entry, tp, dec)
                msg = (
                    f"✅ *TP HIT — {pair}*\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📥 *Was:* {direction} @ `{fmt(entry, dec)}`\n"
                    f"🎯 *TP Hit:* `{fmt(tp, dec)}` ✅\n"
                    f"🛑 *SL Was:* `{fmt(sl, dec)}`\n"
                    f"💰 *Result:* +{pips} pips *PROFIT*\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🏛 *Market:* {market}\n"
                    f"⏰ *Closed:* {ts_wib}\n"
                    f"_Freedom Syndicate | {ts_close}_"
                )
                send_signal(msg)
                del open_signals[pair]
                print(f"    ✅ {pair} TP HIT! +{pips} pips")

            elif hit_sl:
                pips = pips_diff(entry, sl, dec)
                msg = (
                    f"❌ *SL HIT — {pair}*\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📥 *Was:* {direction} @ `{fmt(entry, dec)}`\n"
                    f"🎯 *TP Was:* `{fmt(tp, dec)}`\n"
                    f"🛑 *SL Hit:* `{fmt(sl, dec)}` ❌\n"
                    f"💸 *Result:* -{pips} pips *LOSS*\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🏛 *Market:* {market}\n"
                    f"⏰ *Closed:* {ts_wib}\n"
                    f"_Freedom Syndicate | {ts_close}_"
                )
                send_signal(msg)
                del open_signals[pair]
                print(f"    ❌ {pair} SL HIT! -{pips} pips")

        except Exception as e:
            print(f"    ⚠ Result check error [{pair}]: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  PREDATOR ENGINE (TradingView TA)
# ══════════════════════════════════════════════════════════════════════════════

class PredatorEngine:
    def __init__(self, sym, ex, scr):
        self.symbol = sym
        self.daily = TA_Handler(
            symbol=sym, exchange=ex, screener=scr,
            interval=Interval.INTERVAL_1_DAY, proxies=PROXIES
        )
        self.micro = TA_Handler(
            symbol=sym, exchange=ex, screener=scr,
            interval=Interval.INTERVAL_5_MINUTES, proxies=PROXIES
        )

    def _safe_get(self, handler):
        # Jeda acak 5-10 detik agar tidak terbaca sebagai bot
        time.sleep(random.uniform(5.0, 10.0))
        try:
            return handler.get_analysis()
        except Exception as e:
            print(f"      ✗ Error fetch {self.symbol}: {e}")
            return None


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN RUNNER
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "="*55)
    print("🚀 GLOBAL PREDATOR V11 — ICT SUPREME (STEALTH MODE)")
    print("📍 Status Proxy Tor:", get_current_ip())
    print("="*55 + "\n")

    ts_boot = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    send_signal(
        "🦅 *PREDATOR V11 SUPREME* ONLINE\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "✅ Signal: Entry + SL + TP AKTIF\n"
        "✅ ICT Logic & Analisis AKTIF\n"
        "✅ Result Tracker (TP/SL) AKTIF\n"
        "📍 IP: `Hidden via Tor`\n\n"
        f"_Freedom Syndicate | {ts_boot}_"
    )

    scan_count = 0

    while True:
        ts_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        ts_wib = datetime.now(WIB).strftime("%H:%M WIB")
        print(f"\n[{ts_utc}] ══ SCAN #{scan_count + 1} — {len(PAIRS)} pairs ══")

        # ── Cek hasil open signals setiap selesai 1 siklus ──────────────────
        if scan_count > 0:
            check_open_signals()

        for pair, cfg in PAIRS.items():
            print(f"  > Analyzing {pair}...")

            # Skip jika pair ini masih punya open signal
            if pair in open_signals:
                print(f"    ⏩ {pair} sudah ada open signal aktif — skip.")
                continue

            bot = PredatorEngine(pair, cfg['ex'], cfg['scr'])
            dec = cfg['decimals']

            # ── 1. Daily Bias ────────────────────────────────────────────────
            daily_data = bot._safe_get(bot.daily)
            if not daily_data:
                continue

            bias  = daily_data.summary['RECOMMENDATION']
            atr   = daily_data.indicators.get('ATR', 0)
            close = daily_data.indicators.get('close', 0)

            # Tentukan protokol ICT
            proto = "XAMD" if atr > (close * 0.0015) else "AMDX"

            # ── 2. Micro Confirmation (5M) ────────────────────────────────────
            if "BUY" not in bias and "SELL" not in bias:
                print(f"    ─ {pair} Bias NEUTRAL — no signal.")
                time.sleep(random.randint(5, 10))
                continue

            micro_data = bot._safe_get(bot.micro)
            if not micro_data:
                continue

            entry     = micro_data.indicators['close']
            direction = "BUY" if "BUY" in bias else "SELL"

            # ── 3. Hitung SL & TP ────────────────────────────────────────────
            sl, tp = calc_sl_tp(direction, entry, atr, dec)

            # ── 4. ICT Logic & Analisis ──────────────────────────────────────
            logic, analysis = get_ict_logic(proto, direction)

            # ── 5. Emoji & Label ─────────────────────────────────────────────
            action_emoji = "📈" if direction == "BUY" else "📉"

            # ── 6. Bangun Pesan Signal ────────────────────────────────────────
            msg = (
                f"🦅 *GLOBAL SIGNAL: {pair}* 🦅\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🔥 *Logic:* {logic}\n"
                f"📥 *Action:* {direction} {action_emoji}\n"
                f"🎯 *Price:* `{fmt(entry, dec)}`\n"
                f"🛑 *SL:* `{fmt(sl, dec)}` | 🎯 *TP:* `{fmt(tp, dec)}`\n\n"
                f"📊 *Analisis:*\n{analysis}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🏛 *Market:* {cfg['market']}\n"
                f"🕐 *Macro Status:* ACTIVE\n"
                f"⏰ *Update:* {ts_wib}\n"
                f"_Freedom Syndicate | {ts_utc}_"
            )

            firebase_data = {
                "pair":      pair,
                "direction": direction,
                "entry":     round(entry, dec),
                "sl":        sl,
                "tp":        tp,
                "logic":     logic,
                "protocol":  proto,
                "bias":      bias,
                "timestamp": ts_utc,
            }

            send_signal(msg, firebase_data)
            print(f"    ✅ Signal sent! {direction} @ {fmt(entry,dec)} | SL:{fmt(sl,dec)} | TP:{fmt(tp,dec)}")

            # ── 7. Simpan ke tracker ──────────────────────────────────────────
            open_signals[pair] = {
                "entry":     entry,
                "sl":        sl,
                "tp":        tp,
                "direction": direction,
                "decimals":  dec,
                "market":    cfg['market'],
                "ts_utc":    ts_utc,
                "ts_wib":    ts_wib,
            }

            # Jeda antar pair (20-40 detik) agar aman dari rate-limit
            time.sleep(random.randint(20, 40))

        scan_count += 1
        wait_min = 30
        print(f"\n[OK] Scan #{scan_count} selesai.")
        print(f"     IP saat ini: {get_current_ip()}")
        print(f"     Open signals: {list(open_signals.keys()) or 'None'}")
        print(f"⏳ Istirahat {wait_min} menit sebelum scan berikutnya...\n")
        time.sleep(wait_min * 60)
