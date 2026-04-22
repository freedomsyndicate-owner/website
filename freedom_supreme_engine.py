"""
╔══════════════════════════════════════════════════════════════╗
║        DOMS FREEDOM SYNDICATE — SUPREME ENGINE v4.0         ║
║   PURE ICT: OB · FVG · CISD · BSL/SSL · P/D · SMT · AMDX  ║
║   ZERO OSCILLATORS — 100% Price Action & Structure          ║
╚══════════════════════════════════════════════════════════════╝
"""

import requests
import time
import random
from datetime import datetime, timezone, timedelta
from tradingview_ta import TA_Handler, Interval

# ══════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════
WIB = timezone(timedelta(hours=7))
UTC = timezone.utc
BOT_NAME = "Doms Freedom Syndicate"

TOKEN_TG_PREDATOR = "8196511062:AAGyfWcRUk9uw_lc_aQgUW6vLyyRmgF1hcE"
TOKEN_TG_SUPREME  = "8794811012:AAFUrcWYI-5mldlwXrIl8AyjVvgDvNRKRWk"
CHAT_ID_TG        = "-1003660980986"
TOPIC_ID_GENERAL  = 18

DISCORD_PREDATOR  = "https://discord.com/api/webhooks/1489306608554217736/vTC-HQBFwXWsiBE0WImdB0Uq88WppsSjCb548y5W5aFAubZVYXBgFCEuMLbcB22H1h7H"
DISCORD_FUNDA     = "https://discord.com/api/webhooks/1489314765074595840/BRby0L3L4cfUUGyDpihSBjRlHPpNutFiZWF5mFYU6CpCkjoEA9Hw1A2W0c6LEUgO30i7"
FIREBASE_URL      = "https://freedomsyndicatecloud-default-rtdb.firebaseio.com"

PROXIES          = {'http': 'socks5://127.0.0.1:9150', 'https': 'socks5://127.0.0.1:9150'}
TOR_CONTROL_PORT = 9051
TOR_PASSWORD     = ""

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1",
]

# ══════════════════════════════════════════════════════════════
# PAIRS + SMT CONFIG
# ══════════════════════════════════════════════════════════════
PAIRS = {
    "XAUUSD":  {"ex": "OANDA",   "scr": "cfd",   "dec": 2},
    "GBPUSD":  {"ex": "OANDA",   "scr": "forex",  "dec": 5},
    "EURUSD":  {"ex": "OANDA",   "scr": "forex",  "dec": 5},
    "USDJPY":  {"ex": "OANDA",   "scr": "forex",  "dec": 3},
    "BTCUSDT": {"ex": "BINANCE", "scr": "crypto", "dec": 2},
}

# SMT (Smart Money Technique) — pair korelasi untuk deteksi divergence institusional
# XAUUSD vs XAUEUR: Gold dalam USD vs Gold dalam EUR
# GBPUSD vs EURUSD: Sterling vs Euro — sering diverge saat manipulation
# USDJPY vs USDCHF: Safe-haven divergence
# BTCUSDT vs ETHUSDT: Crypto SMT
SMT_PAIRS = {
    "XAUUSD":  {"pair": "XAUEUR",  "ex": "OANDA",   "scr": "cfd",   "dec": 2},
    "GBPUSD":  {"pair": "EURUSD",  "ex": "OANDA",   "scr": "forex", "dec": 5},
    "EURUSD":  {"pair": "GBPUSD",  "ex": "OANDA",   "scr": "forex", "dec": 5},
    "USDJPY":  {"pair": "USDCHF",  "ex": "OANDA",   "scr": "forex", "dec": 5},
    "BTCUSDT": {"pair": "ETHUSDT", "ex": "BINANCE", "scr": "crypto","dec": 2},
}

IMPACT_MAP = {"High": "🔴 HIGH", "Medium": "🟡 MED", "Low": "🟢 LOW"}

# ICT SL config per pair: (min_sl, max_sl, ob_height_atr_ratio, sl_buffer_atr_ratio)
# OB Height: estimasi tinggi candle Order Block dari ATR
# SL Buffer: jarak tambahan di bawah/atas OB agar SL tidak di dalam OB
PAIR_SL_CONFIG = {
    "XAUUSD":  (1.50, 8.00,  0.35, 0.15),  # Gold: OB ~$1.5-3, SL buffer $0.5-1
    "GBPUSD":  (0.0015, 0.0040, 0.35, 0.15),  # 15-40 pip SL, OB ~10-15 pips tall
    "EURUSD":  (0.0015, 0.0040, 0.35, 0.15),
    "USDJPY":  (0.150, 0.400, 0.35, 0.15),
    "BTCUSDT": (200.0, 1000.0, 0.35, 0.15),
}

# Anti-spam trackers
sent_fundamentals = set()
last_signal_time  = {}


# ══════════════════════════════════════════════════════════════
# TOR UTILS
# ══════════════════════════════════════════════════════════════

def rotate_tor_ip():
    try:
        import socket
        s = socket.socket()
        s.connect(('127.0.0.1', TOR_CONTROL_PORT))
        s.send(b'AUTHENTICATE "' + TOR_PASSWORD.encode() + b'"\r\n'); s.recv(128)
        s.send(b'SIGNAL NEWNYM\r\n'); s.recv(128)
        s.close()
        time.sleep(3)
        print("🔄 Tor IP rotated.")
    except Exception as e:
        print(f"⚠️ Tor rotate failed: {e}")

def get_headers():
    return {"User-Agent": random.choice(USER_AGENTS)}

def safe_ta(symbol, exchange, screener, interval):
    """Wrapper TA_Handler dengan error handling"""
    try:
        h = TA_Handler(symbol=symbol, exchange=exchange, screener=screener,
                       interval=interval, proxies=PROXIES)
        return h.get_analysis()
    except Exception as e:
        print(f"  ⚠️ TA Error [{symbol} {interval}]: {e}")
        return None


# ══════════════════════════════════════════════════════════════
# ICT SESSION ENGINE — Referensi UTC-4 (New York Time) → WIB
# ══════════════════════════════════════════════════════════════
#
#  Konversi: UTC-4 + 11 jam = WIB (UTC+7)
#
#  ┌─────────────────────────────────────────────────────────┐
#  │  SESI           UTC-4           WIB (UTC+7)             │
#  │  ─────────────────────────────────────────────────────  │
#  │  Asia Session   20:00–00:00     07:00–11:00             │
#  │  London Session 02:00–05:00     13:00–16:00  ← gambar   │
#  │  NY AM Session  09:30–11:00     20:30–22:00  ← gambar   │
#  │                                                         │
#  │  ICT KILLZONES (prime window, reversal entry):          │
#  │  Asia KZ        20:00–00:00     07:00–11:00             │
#  │  London KZ      02:00–05:00     13:00–16:00             │
#  │  NY AM KZ       09:30–11:00     20:30–22:00             │
#  │  NY PM KZ       14:00–16:00     01:00–03:00             │
#  │                                                         │
#  │  ICT SILVER BULLET (ultra-high prob, 1-hour window):    │
#  │  London SB      03:00–04:00     14:00–15:00             │
#  │  NY AM SB       10:00–11:00     21:00–22:00             │
#  │  NY PM SB       14:00–15:00     01:00–02:00             │
#  │                                                         │
#  │  ICT MACRO WINDOWS (90-min micro-cycle transition):     │
#  │  London Open    02:33           13:33                   │
#  │  London AM      04:03           15:03                   │
#  │  NY Pre-Open    08:50–09:10     19:50–20:10             │
#  │  NY AM ⚡       09:50–10:10     20:50–21:10 ← terkuat  │
#  │  NY AM2         10:50–11:10     21:50–22:10             │
#  │  NY PM          11:50–12:10     22:50–23:10             │
#  │                                                         │
#  │  AMDX DAILY (based on sesi):                            │
#  │  A Accumulation 20:00–02:00 UTC-4  → 07:00–13:00 WIB   │
#  │  M Manipulation 02:00–05:00 UTC-4  → 13:00–16:00 WIB   │
#  │  D Distribution 05:00–09:30 UTC-4  → 16:00–20:30 WIB   │
#  │  X eXpansion    09:30–16:00 UTC-4  → 20:30–03:00 WIB   │
#  └─────────────────────────────────────────────────────────┘
#
#  BOT HANYA AKTIF saat Killzone ATAU Silver Bullet.
#  Di luar window itu = TIDUR, tidak scan, tidak kirim signal.
# ══════════════════════════════════════════════════════════════

# Semua window dalam total menit sejak 00:00 WIB
# Format: (start_min, end_min, label, priority)
# priority: 3=Silver Bullet, 2=Killzone, 1=Macro only

_WINDOWS = [
    # ── Asia Killzone ──────────────────────────────────────────
    (7*60,      11*60,     "ASIA KILLZONE",        2, "ASIA"),
    # ── London Killzone ───────────────────────────────────────
    (13*60,     16*60,     "LONDON KILLZONE",      2, "LONDON"),
    # ── London Silver Bullet (dalam London KZ) ────────────────
    (14*60,     15*60,     "LONDON SILVER BULLET", 3, "LONDON"),
    # ── NY AM Killzone ────────────────────────────────────────
    (20*60+30,  22*60,     "NY AM KILLZONE",       2, "NEW YORK"),
    # ── NY AM Silver Bullet ───────────────────────────────────
    (21*60,     22*60,     "NY AM SILVER BULLET",  3, "NEW YORK"),
    # ── NY PM Killzone (lewat tengah malam) ───────────────────
    (1*60,      3*60,      "NY PM KILLZONE",       2, "NEW YORK"),
    # ── NY PM Silver Bullet ───────────────────────────────────
    (1*60,      2*60,      "NY PM SILVER BULLET",  3, "NEW YORK"),
]

_MACROS = [
    (13*60+33, 13*60+50, "LONDON OPEN MACRO"),
    (15*60+3,  15*60+20, "LONDON AM MACRO"),
    (19*60+50, 20*60+10, "NY PRE-OPEN MACRO"),
    (20*60+50, 21*60+10, "NY AM MACRO ⚡"),
    (21*60+50, 22*60+10, "NY AM2 MACRO"),
    (22*60+50, 23*60+10, "NY PM MACRO"),
]

def _total_min():
    now = datetime.now(WIB)
    return now.hour * 60 + now.minute

def minutes_until_next_window():
    """
    Hitung berapa menit sampai window Killzone/SB berikutnya.
    Dipakai bot untuk tidur efisien, bukan polling tiap menit.
    """
    t = _total_min()
    # Kumpulkan semua start time dari windows
    starts = []
    for s, e, lbl, pri, sess in _WINDOWS:
        # Kalau window sudah lewat hari ini, tambah 1440 (besok)
        starts.append(s if s > t else s + 1440)
    next_start = min(starts)
    wait = next_start - t
    return max(wait, 1)

def get_session_info():
    """Return context sesi ICT saat ini."""
    t = _total_min()

    # ── Cari window aktif tertinggi prioritasnya ──────────────
    active_windows = [(pri, lbl, sess) for s, e, lbl, pri, sess in _WINDOWS if s <= t < e]
    # Sort by priority desc
    active_windows.sort(key=lambda x: x[0], reverse=True)

    if active_windows:
        priority, window_label, session = active_windows[0]
        is_killzone  = priority >= 2
        is_silver    = priority == 3
        is_active    = True
    else:
        window_label = "OFF-WINDOW"
        session      = "OFF"
        is_killzone  = False
        is_silver    = False
        is_active    = False

    # Killzone icon
    if is_silver:
        kz_icon = f"🥈 SILVER BULLET: {window_label}"
    elif is_killzone:
        kz_icon = f"🗡️ KILLZONE: {window_label}"
    else:
        kz_icon = "💤 OFF-WINDOW — Bot menunggu Killzone berikutnya"

    # ── Macro ─────────────────────────────────────────────────
    macro = next((lbl for s, e, lbl in _MACROS if s <= t < e), None)

    # ── AMDX Phase ────────────────────────────────────────────
    if 7*60 <= t < 13*60:
        phase, amdx = "A — ACCUMULATION (Asia builds range)",          "A"
    elif 13*60 <= t < 16*60:
        phase, amdx = "M — MANIPULATION (London Judas Swing)",         "M"
    elif 16*60 <= t < 20*60+30:
        phase, amdx = "D — DISTRIBUTION (Pre-NY setup)",               "D"
    elif t >= 20*60+30 or t < 3*60:
        phase, amdx = "X — eXPANSION (NY true direction)",             "X"
    else:
        phase, amdx = "TRANSITION — Tunggu Killzone",                  "OFF"

    return {
        "session":    session,
        "killzone":   kz_icon,
        "silver":     window_label if is_silver else None,
        "macro":      macro,
        "phase":      phase,
        "amdx":       amdx,
        "is_active":  is_active,
        "is_killzone":is_killzone,
        "is_silver":  is_silver,
        "priority":   active_windows[0][0] if active_windows else 0,
    }


# ══════════════════════════════════════════════════════════════
# HTF CASCADE BIAS (D1 > H4 > H1 > M15)
# ══════════════════════════════════════════════════════════════

def get_htf_bias(pair, cfg):
    """
    ICT HTF cascade:
    D1 menentukan daily bias (paling dominan).
    H4 konfirmasi intermediate struktur.
    H1 entry alignment.
    M15 trigger timeframe.

    Scoring: D1=4, H4=3, H1=2, M15=1 (total=10)
    Confidence >60% = valid signal.
    """
    tf_config = [
        (Interval.INTERVAL_1_DAY,      4, "D1 "),
        (Interval.INTERVAL_4_HOURS,    3, "H4 "),
        (Interval.INTERVAL_1_HOUR,     2, "H1 "),
        (Interval.INTERVAL_15_MINUTES, 1, "M15"),
    ]

    buy_score, sell_score, total_w = 0, 0, 0
    details = []

    for interval, w, tf_name in tf_config:
        a = safe_ta(pair, cfg['ex'], cfg['scr'], interval)
        if not a:
            details.append(f"⬜ {tf_name}: N/A")
            continue
        rec = a.summary['RECOMMENDATION']
        bv  = a.summary.get('BUY', 0)
        sv  = a.summary.get('SELL', 0)
        nv  = a.summary.get('NEUTRAL', 0)

        if "BUY" in rec:
            buy_score += w; emoji = "📈"; trend = "BULLISH"
        elif "SELL" in rec:
            sell_score += w; emoji = "📉"; trend = "BEARISH"
        else:
            emoji = "⚖️"; trend = "NEUTRAL"

        details.append(f"{emoji} {tf_name}: {trend}  ({bv}▲ {sv}▼ {nv}—)")
        total_w += w
        time.sleep(0.4)

    if buy_score > sell_score:
        direction  = "BUY"
        confidence = (buy_score / max(total_w, 1)) * 100
    elif sell_score > buy_score:
        direction  = "SELL"
        confidence = (sell_score / max(total_w, 1)) * 100
    else:
        direction  = "NEUTRAL"
        confidence = 0

    return direction, round(confidence, 1), details


# ══════════════════════════════════════════════════════════════
# SMT DIVERGENCE (Smart Money Technique)
# ══════════════════════════════════════════════════════════════

def check_smt(pair, main_m15_rec, cfg):
    """
    SMT = Smart Money Technique (bukan Tool).
    Bandingkan pair utama dengan pair korelasi pada M15.

    XAUUSD vs XAUEUR:
      Gold dalam USD naik tapi dalam EUR turun → USD weakness manipulation
      Gold dalam USD turun tapi dalam EUR naik → Bullish SMT (sweep LOW sebelum naik)

    GBPUSD vs EURUSD:
      GBP turun tapi EUR naik → GBPUSD sudah disweep, akan balik naik

    Logic:
      SMT BULLISH: main BEARISH, correlated BULLISH → institutional sedang sweep LOW,
                   true direction NAIK → cari BUY
      SMT BEARISH: main BULLISH, correlated BEARISH → sweep HIGH, true direction TURUN
                   → cari SELL
      CONFLUENT:   Keduanya searah → tambah confidence signal existing direction
    """
    if pair not in SMT_PAIRS:
        return "⬜ SMT: Tidak dikonfig untuk pair ini", False, False

    smt = SMT_PAIRS[pair]
    a   = safe_ta(smt['pair'], smt['ex'], smt['scr'], Interval.INTERVAL_15_MINUTES)
    if not a:
        return f"⬜ SMT: {smt['pair']} fetch error", False, False

    smt_rec     = a.summary['RECOMMENDATION']
    main_bear   = "SELL" in main_m15_rec
    main_bull   = "BUY"  in main_m15_rec
    corr_bear   = "SELL" in smt_rec
    corr_bull   = "BUY"  in smt_rec

    if main_bear and corr_bull:
        msg = (
            f"✅ SMT BULLISH DIVERGENCE\n"
            f"   {pair}: BEARISH  |  {smt['pair']}: BULLISH\n"
            f"   → Sweep LOW sebelum NAIK (Institutional BUY Setup)"
        )
        return msg, True, False

    elif main_bull and corr_bear:
        msg = (
            f"✅ SMT BEARISH DIVERGENCE\n"
            f"   {pair}: BULLISH  |  {smt['pair']}: BEARISH\n"
            f"   → Sweep HIGH sebelum TURUN (Institutional SELL Setup)"
        )
        return msg, False, True

    else:
        align = "BULLISH" if main_bull else "BEARISH" if main_bear else "NEUTRAL"
        msg = (
            f"⬜ SMT CONFLUENT ({align})\n"
            f"   {pair} & {smt['pair']} searah → Tambah confidence"
        )
        return msg, False, False


# ══════════════════════════════════════════════════════════════
# PURE ICT PRICE ACTION CONFIRMATION (M15 + M5)
# ZERO OSCILLATORS — Candle structure only
# ══════════════════════════════════════════════════════════════

def check_ict_pa(pair, cfg, direction, entry, atr):
    """
    100% Pure ICT Price Action — NO RSI, NO MACD, NO Stochastic.
    Semua konfirmasi berbasis STRUCTURE & CANDLE, bukan oscillator.

    ┌─────────────────────────────────────────────────────────────┐
    │ 1. CISD (Change In State of Delivery)              [3 pts]  │
    │    Bukan indicator — ini adalah CANDLE yang close           │
    │    DI ATAS swing high (Bullish) atau DI BAWAH swing low    │
    │    (Bearish). Bukti institutional delivery shift.           │
    │    Proxy: M15 close > R1 (BUY) atau close < S1 (SELL)     │
    │           + M5 candle konfirmasi arah                       │
    │                                                             │
    │ 2. Displacement / FVG (Fair Value Gap)             [2 pts]  │
    │    Candle besar (body > ATR × 0.5) = institutional move.   │
    │    Move besar ini menciptakan FVG/Imbalance di belakangnya. │
    │    Price akan retest FVG (= OB zone) sebelum lanjut.       │
    │                                                             │
    │ 3. Liquidity Sweep (BSL / SSL)                     [2 pts]  │
    │    BUY: Wick candle menembus S1 (sweep SSL/EQL)            │
    │         tapi CLOSE kembali di atas S1 → institutional buy  │
    │    SELL: Wick candle menembus R1 (sweep BSL/EQH)           │
    │          tapi CLOSE kembali di bawah R1 → institutional    │
    │          sell                                               │
    │                                                             │
    │ 4. Premium / Discount Alignment                    [2 pts]  │
    │    EQ = (R1 + S1) / 2 = Session Equilibrium (50% level)    │
    │    BUY harus di Discount (entry < EQ)                      │
    │    SELL harus di Premium (entry > EQ)                      │
    │    ICT: "BUY below EQ, SELL above EQ"                      │
    │                                                             │
    │ 5. OB Belum Ter-mitigasi                           [1 pt]   │
    │    OB mitigated = price sudah trade through OB → invalid.  │
    │    BUY OB valid: close belum menembus di bawah S2           │
    │    SELL OB valid: close belum menembus di atas R2           │
    │                                                             │
    │ SCORING:  8-10 = KONFIRMASI PENUH                          │
    │           5-7  = KONFIRMASI PARSIAL                         │
    │           <5   = AGRESIF (pastikan killzone aktif)          │
    └─────────────────────────────────────────────────────────────┘
    """
    confirmations = []
    score = 0

    # ── Fetch M15 & M5 data (price action only) ───────────────
    data = {}
    for interval, tf in [(Interval.INTERVAL_15_MINUTES, "M15"),
                         (Interval.INTERVAL_5_MINUTES,  "M5")]:
        a = safe_ta(pair, cfg['ex'], cfg['scr'], interval)
        if not a:
            confirmations.append(f"⬜ {tf}: data error")
            continue
        ind = a.indicators
        data[tf] = {
            "open":  ind.get('open')  or 0,
            "high":  ind.get('high')  or 0,
            "low":   ind.get('low')   or 0,
            "close": ind.get('close') or 0,
            "s1":    ind.get('Pivot.M.Classic.S1') or ind.get('Pivot.M.Fibonacci.S1') or (entry - atr),
            "s2":    ind.get('Pivot.M.Classic.S2') or ind.get('Pivot.M.Fibonacci.S2') or (entry - atr*2),
            "r1":    ind.get('Pivot.M.Classic.R1') or ind.get('Pivot.M.Fibonacci.R1') or (entry + atr),
            "r2":    ind.get('Pivot.M.Classic.R2') or ind.get('Pivot.M.Fibonacci.R2') or (entry + atr*2),
        }
        time.sleep(0.4)

    if not data:
        return "AGRESIF ⚠️", ["⬜ Semua timeframe error — masuk agresif"], 0

    # Ambil data dari timeframe yang tersedia
    m15 = data.get("M15", {})
    m5  = data.get("M5",  {})

    # Gunakan M15 sebagai referensi utama struktur, M5 sebagai trigger
    ref  = m15 if m15 else m5
    trig = m5  if m5  else m15

    s1 = ref.get('s1', entry - atr)
    s2 = ref.get('s2', entry - atr*2)
    r1 = ref.get('r1', entry + atr)
    r2 = ref.get('r2', entry + atr*2)
    eq = (r1 + s1) / 2   # Session Equilibrium = 50% level

    dec = {"XAUUSD":2,"GBPUSD":5,"EURUSD":5,"USDJPY":3,"BTCUSDT":2}.get(pair,5)

    # ── 1. CISD CHECK ─────────────────────────────────────────
    # Bullish CISD: M15 close DI ATAS R1 = broke above swing high → delivery shift UP
    # Bearish CISD: M15 close DI BAWAH S1 = broke below swing low → delivery shift DOWN
    m15_close = m15.get('close', 0)
    m15_open  = m15.get('open',  0)
    m5_close  = m5.get('close',  0)
    m5_open   = m5.get('open',   0)

    m15_bull = m15_close > m15_open
    m15_bear = m15_close < m15_open
    m5_bull  = m5_close  > m5_open
    m5_bear  = m5_close  < m5_open

    if direction == "BUY":
        # CISD Bullish: M15 close menembus struktur swing high (R1)
        # atau M5 displacement bullish dari OB zone (S1 area)
        cisd_m15 = m15_close > r1 and m15_bull
        cisd_m5  = m5_close  > (s1 + atr * 0.2) and m5_bull   # Bounced cleanly from OB
        cisd_ok  = cisd_m15 or cisd_m5
        if cisd_m15:
            confirmations.append(f"✅ CISD M15: Close {m15_close:.{dec}f} tembus swing HIGH {r1:.{dec}f} → Delivery shift BULLISH")
            score += 3
        elif cisd_m5:
            confirmations.append(f"✅ CISD M5: Bounce kuat dari OB zone (close {m5_close:.{dec}f} > {(s1+atr*0.2):.{dec}f})")
            score += 2
        else:
            confirmations.append(f"⚠️ CISD: Belum ada structural break — M15 close {m15_close:.{dec}f} masih di bawah R1 {r1:.{dec}f}")
    else:
        cisd_m15 = m15_close < s1 and m15_bear
        cisd_m5  = m5_close  < (r1 - atr * 0.2) and m5_bear
        cisd_ok  = cisd_m15 or cisd_m5
        if cisd_m15:
            confirmations.append(f"✅ CISD M15: Close {m15_close:.{dec}f} tembus swing LOW {s1:.{dec}f} → Delivery shift BEARISH")
            score += 3
        elif cisd_m5:
            confirmations.append(f"✅ CISD M5: Rejection kuat dari OB zone (close {m5_close:.{dec}f} < {(r1-atr*0.2):.{dec}f})")
            score += 2
        else:
            confirmations.append(f"⚠️ CISD: Belum ada structural break — M15 close {m15_close:.{dec}f} masih di atas S1 {s1:.{dec}f}")

    # ── 2. DISPLACEMENT / FVG ─────────────────────────────────
    # Displacement = candle body besar → pasti ada FVG di belakangnya
    # ICT: FVG = area imbalance yang akan di-retest sebelum harga lanjut
    m15_body = abs(m15_close - m15_open) if m15_close and m15_open else 0
    m5_body  = abs(m5_close  - m5_open)  if m5_close  and m5_open  else 0
    disp_thr = atr * 0.45   # Threshold displacement (45% ATR = significant move)

    if direction == "BUY":
        disp_ok = (m15_bull and m15_body > disp_thr) or (m5_bull and m5_body > disp_thr)
    else:
        disp_ok = (m15_bear and m15_body > disp_thr) or (m5_bear and m5_body > disp_thr)

    if disp_ok:
        bigger = max(m15_body, m5_body)
        confirmations.append(f"✅ DISPLACEMENT: Body {bigger:.{dec}f} > threshold {disp_thr:.{dec}f} → FVG terbentuk, price akan retest OB")
        score += 2
    else:
        confirmations.append(f"⚠️ DISPLACEMENT: Candle kecil (body M15:{m15_body:.{dec}f} M5:{m5_body:.{dec}f}) — FVG belum terbentuk / candle lemah")

    # ── 3. LIQUIDITY SWEEP (BSL / SSL) ───────────────────────
    # ICT: Harga harus SWEEP likuiditas dulu sebelum reversal
    # BUY = harga wick ke bawah S1 (sweep Equal Lows / SSL) lalu TOLAK ke atas → Bullish
    # SELL = harga wick ke atas R1 (sweep Equal Highs / BSL) lalu TOLAK ke bawah → Bearish
    m15_low  = m15.get('low',  entry)
    m15_high = m15.get('high', entry)
    m5_low   = m5.get('low',   entry)
    m5_high  = m5.get('high',  entry)

    if direction == "BUY":
        # Wick went below S1 (swept SSL) tapi close di atas S1
        sweep_m15 = m15_low < s1 and m15_close > s1
        sweep_m5  = m5_low  < s1 and m5_close  > s1
        sweep_ok  = sweep_m15 or sweep_m5
        if sweep_ok:
            low_ref = min(m15_low, m5_low)
            confirmations.append(f"✅ LIQUIDITY SWEEP: Wick swept SSL {s1:.{dec}f} (low: {low_ref:.{dec}f}) — Close balik atas → Institutional BUY absorption")
            score += 2
        else:
            confirmations.append(f"⚠️ SWEEP: SSL {s1:.{dec}f} belum di-sweep — kemungkinan akan test dulu sebelum naik")
    else:
        sweep_m15 = m15_high > r1 and m15_close < r1
        sweep_m5  = m5_high  > r1 and m5_close  < r1
        sweep_ok  = sweep_m15 or sweep_m5
        if sweep_ok:
            high_ref = max(m15_high, m5_high)
            confirmations.append(f"✅ LIQUIDITY SWEEP: Wick swept BSL {r1:.{dec}f} (high: {high_ref:.{dec}f}) — Close balik bawah → Institutional SELL distribution")
            score += 2
        else:
            confirmations.append(f"⚠️ SWEEP: BSL {r1:.{dec}f} belum di-sweep — kemungkinan akan test dulu sebelum turun")

    # ── 4. PREMIUM / DISCOUNT ALIGNMENT ──────────────────────
    # ICT Rule: BUY di Discount (bawah EQ 50%), SELL di Premium (atas EQ)
    # EQ = midpoint antara swing high dan swing low sesi ini
    eq_str = f"{eq:.{dec}f}"
    if direction == "BUY":
        pd_ok = entry < eq
        if pd_ok:
            discount_pct = ((eq - entry) / max(r1 - s1, 0.0001)) * 100
            confirmations.append(f"✅ PREMIUM/DISCOUNT: Entry {entry:.{dec}f} di DISCOUNT zone ({discount_pct:.0f}% below EQ {eq_str}) ✔️ ICT aligned")
            score += 2
        else:
            premium_pct  = ((entry - eq) / max(r1 - s1, 0.0001)) * 100
            confirmations.append(f"⚠️ PREMIUM/DISCOUNT: Entry {entry:.{dec}f} di PREMIUM zone ({premium_pct:.0f}% above EQ {eq_str}) — BUY countertrend! Risiko tinggi")
    else:
        pd_ok = entry > eq
        if pd_ok:
            premium_pct  = ((entry - eq) / max(r1 - s1, 0.0001)) * 100
            confirmations.append(f"✅ PREMIUM/DISCOUNT: Entry {entry:.{dec}f} di PREMIUM zone ({premium_pct:.0f}% above EQ {eq_str}) ✔️ ICT aligned")
            score += 2
        else:
            discount_pct = ((eq - entry) / max(r1 - s1, 0.0001)) * 100
            confirmations.append(f"⚠️ PREMIUM/DISCOUNT: Entry {entry:.{dec}f} di DISCOUNT zone ({discount_pct:.0f}% below EQ {eq_str}) — SELL countertrend! Risiko tinggi")

    # ── 5. OB MITIGATION STATUS ───────────────────────────────
    # OB ter-mitigasi = harga sudah menembus OB sepenuhnya → OB invalid
    # BUY OB valid: price belum close di bawah S2 (OB belum ditembus penuh)
    # SELL OB valid: price belum close di atas R2
    if direction == "BUY":
        ob_valid = m15_close > s2 and m5_close > s2
        if ob_valid:
            confirmations.append(f"✅ OB STATUS: Bullish OB [{s1:.{dec}f}] belum ter-mitigasi (close {m15_close:.{dec}f} > S2 {s2:.{dec}f}) — OB masih valid")
            score += 1
        else:
            confirmations.append(f"⛔ OB STATUS: Harga close di bawah S2 {s2:.{dec}f} — Bullish OB sudah INVALID! Signal ditolak oleh OB check")
            score -= 2  # Penalty besar — OB invalid
    else:
        ob_valid = m15_close < r2 and m5_close < r2
        if ob_valid:
            confirmations.append(f"✅ OB STATUS: Bearish OB [{r1:.{dec}f}] belum ter-mitigasi (close {m15_close:.{dec}f} < R2 {r2:.{dec}f}) — OB masih valid")
            score += 1
        else:
            confirmations.append(f"⛔ OB STATUS: Harga close di atas R2 {r2:.{dec}f} — Bearish OB sudah INVALID! Signal ditolak oleh OB check")
            score -= 2

    # ── Entry Type Classification ─────────────────────────────
    score = max(score, 0)
    if score >= 8:
        entry_type = "KONFIRMASI PENUH 🔥🔥 — Semua ICT struktur aligned"
    elif score >= 5:
        entry_type = "KONFIRMASI PARSIAL ✅ — Setup valid, entry di OB zone"
    else:
        entry_type = "AGRESIF ⚠️ — Struktur lemah, hanya di Killzone aktif"

    return entry_type, confirmations, score


# ══════════════════════════════════════════════════════════════
# ICT SL/TP ENGINE — PROPER ORDER BLOCK BASED
# ══════════════════════════════════════════════════════════════

def calculate_ict_sltp(pair, direction, entry, atr, indicators):
    """
    ICT PROPER SL/TP — bukan asal ATR!

    ┌──────────────────────────────────────────────────────────────┐
    │ ORDER BLOCK (OB) untuk BUY:                                  │
    │   OB = Last significant bearish candle sebelum move bullish  │
    │   Di proxy dengan: Pivot S1 sebagai base OB                 │
    │   OB Low  = S1  (bawah OB)                                  │
    │   OB High = S1 + (ATR × ob_ratio)  (atas OB body)          │
    │                                                              │
    │   ENTRY AGRESIF    = OB High (top of OB)                    │
    │   ENTRY KONFIRMASI = OB Mid  (tengah OB)                    │
    │   SL = OB Low − (ATR × sl_buffer)  → BELOW OB, BUKAN DI   │
    │         DALAM OB! SL harus di luar struktur.                │
    │                                                              │
    │ ORDER BLOCK (OB) untuk SELL:                                 │
    │   OB = Last significant bullish candle sebelum move bearish  │
    │   OB High = R1                                               │
    │   OB Low  = R1 − (ATR × ob_ratio)                           │
    │                                                              │
    │   ENTRY AGRESIF    = OB Low (bottom of OB)                  │
    │   ENTRY KONFIRMASI = OB Mid                                  │
    │   SL = OB High + (ATR × sl_buffer)  → ABOVE OB             │
    └──────────────────────────────────────────────────────────────┘

    TP Targets (liquidity pools):
      TP1 = R1/S1 (nearest swing high/low = BSL/SSL)
      TP2 = R2/S2 (PDH/PDL area = major liquidity pool)
      RR minimum: 1.5:1 (reject kalau < 1.5)
      Ideal: TP1 ≥ 2:1, TP2 ≥ 3.5:1
    """
    cfg_sl = PAIR_SL_CONFIG.get(pair, (atr*0.5, atr*5, 0.35, 0.15))
    min_sl, max_sl, ob_ratio, sl_buf = cfg_sl
    dec = {"XAUUSD": 2, "GBPUSD": 5, "EURUSD": 5, "USDJPY": 3, "BTCUSDT": 2}.get(pair, 5)

    # ── Pivot Levels (proxy untuk swing structure) ────────────
    def get_piv(key, fallback):
        v = indicators.get(key) or indicators.get(key.replace('Classic', 'Fibonacci'))
        return v if v else fallback

    s1 = get_piv('Pivot.M.Classic.S1', entry - atr * 1.0)
    s2 = get_piv('Pivot.M.Classic.S2', entry - atr * 2.2)
    s3 = get_piv('Pivot.M.Classic.S3', entry - atr * 3.5)
    r1 = get_piv('Pivot.M.Classic.R1', entry + atr * 1.0)
    r2 = get_piv('Pivot.M.Classic.R2', entry + atr * 2.2)
    r3 = get_piv('Pivot.M.Classic.R3', entry + atr * 3.5)

    if direction == "BUY":
        # ── Bullish OB Zone ────────────────────────────────────
        ob_low   = s1
        ob_high  = s1 + (atr * ob_ratio)
        ob_mid   = (ob_low + ob_high) / 2

        entry_agg  = ob_high  # Agresif: top of OB
        entry_conf = ob_mid   # Konfirmasi: mid OB

        # SL HARUS di bawah OB Low — bukan di dalam OB!
        raw_sl      = ob_low - (atr * sl_buf)
        sl_distance = entry_agg - raw_sl  # Hitung dari agresif entry

        # Validate
        if sl_distance < min_sl:
            raw_sl = entry_agg - min_sl; sl_distance = min_sl
            sl_note = f"SL adjusted → min {min_sl}"
        elif sl_distance > max_sl:
            raw_sl = entry_agg - max_sl; sl_distance = max_sl
            sl_note = f"SL capped → max {max_sl}"
        else:
            sl_note = f"SL di bawah OB [{ob_low:.{dec}f}–{ob_high:.{dec}f}]"

        # ── TP: ke liquidity pool berikutnya ──────────────────
        # TP1: R1 kalau cukup jauh (≥ 1.5× SL dist), else RR 2.0
        if r1 > entry_agg and (r1 - entry_agg) >= sl_distance * 1.5:
            tp1 = r1; tp1_lbl = f"R1 BSL [{r1:.{dec}f}]"
        else:
            tp1 = entry_agg + sl_distance * 2.2; tp1_lbl = "RR 2.2x (ATR)"

        # TP2: R2 kalau cukup jauh (≥ 3× SL dist), else RR 4.0
        if r2 > entry_agg and (r2 - entry_agg) >= sl_distance * 3.0:
            tp2 = r2; tp2_lbl = f"R2 Liquidity [{r2:.{dec}f}]"
        else:
            tp2 = entry_agg + sl_distance * 4.0; tp2_lbl = "RR 4.0x (Extension)"

        rr1 = (tp1 - entry_agg) / max(sl_distance, 1e-9)
        rr2 = (tp2 - entry_agg) / max(sl_distance, 1e-9)

    else:  # SELL
        # ── Bearish OB Zone ────────────────────────────────────
        ob_high  = r1
        ob_low   = r1 - (atr * ob_ratio)
        ob_mid   = (ob_low + ob_high) / 2

        entry_agg  = ob_low   # Agresif: bottom of OB
        entry_conf = ob_mid   # Konfirmasi: mid OB

        raw_sl      = ob_high + (atr * sl_buf)
        sl_distance = raw_sl - entry_agg

        if sl_distance < min_sl:
            raw_sl = entry_agg + min_sl; sl_distance = min_sl
            sl_note = f"SL adjusted → min {min_sl}"
        elif sl_distance > max_sl:
            raw_sl = entry_agg + max_sl; sl_distance = max_sl
            sl_note = f"SL capped → max {max_sl}"
        else:
            sl_note = f"SL di atas OB [{ob_low:.{dec}f}–{ob_high:.{dec}f}]"

        if s1 < entry_agg and (entry_agg - s1) >= sl_distance * 1.5:
            tp1 = s1; tp1_lbl = f"S1 SSL [{s1:.{dec}f}]"
        else:
            tp1 = entry_agg - sl_distance * 2.2; tp1_lbl = "RR 2.2x (ATR)"

        if s2 < entry_agg and (entry_agg - s2) >= sl_distance * 3.0:
            tp2 = s2; tp2_lbl = f"S2 Liquidity [{s2:.{dec}f}]"
        else:
            tp2 = entry_agg - sl_distance * 4.0; tp2_lbl = "RR 4.0x (Extension)"

        rr1 = (entry_agg - tp1) / max(sl_distance, 1e-9)
        rr2 = (entry_agg - tp2) / max(sl_distance, 1e-9)

    # ── Reject filter ─────────────────────────────────────────
    if rr1 < 1.5:
        return None, None, None, None, None, None, None, None, \
               f"❌ DITOLAK — RR1 {rr1:.1f}:1 < 1.5 minimum (OB terlalu jauh dari pivot)"

    rr_emoji1 = "🔥🔥" if rr1 >= 3 else "🔥" if rr1 >= 2 else "✅"
    rr_emoji2 = "🔥🔥" if rr2 >= 4 else "🔥" if rr2 >= 3 else "✅"

    zone_info = (
        f"✅ {sl_note}\n"
        f"• TP1 → {tp1_lbl}  RR {rr1:.1f}:1 {rr_emoji1}\n"
        f"• TP2 → {tp2_lbl}  RR {rr2:.1f}:1 {rr_emoji2}"
    )

    ob_zone = {"low": ob_low, "high": ob_high, "mid": ob_mid,
               "entry_agg": entry_agg, "entry_conf": entry_conf}

    return raw_sl, tp1, tp2, sl_distance, rr1, rr2, ob_zone, zone_info, None


# ══════════════════════════════════════════════════════════════
# MESSAGE BUILDER (Telegram · Discord · Firebase)
# ══════════════════════════════════════════════════════════════

def build_messages(pair, cfg, direction, sl, tp1, tp2, rr1, rr2,
                   zone_info, ob_zone, session_info, htf_details,
                   cisd_type, cisd_list, smt_info, smt_bull, smt_bear):

    dec      = cfg['dec']
    now_str  = datetime.now(WIB).strftime('%d %b %Y  %H:%M WIB')
    d_emoji  = "🟢" if direction == "BUY" else "🔴"
    d_lbl    = "📈 BUY" if direction == "BUY" else "📉 SELL"

    ob_lo  = f"{ob_zone['low']:.{dec}f}"
    ob_hi  = f"{ob_zone['high']:.{dec}f}"
    ob_mid = f"{ob_zone['mid']:.{dec}f}"
    e_agg  = f"{ob_zone['entry_agg']:.{dec}f}"
    e_con  = f"{ob_zone['entry_conf']:.{dec}f}"
    sl_str = f"{sl:.{dec}f}"
    tp1str = f"{tp1:.{dec}f}"
    tp2str = f"{tp2:.{dec}f}"

    # HTF cascade string (max 4 lines)
    htf_str  = "\n".join(f"    {d}" for d in htf_details[:4])
    # CISD string (max 6 lines, alternating M15/M5)
    cisd_str = "\n".join(f"    {c}" for c in cisd_list[:6])
    # SMT (first 3 lines)
    smt_str  = "\n".join(f"    {l}" for l in smt_info.split('\n')[:3])

    silver_line = f"\n🥈 *{session_info['silver']}* — HIGHEST PROBABILITY!\n" if session_info['silver'] else ""
    macro_line  = f"⏰ *MACRO: {session_info['macro']}*\n" if session_info['macro'] else ""

    # AMDX phase label
    amdx = session_info['amdx']
    if amdx == "M":
        amdx_lbl = f"JUDAS SWING — {'LOW sweep sebelum NAIK' if direction=='BUY' else 'HIGH sweep sebelum TURUN'}"
    elif amdx == "X":
        amdx_lbl = f"EXPANSION — NY True Direction {'BULLISH' if direction=='BUY' else 'BEARISH'}"
    elif amdx == "A":
        amdx_lbl = "ACCUMULATION — Asia Range (setup early entry)"
    else:
        amdx_lbl = f"DISTRIBUTION — {session_info['phase']}"

    # SMT override warning
    smt_warn = ""
    if direction == "BUY" and smt_bear:
        smt_warn = "\n⚠️ *SMT CONFLICT: Bearish divergence vs BUY → Konfirmasi lebih ketat!*"
    elif direction == "SELL" and smt_bull:
        smt_warn = "\n⚠️ *SMT CONFLICT: Bullish divergence vs SELL → Konfirmasi lebih ketat!*"

    # ════════════════════════════════════════════════════════
    # TELEGRAM — Markdown detail lengkap
    # ════════════════════════════════════════════════════════
    tg = (
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🦅  *FREEDOM SYNDICATE*  |  *{pair}*  🦅\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{silver_line}"
        f"{macro_line}"
        f"{d_emoji} *{d_lbl}*  |  {cfg['ex']}  |  {now_str}\n\n"

        f"📍 *ORDER BLOCK ENTRY ZONE:*\n"
        f"   Zone:        `{ob_lo}` — `{ob_hi}`\n"
        f"   🎯 Agresif:  `{e_agg}` _(top/bottom OB)_\n"
        f"   ✅ Konfirm:  `{e_con}` _(mid OB, setelah CISD)_\n\n"

        f"🛑 *STOP LOSS:*  `{sl_str}`  _{('Below OB Low' if direction=='BUY' else 'Above OB High')}_\n"
        f"🎯 *TP1:*        `{tp1str}`  _RR {rr1:.1f}:1_\n"
        f"🚀 *TP2:*        `{tp2str}`  _RR {rr2:.1f}:1_\n"
        f"{smt_warn}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🧠 *ICT CONTEXT — {amdx_lbl}*\n"
        f"• Sesi:     {session_info['session']}\n"
        f"• {session_info['killzone']}\n"
        f"• Phase:    {session_info['phase']}\n\n"

        f"📊 *HTF CASCADE BIAS:*\n{htf_str}\n\n"

        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔬 *ICT PA CONFIRMATION — {cisd_type}:*\n"
        f"_[CISD · FVG · BSL/SSL Sweep · Premium/Discount · OB Status]_\n"
        f"{cisd_str}\n\n"

        f"🔀 *SMT DIVERGENCE:*\n{smt_str}\n\n"

        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📐 *SL/TP STRUCTURE:*\n{zone_info}\n\n"

        f"_⚠️ Entry di OB zone — bukan market price._\n"
        f"_Tunggu retest + CISD candle konfirmasi sebelum eksekusi._"
    )

    # ════════════════════════════════════════════════════════
    # DISCORD — Embed + compact text
    # ════════════════════════════════════════════════════════
    silver_disc = f"🥈 **{session_info['silver']}** — ULTRA HIGH PROB!\n" if session_info['silver'] else ""
    macro_disc  = f"⏰ **MACRO: {session_info['macro']}**\n" if session_info['macro'] else ""
    smt_warn_d  = ""
    if direction == "BUY" and smt_bear:
        smt_warn_d = "\n⚠️ **SMT CONFLICT: Bearish vs BUY → Size kecil!**"
    elif direction == "SELL" and smt_bull:
        smt_warn_d = "\n⚠️ **SMT CONFLICT: Bullish vs SELL → Size kecil!**"

    # First line of SMT for Discord (shorter)
    smt_d1 = smt_info.split('\n')[0].strip()

    disc_embed_desc = (
        f"{silver_disc}{macro_disc}"
        f"{d_emoji} **{d_lbl}**  |  {cfg['ex']}  |  {now_str}\n\n"

        f"📍 **OB ENTRY ZONE:** `{ob_lo}` – `{ob_hi}`\n"
        f"   Agresif: `{e_agg}`  |  Konfirm: `{e_con}`\n\n"

        f"🛑 **SL:** `{sl_str}`  ({'Below OB Low' if direction=='BUY' else 'Above OB High'})\n"
        f"🎯 **TP1:** `{tp1str}`  RR {rr1:.1f}:1\n"
        f"🚀 **TP2:** `{tp2str}`  RR {rr2:.1f}:1\n"
        f"{smt_warn_d}\n\n"

        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🧠 {amdx_lbl}\n"
        f"{session_info['killzone']}  |  {session_info['phase']}\n\n"

        f"✔️ **ICT PA:** {cisd_type}\n"
        f"🔀 {smt_d1}\n\n"

        f"📐 {zone_info.replace(chr(10), '  ')}\n\n"
        f"*⚠️ Entry di OB zone, bukan market price!*"
    )

    # Potong kalau > 4000 char
    if len(disc_embed_desc) > 4000:
        disc_embed_desc = disc_embed_desc[:3990] + "\n..."

    discord_payload = {
        "embeds": [{
            "title":       f"🦅 FREEDOM SYNDICATE  |  {pair}  |  {d_lbl}",
            "description": disc_embed_desc,
            "color":       0x00FF88 if direction == "BUY" else 0xFF3333,
            "footer":      {"text": f"Freedom Syndicate Supreme v3  •  {now_str}"}
        }]
    }

    # ════════════════════════════════════════════════════════
    # FIREBASE — JSON terstruktur (untuk website)
    # ════════════════════════════════════════════════════════
    fb_data = {
        "pair":            pair,
        "exchange":        cfg['ex'],
        "direction":       direction,
        "timestamp":       datetime.now(WIB).isoformat(),
        "timestamp_unix":  int(time.time()),
        "ob_zone": {
            "low":          round(ob_zone['low'],  dec),
            "high":         round(ob_zone['high'], dec),
            "mid":          round(ob_zone['mid'],  dec),
            "entry_agg":    round(ob_zone['entry_agg'],  dec),
            "entry_conf":   round(ob_zone['entry_conf'], dec),
        },
        "sl":              round(sl,  dec),
        "tp1":             round(tp1, dec),
        "tp2":             round(tp2, dec),
        "rr1":             round(rr1, 2),
        "rr2":             round(rr2, 2),
        "session":         session_info['session'],
        "killzone":        session_info['killzone'],
        "silver_bullet":   session_info['silver'] or "",
        "macro":           session_info['macro'] or "",
        "phase":           session_info['phase'],
        "amdx_phase":      amdx,
        "entry_type":      cisd_type,
        "smt_status":      smt_info.split('\n')[0],
        "smt_bullish":     smt_bull,
        "smt_bearish":     smt_bear,
        "htf_bias":        htf_details,
        "status":          "ACTIVE",
    }

    return tg, discord_payload, fb_data


# ══════════════════════════════════════════════════════════════
# SEND ENGINE (Telegram · Discord Embed · Firebase)
# ══════════════════════════════════════════════════════════════

def send_signal(tg_msg, discord_payload, fb_data):
    """Send signal ke semua platform"""

    # ── Telegram ─────────────────────────────────────────────
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN_TG_PREDATOR}/sendMessage",
            json={
                "chat_id":           CHAT_ID_TG,
                "message_thread_id": TOPIC_ID_GENERAL,
                "text":              tg_msg,
                "parse_mode":        "Markdown",
            },
            timeout=10,
        )
        print(f"{'✅' if r.ok else '⚠️'} Telegram signal: {r.status_code}")
        if not r.ok: print(f"   {r.text[:200]}")
    except Exception as e:
        print(f"❌ Telegram exception: {e}")

    # ── Discord (Embed) ───────────────────────────────────────
    try:
        r = requests.post(DISCORD_PREDATOR, json=discord_payload, timeout=10)
        print(f"{'✅' if r.ok else '⚠️'} Discord signal: {r.status_code}")
        if not r.ok: print(f"   {r.text[:200]}")
    except Exception as e:
        print(f"❌ Discord exception: {e}")

    # ── Firebase ──────────────────────────────────────────────
    try:
        r = requests.post(f"{FIREBASE_URL}/signals/ict.json", json=fb_data, timeout=10)
        print(f"{'✅' if r.ok else '⚠️'} Firebase signal: {r.status_code}")
    except Exception as e:
        print(f"❌ Firebase exception: {e}")


def send_news(msg, data=None):
    """Send fundamental news alert"""
    # Telegram
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN_TG_SUPREME}/sendMessage",
            json={"chat_id": CHAT_ID_TG, "message_thread_id": TOPIC_ID_GENERAL,
                  "text": msg, "parse_mode": "Markdown"},
            timeout=10,
        )
        print(f"{'✅' if r.ok else '⚠️'} Telegram news: {r.status_code}")
    except Exception as e:
        print(f"❌ Telegram news exception: {e}")

    # Discord
    impact_color = 0xFF0000 if "HIGH" in msg else 0xFFAA00 if "MED" in msg else 0x00CC44
    try:
        r = requests.post(
            DISCORD_FUNDA,
            json={"embeds": [{
                "title": "⚠️ FUNDAMENTAL ALERT",
                "description": msg,
                "color": impact_color,
                "footer": {"text": f"Freedom Syndicate  •  {datetime.now(WIB).strftime('%H:%M WIB')}"}
            }]},
            timeout=10,
        )
        print(f"{'✅' if r.ok else '⚠️'} Discord news: {r.status_code}")
    except Exception as e:
        print(f"❌ Discord news exception: {e}")

    # Firebase
    if data:
        try:
            requests.post(f"{FIREBASE_URL}/signals/fundamental.json", json=data, timeout=10)
        except Exception as e:
            print(f"❌ Firebase news exception: {e}")


# ══════════════════════════════════════════════════════════════
# MAIN RUNNER
# ══════════════════════════════════════════════════════════════

def run_freedom_engine():
    print(f"\n{'═'*62}")
    print(f"  🦅  {BOT_NAME}  —  SUPREME ENGINE v4.0")
    print(f"  PURE ICT | ZERO OSCILLATORS | Killzone-Only Signals")
    print(f"  Sessions (WIB): Asia 07-11 | London 13-16 | NY 20:30-22")
    print(f"  Silver Bullet:  London 14-15 | NY AM 21-22 | NY PM 01-02")
    print(f"{'═'*62}\n")

    while True:
        try:
            cycle_start = datetime.now(WIB)
            print(f"\n[{cycle_start.strftime('%H:%M:%S WIB')}] ──── NEW CYCLE ────")

            # ══════════════════════════════════════════════════
            # 1. FUNDAMENTAL RADAR
            # ══════════════════════════════════════════════════
            try:
                funda_url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
                events    = requests.get(funda_url, proxies=PROXIES,
                                         headers=get_headers(), timeout=15).json()
            except Exception as e:
                print(f"❌ Fundamental fetch: {e}")
                rotate_tor_ip(); events = []

            now_utc = datetime.now(UTC)
            for ev in events:
                try:
                    ev_dt = datetime.fromisoformat(ev['date']).astimezone(UTC)
                    ev_id = f"{ev.get('title','')}|{ev.get('date','')}|{ev.get('country','')}"
                    diff  = (ev_dt - now_utc).total_seconds()

                    # Kirim jika 1 jam ke depan & belum pernah dikirim
                    if 0 <= diff <= 3600 and ev_id not in sent_fundamentals:
                        impact = IMPACT_MAP.get(ev.get('impact', ''))
                        if impact:
                            news_msg = (
                                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                f"⚠️  *FUNDAMENTAL RADAR*  ⚠️\n"
                                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                f"📋 *{ev.get('title', 'N/A')}*\n"
                                f"🏛  Currency: `{ev.get('country', 'N/A')}`\n"
                                f"🔥 Impact: {impact}\n"
                                f"🕐 Time: `{ev_dt.astimezone(WIB).strftime('%H:%M WIB')}`\n"
                                f"_⚠️ Waspada — Hindari entry 30 menit sebelum & sesudah news!_"
                            )
                            send_news(news_msg, data=ev)
                            sent_fundamentals.add(ev_id)
                except Exception:
                    pass

            # Bersihkan tracker lama (> 2 jam)
            for ev in (events or []):
                try:
                    ev_dt = datetime.fromisoformat(ev['date']).astimezone(UTC)
                    ev_id = f"{ev.get('title','')}|{ev.get('date','')}|{ev.get('country','')}"
                    if (now_utc - ev_dt).total_seconds() > 7200:
                        sent_fundamentals.discard(ev_id)
                except Exception:
                    pass

            # ══════════════════════════════════════════════════
            # 2. SESSION CHECK
            # ══════════════════════════════════════════════════
            session_info = get_session_info()
            now_str      = datetime.now(WIB).strftime('%H:%M:%S WIB')
            print(f"  [{now_str}] {session_info['killzone']}")
            if session_info['macro']:
                print(f"  ⏰ {session_info['macro']}")
            print(f"  📅 AMDX: {session_info['phase']}")

            # ══════════════════════════════════════════════════
            # GATE: Hanya aktif saat Killzone atau Silver Bullet
            # Di luar window = tidur efisien, bukan polling spam
            # ══════════════════════════════════════════════════
            if not session_info['is_active']:
                wait_min = minutes_until_next_window()
                wake_at  = (datetime.now(WIB) + timedelta(minutes=wait_min)).strftime('%H:%M WIB')
                print(f"  💤 OFF-WINDOW — Tidur {wait_min} menit. Bangun ~{wake_at}")
                print(f"     (Bot HANYA scan saat Killzone / Silver Bullet)")
                time.sleep(wait_min * 60)
                continue

            # Silver Bullet → scan lebih sering (setiap 3 menit)
            # Killzone biasa → scan setiap 5 menit
            # Bukan silver = setiap 10 menit dalam killzone
            scan_interval = 180 if session_info['is_silver'] else 300

            # ══════════════════════════════════════════════════
            # 3. SIGNAL SCAN — per pair
            # ══════════════════════════════════════════════════
            for pair, cfg in PAIRS.items():
                print(f"\n  ── Scanning {pair} ──")
                try:
                    # Anti-spam: cooldown per pair
                    # Silver Bullet = 10 menit (window cuma 1 jam, jangan miss)
                    # Killzone biasa = 20 menit (window lebih lebar)
                    cooldown = 600 if session_info['is_silver'] else 1200
                    now_ts = time.time()
                    if pair in last_signal_time and (now_ts - last_signal_time[pair]) < cooldown:
                        remaining = int((cooldown - (now_ts - last_signal_time[pair])) / 60)
                        print(f"     ⏳ Cooldown {remaining}m — skip.")
                        continue

                    # ── HTF Cascade Bias ──────────────────────
                    print(f"     📊 HTF Bias scan...")
                    direction, confidence, htf_details = get_htf_bias(pair, cfg)
                    print(f"     → {direction}  confidence: {confidence}%")

                    if direction == "NEUTRAL":
                        print(f"     ⚖️ NEUTRAL bias — skip.")
                        continue
                    if confidence < 50:
                        print(f"     ⚠️ Confidence {confidence}% < 50% — skip.")
                        continue

                    # ── M5 untuk current price + ATR ─────────
                    a5 = safe_ta(pair, cfg['ex'], cfg['scr'], Interval.INTERVAL_5_MINUTES)
                    if not a5:
                        print(f"     ❌ M5 data error — skip.")
                        continue

                    entry = a5.indicators.get('close') or a5.indicators.get('Pivot.M.Classic.Middle')
                    atr   = a5.indicators.get('ATR') or a5.indicators.get('ATR14')
                    m5_rec = a5.summary.get('RECOMMENDATION', '')

                    if not entry:
                        print(f"     ❌ Entry price N/A — skip.")
                        continue
                    if not atr or atr == 0:
                        atr = entry * 0.001
                        print(f"     ⚠️ ATR fallback: {atr:.5f}")

                    print(f"     Price: {entry:.{cfg['dec']}f}  ATR: {atr:.{cfg['dec']}f}")

                    # ── SMT Divergence ────────────────────────
                    print(f"     🔀 SMT check vs {SMT_PAIRS.get(pair, {}).get('pair', 'N/A')}...")
                    smt_info, smt_bull, smt_bear = check_smt(pair, m5_rec, cfg)
                    print(f"     → {smt_info.split(chr(10))[0]}")

                    # ── Pure ICT PA Confirmation ─────────────
                    # CISD candle · FVG/Displacement · BSL/SSL Sweep · Premium/Discount
                    print(f"     🔬 ICT PA check (CISD·FVG·Sweep·P/D)...")
                    cisd_type, cisd_list, cisd_score = check_ict_pa(pair, cfg, direction, entry, atr)
                    print(f"     → {cisd_type}  (score: {cisd_score})")

                    # ── ICT SL/TP (OB-based) ──────────────────
                    result = calculate_ict_sltp(pair, direction, entry, atr, a5.indicators)
                    sl, tp1, tp2, sl_dist, rr1, rr2, ob_zone, zone_info, reject_reason = result

                    if sl is None:
                        print(f"     ⛔ {reject_reason}")
                        continue

                    print(f"     OB Zone: {ob_zone['low']:.{cfg['dec']}f} – {ob_zone['high']:.{cfg['dec']}f}")
                    print(f"     SL: {sl:.{cfg['dec']}f}  TP1: {tp1:.{cfg['dec']}f}  TP2: {tp2:.{cfg['dec']}f}")
                    print(f"     RR1: {rr1:.1f}:1  RR2: {rr2:.1f}:1")

                    # ── Build & Send ──────────────────────────
                    tg_msg, disc_payload, fb_data = build_messages(
                        pair, cfg, direction, sl, tp1, tp2, rr1, rr2,
                        zone_info, ob_zone, session_info, htf_details,
                        cisd_type, cisd_list, smt_info, smt_bull, smt_bear
                    )

                    send_signal(tg_msg, disc_payload, fb_data)
                    last_signal_time[pair] = now_ts
                    print(f"     ✅ Signal sent!")
                    time.sleep(30)   # Anti-spam antar pair

                except Exception as e:
                    print(f"     ❌ Error [{pair}]: {e}")
                    rotate_tor_ip()
                    time.sleep(10)

            # ── Cek apakah masih dalam window aktif ──────────
            si_end = get_session_info()
            if si_end['is_active']:
                label = "Silver Bullet" if si_end['is_silver'] else "Killzone"
                print(f"\n  [{datetime.now(WIB).strftime('%H:%M WIB')}] {label} masih aktif — scan lagi dalam {scan_interval//60} menit...")
                time.sleep(scan_interval)
            else:
                # Window baru saja tutup → tidur sampai window berikutnya
                wait_min = minutes_until_next_window()
                wake_at  = (datetime.now(WIB) + timedelta(minutes=wait_min)).strftime('%H:%M WIB')
                print(f"\n  [{datetime.now(WIB).strftime('%H:%M WIB')}] Window selesai. Tidur {wait_min} menit. Bangun ~{wake_at}")
                time.sleep(wait_min * 60)

        except Exception as e:
            print(f"❌ Main loop error: {e}")
            time.sleep(60)


if __name__ == "__main__":
    run_freedom_engine()
