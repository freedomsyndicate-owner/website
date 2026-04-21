"""
╔══════════════════════════════════════════════════════════════════════════════╗
║    DOMS FREEDOM SYNDICATE — MT5 ICT SCALPER v2.0                            ║
║    Enhanced: Compound Lot · Trailing Stop · Breakeven · M1 Scalping         ║
║    Strategi: ICT + EMA Ribbon + RSI Confluence + Multi-TF                   ║
╚══════════════════════════════════════════════════════════════════════════════╝

INSTALL:
    pip install MetaTrader5 numpy pandas requests

CARA PAKAI:
    1. Buka MT5, login ke akun kamu
    2. MT5 → Tools → Options → Expert Advisors → centang "Allow automated trading"
    3. Isi MT5_LOGIN, MT5_PASSWORD, MT5_SERVER di bawah
    4. Jalankan: python freedom_mt5_scalper_v2.py

⚠️  DISCLAIMER:
    Trading forex/gold mengandung risiko tinggi. Bot ini TIDAK menjamin profit.
    Gunakan dengan uang yang siap kamu rugikan. Selalu test di akun DEMO dulu!
"""

import MetaTrader5 as mt5
import numpy as np
import pandas as pd
import time
import requests
from datetime import datetime, timezone, timedelta

# ─── KONFIGURASI AKUN ──────────────────────────────────────────────────────────
MT5_LOGIN    = 15968176          # Ganti dengan login kamu
MT5_PASSWORD = "Winongo*03"      # Ganti dengan password kamu
MT5_SERVER   = "Headway-Real"    # Ganti dengan nama server broker kamu

WIB = timezone(timedelta(hours=7))

BOT_NAME    = "Freedom Syndicate Scalper v2.0"
MAGIC_NUMBER = 202604

# ─── TELEGRAM ──────────────────────────────────────────────────────────────────
TOKEN_TG   = "8196511062:AAGyfWcRUk9uw_lc_aQgUW6vLyyRmgF1hcE"
CHAT_ID_TG = "-1003660980986"
TOPIC_ID   = 18

# ─── KONFIGURASI PAIR ──────────────────────────────────────────────────────────
PAIRS_CONFIG = {
    "XAUUSD": {
        "dec":        2,
        "min_sl":     2.0,
        "max_sl":     20.0,    # Lebih ketat untuk scalping
        "spread_max": 35,
        "pip_value":  0.1,     # $ per 0.01 lot per pip (approx)
        "atr_mult_sl": 0.8,    # SL lebih ketat = reward lebih besar
        "atr_mult_tp": 2.0,    # TP minimum 2× SL
    },
}

# ─── RISK & MONEY MANAGEMENT ───────────────────────────────────────────────────
RISK_PER_TRADE_PCT   = 1.0    # % balance yang dirisiko per trade
MAX_OPEN_TRADES      = 1      # Maksimum 1 posisi sekaligus
MAX_DAILY_LOSS_PCT   = 4.0    # Stop trading jika rugi 4% hari ini
MAX_DRAWDOWN_PCT     = 8.0    # Stop total jika DD > 8%
MIN_LOT              = 0.01   # Lot minimum
MAX_LOT              = 1.0    # Lot maksimum (safety cap)

# ─── COMPOUND / GROWTH SETTINGS ────────────────────────────────────────────────
# Lot dihitung otomatis dari balance → modal kecil bisa berkembang
# Formula: lot = (balance × RISK_PCT) / (sl_pips × pip_value_per_lot)
# Makin besar balance, makin besar lot → compound effect

# ─── SCALPING SETTINGS ─────────────────────────────────────────────────────────
SCALP_TIMEFRAME   = mt5.TIMEFRAME_M1   # Entry di M1
CONFIRM_TIMEFRAME = mt5.TIMEFRAME_M5   # Konfirmasi di M5
HTF_TIMEFRAME     = mt5.TIMEFRAME_H4   # Bias dari H4

BREAKEVEN_AT_RR   = 1.0   # Pindahkan SL ke entry saat profit = 1×SL
TRAILING_TRIGGER  = 1.5   # Aktifkan trailing saat profit = 1.5×SL
TRAILING_STEP     = 0.5   # Trail tiap 0.5×ATR
PARTIAL_CLOSE_RR  = 1.2   # Tutup 50% posisi saat profit = 1.2×SL (fitur opsional)

# ─── STATE ─────────────────────────────────────────────────────────────────────
daily_start_balance  = None
session_traded_pairs = set()
trade_states         = {}   # {ticket: {entry, sl_orig, be_done, trail_dist}}

# ══════════════════════════════════════════════════════════════════════════════
# KONEKSI MT5
# ══════════════════════════════════════════════════════════════════════════════

def connect_mt5():
    if not mt5.initialize():
        print(f"❌ MT5 initialize gagal: {mt5.last_error()}")
        return False
    auth = mt5.login(MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER)
    if not auth:
        print(f"❌ Login gagal: {mt5.last_error()}")
        mt5.shutdown()
        return False
    info = mt5.account_info()
    print(f"✅ MT5 Connected!")
    print(f"   Akun    : {info.login} — {info.name}")
    print(f"   Balance : ${info.balance:.2f} | Equity: ${info.equity:.2f}")
    print(f"   Leverage: 1:{info.leverage}")
    return True

# ══════════════════════════════════════════════════════════════════════════════
# SESSION & ICT TIME
# ══════════════════════════════════════════════════════════════════════════════

def get_active_session():
    hr = datetime.now(WIB).hour
    # Sesi terbaik untuk scalping XAUUSD
    if 7 <= hr <= 10:   return "ASIA"
    if 14 <= hr <= 18:  return "LONDON"      # Diperluas sedikit
    if 20 <= hr <= 23:  return "NEWYORK"
    return "OFF"

def get_killzone_label():
    hr = datetime.now(WIB).hour
    if 7 <= hr <= 10:   return "ASIA KILLZONE 🌏"
    if 14 <= hr <= 18:  return "LONDON KILLZONE 🇬🇧"
    if 20 <= hr <= 23:  return "NEW YORK KILLZONE 🗽"
    return "OFF-SESSION 💤"

def get_macro_phase():
    """Deteksi ICT macro window & 90-menit cycle"""
    now       = datetime.now(WIB)
    total_min = now.hour * 60 + now.minute

    macros = [
        (7*60+50,  8*60+10,  "ASIA OPEN MACRO"),
        (9*60+50,  10*60+10, "ASIA CLOSE MACRO"),
        (14*60+50, 15*60+10, "LONDON OPEN MACRO"),
        (16*60+50, 17*60+10, "LONDON/NY PRE-MACRO"),
        (20*60+50, 21*60+10, "NEW YORK OPEN MACRO"),
        (22*60+50, 23*60+10, "NY LUNCH MACRO"),
    ]
    for start, end, label in macros:
        if start <= total_min <= end:
            return "MACRO_WINDOW", label

    cycle_starts = [7*60, 8*60+30, 10*60, 11*60+30,
                    14*60, 15*60+30, 17*60, 18*60+30,
                    20*60, 21*60+30, 23*60]
    for cs in cycle_starts:
        if cs <= total_min <= cs + 90:
            elapsed = total_min - cs
            if elapsed <= 20:   return "ACCUMULATION", f"Cycle {elapsed}m — Akumulasi"
            elif elapsed <= 60: return "MANIPULATION",  f"Cycle {elapsed}m — Judas Swing"
            else:               return "EXPANSION",     f"Cycle {elapsed}m — Expansion"

    return "OFF_MACRO", "Di luar macro window"

# ══════════════════════════════════════════════════════════════════════════════
# DATA & INDICATOR
# ══════════════════════════════════════════════════════════════════════════════

def get_ohlcv(symbol, timeframe=mt5.TIMEFRAME_M5, bars=150):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
    if rates is None or len(rates) == 0:
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

def get_atr(df, period=14):
    """ATR manual"""
    high  = df['high'].values
    low   = df['low'].values
    close = df['close'].values
    trs   = []
    for i in range(1, len(close)):
        trs.append(max(high[i] - low[i],
                       abs(high[i] - close[i-1]),
                       abs(low[i]  - close[i-1])))
    if len(trs) < period:
        return np.mean(trs) if trs else 1.0
    return np.mean(trs[-period:])

def get_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def get_rsi(series, period=14):
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, 0.001)
    return 100 - (100 / (1 + rs))

def detect_ema_ribbon(df):
    """
    EMA Ribbon: 8, 13, 21 pada M5/M1
    Bullish: EMA8 > EMA13 > EMA21 dan harga di atas semua
    Bearish: EMA8 < EMA13 < EMA21 dan harga di bawah semua
    """
    ema8  = get_ema(df['close'], 8).iloc[-1]
    ema13 = get_ema(df['close'], 13).iloc[-1]
    ema21 = get_ema(df['close'], 21).iloc[-1]
    price = df['close'].iloc[-1]

    if ema8 > ema13 > ema21 and price > ema8:
        return "BULLISH", f"EMA8>{ema8:.2f} >EMA13>{ema13:.2f} >EMA21{ema21:.2f}"
    elif ema8 < ema13 < ema21 and price < ema8:
        return "BEARISH", f"EMA8<{ema8:.2f} <EMA13<{ema13:.2f} <EMA21{ema21:.2f}"
    return "NEUTRAL", "EMA ribbon tidak jelas"

def detect_rsi_confluence(df, direction):
    """
    RSI confluence untuk scalping:
    BUY: RSI di 35-55 dan naik (momentum beli)
    SELL: RSI di 45-65 dan turun (momentum jual)
    Hindari overbought/oversold untuk scalp
    """
    rsi = get_rsi(df['close'], 14).iloc[-3:]
    rsi_now  = rsi.iloc[-1]
    rsi_prev = rsi.iloc[-2]

    if direction == "BUY":
        if 30 <= rsi_now <= 60 and rsi_now > rsi_prev:
            return True, f"RSI {rsi_now:.1f} ↑ (momentum beli)"
        return False, f"RSI {rsi_now:.1f} (tidak kondusif untuk BUY scalp)"
    else:
        if 40 <= rsi_now <= 70 and rsi_now < rsi_prev:
            return True, f"RSI {rsi_now:.1f} ↓ (momentum jual)"
        return False, f"RSI {rsi_now:.1f} (tidak kondusif untuk SELL scalp)"

def find_swing_points(df, lookback=3):
    highs  = df['high'].values
    lows   = df['low'].values
    n      = len(highs)
    sh_list = []
    sl_list = []
    for i in range(lookback, n - lookback):
        if highs[i] == max(highs[i-lookback:i+lookback+1]):
            sh_list.append((i, highs[i]))
        if lows[i] == min(lows[i-lookback:i+lookback+1]):
            sl_list.append((i, lows[i]))
    return sh_list, sl_list

def detect_fvg(df):
    """Fair Value Gap / Imbalance"""
    fvg_list = []
    for i in range(1, len(df) - 1):
        if df['low'].iloc[i+1] > df['high'].iloc[i-1]:
            fvg_list.append({
                'type': 'BULLISH',
                'top':  df['low'].iloc[i+1],
                'bot':  df['high'].iloc[i-1],
                'mid':  (df['low'].iloc[i+1] + df['high'].iloc[i-1]) / 2,
                'idx':  i
            })
        elif df['high'].iloc[i+1] < df['low'].iloc[i-1]:
            fvg_list.append({
                'type': 'BEARISH',
                'top':  df['low'].iloc[i-1],
                'bot':  df['high'].iloc[i+1],
                'mid':  (df['low'].iloc[i-1] + df['high'].iloc[i+1]) / 2,
                'idx':  i
            })
    return fvg_list

def detect_orderblock(df, direction):
    """Order Block ICT"""
    obs = []
    for i in range(2, len(df) - 2):
        body_size = abs(df['close'].iloc[i] - df['open'].iloc[i])
        next_move = abs(df['close'].iloc[i+2] - df['close'].iloc[i])
        if direction == "BUY":
            if (df['close'].iloc[i] < df['open'].iloc[i] and
                df['close'].iloc[i+1] > df['open'].iloc[i+1] and
                next_move > body_size * 1.5):
                obs.append({
                    'type': 'BULLISH_OB',
                    'top':  df['open'].iloc[i],
                    'bot':  df['low'].iloc[i],
                    'mid':  (df['open'].iloc[i] + df['low'].iloc[i]) / 2,
                    'idx':  i
                })
        else:
            if (df['close'].iloc[i] > df['open'].iloc[i] and
                df['close'].iloc[i+1] < df['open'].iloc[i+1] and
                next_move > body_size * 1.5):
                obs.append({
                    'type': 'BEARISH_OB',
                    'top':  df['high'].iloc[i],
                    'bot':  df['open'].iloc[i],
                    'mid':  (df['high'].iloc[i] + df['open'].iloc[i]) / 2,
                    'idx':  i
                })
    return obs

def detect_market_structure(df):
    """MSB / ChoCH detection di M15"""
    swing_highs, swing_lows = find_swing_points(df, lookback=3)
    current_close = df['close'].iloc[-1]
    current_open  = df['open'].iloc[-1]
    msb = "NONE"

    if len(swing_highs) >= 2:
        prev_sh = swing_highs[-2][1]
        last_sh = swing_highs[-1][1]
        if current_close > prev_sh and last_sh > prev_sh:
            candle_body = abs(current_close - current_open)
            if candle_body > df['high'].iloc[-1] * 0.0003:
                msb = "BULLISH_MSB"

    if len(swing_lows) >= 2:
        prev_sl = swing_lows[-2][1]
        last_sl = swing_lows[-1][1]
        if current_close < prev_sl and last_sl < prev_sl:
            candle_body = abs(current_close - current_open)
            if candle_body > df['low'].iloc[-1] * 0.0003:
                msb = "BEARISH_MSB"

    return msb

def get_daily_bias_from_htf(symbol):
    """Daily bias dari H4 — EMA20 + struktur HH/HL/LH/LL"""
    df_h4 = get_ohlcv(symbol, timeframe=HTF_TIMEFRAME, bars=60)
    if df_h4 is None or len(df_h4) < 25:
        return "NEUTRAL", "HTF data tidak cukup"

    ema20 = get_ema(df_h4['close'], 20).iloc[-1]
    ema50 = get_ema(df_h4['close'], 50).iloc[-1]
    close = df_h4['close'].iloc[-1]

    swing_h, swing_l = find_swing_points(df_h4, lookback=3)
    if len(swing_h) >= 2 and len(swing_l) >= 2:
        hh = swing_h[-1][1] > swing_h[-2][1]
        hl = swing_l[-1][1] > swing_l[-2][1]
        lh = swing_h[-1][1] < swing_h[-2][1]
        ll = swing_l[-1][1] < swing_l[-2][1]

        if hh and hl and close > ema20 and ema20 > ema50:
            return "BULLISH", f"H4 HH+HL | EMA20={ema20:.2f} > EMA50={ema50:.2f}"
        elif lh and ll and close < ema20 and ema20 < ema50:
            return "BEARISH", f"H4 LH+LL | EMA20={ema20:.2f} < EMA50={ema50:.2f}"
        elif close > ema20:
            return "BULLISH", f"H4 above EMA20={ema20:.2f}"
        elif close < ema20:
            return "BEARISH", f"H4 below EMA20={ema20:.2f}"

    return "NEUTRAL", "Struktur H4 tidak jelas"

# ══════════════════════════════════════════════════════════════════════════════
# DYNAMIC LOT SIZING — COMPOUND GROWTH
# ══════════════════════════════════════════════════════════════════════════════

def calculate_dynamic_lot(symbol, sl_distance_price):
    """
    Compound lot sizing:
    Lot = (Balance × Risk%) / (SL_price × ContractSize)
    Makin besar balance → lot naik otomatis
    """
    account  = mt5.account_info()
    sym_info = mt5.symbol_info(symbol)
    if not account or not sym_info:
        return MIN_LOT

    balance      = account.balance
    risk_amount  = balance * (RISK_PER_TRADE_PCT / 100.0)

    # Untuk XAUUSD: contract size = 100 oz, SL dalam USD
    contract_size = sym_info.trade_contract_size  # biasanya 100 untuk Gold
    sl_usd_per_lot = sl_distance_price * contract_size

    if sl_usd_per_lot <= 0:
        return MIN_LOT

    lot = risk_amount / sl_usd_per_lot
    lot = round(lot, 2)
    lot = max(MIN_LOT, min(lot, MAX_LOT))

    # Snap ke volume_step broker
    step = sym_info.volume_step if sym_info.volume_step > 0 else 0.01
    lot  = round(lot / step) * step
    lot  = max(sym_info.volume_min, min(lot, sym_info.volume_max))

    print(f"  💰 Compound Lot: ${balance:.2f} × {RISK_PER_TRADE_PCT}% / ${sl_usd_per_lot:.2f} = {lot:.2f} lot")
    return lot

# ══════════════════════════════════════════════════════════════════════════════
# ANALISA ICT MULTI-TF + EMA RIBBON + RSI (SCALPING FOCUSED)
# ══════════════════════════════════════════════════════════════════════════════

def analyze_pair_scalp(symbol):
    """
    Full confluence untuk scalping:
    1. Sesi & Macro ICT
    2. Daily Bias H4 (EMA20+50 + struktur)
    3. MSB + EMA Ribbon M5 (konfirmasi)
    4. RSI M5 momentum filter
    5. FVG / OB entry zone M5 (atau M1 untuk scalp presisi)
    6. SL/TP ATR-based | RR min 1.8:1
    """
    cfg = PAIRS_CONFIG.get(symbol)
    if not cfg:
        return None

    # ── 1. Sesi & Macro ──────────────────────────────────────────────────────
    session = get_active_session()
    if session == "OFF":
        return None

    macro_phase, macro_label = get_macro_phase()
    if macro_phase == "MANIPULATION":
        print(f"  ⏳ {symbol}: Skip — MANIPULATION (Judas Swing)")
        return None

    # ── 2. Daily Bias H4 ─────────────────────────────────────────────────────
    daily_bias, bias_detail = get_daily_bias_from_htf(symbol)
    if daily_bias == "NEUTRAL":
        print(f"  ⚖️  {symbol}: Skip — Bias NEUTRAL")
        return None

    direction = "BUY" if daily_bias == "BULLISH" else "SELL"

    # ── 3. MSB M15 ────────────────────────────────────────────────────────────
    df_m15 = get_ohlcv(symbol, timeframe=mt5.TIMEFRAME_M15, bars=80)
    if df_m15 is None:
        return None
    msb = detect_market_structure(df_m15)
    if daily_bias == "BULLISH" and msb != "BULLISH_MSB":
        print(f"  🔍 {symbol}: Bias BULLISH, belum ada MSB bullish di M15")
        return None
    if daily_bias == "BEARISH" and msb != "BEARISH_MSB":
        print(f"  🔍 {symbol}: Bias BEARISH, belum ada MSB bearish di M15")
        return None

    # ── 4. EMA Ribbon M5 ─────────────────────────────────────────────────────
    df_m5 = get_ohlcv(symbol, timeframe=mt5.TIMEFRAME_M5, bars=100)
    if df_m5 is None:
        return None

    ribbon_dir, ribbon_detail = detect_ema_ribbon(df_m5)
    if ribbon_dir != daily_bias:
        print(f"  📊 {symbol}: EMA Ribbon M5 = {ribbon_dir}, beda dari bias {daily_bias}. Skip.")
        return None

    # ── 5. RSI M5 Momentum ───────────────────────────────────────────────────
    rsi_ok, rsi_detail = detect_rsi_confluence(df_m5, direction)
    if not rsi_ok:
        print(f"  📉 {symbol}: RSI tidak kondusif — {rsi_detail}")
        return None

    # ── 6. Entry Zone: FVG / OB ──────────────────────────────────────────────
    atr_m5   = get_atr(df_m5, 14)
    fvg_list = detect_fvg(df_m5)
    ob_list  = detect_orderblock(df_m5, direction)
    current_price = df_m5['close'].iloc[-1]
    dec = cfg['dec']

    entry_zone = None
    entry_type = ""
    fvg_target = "BULLISH" if direction == "BUY" else "BEARISH"

    # FVG — filter yang masih belum terisi & dekat harga
    valid_fvgs = []
    for fvg in reversed(fvg_list[-30:]):
        if fvg['type'] == fvg_target:
            dist = abs(current_price - fvg['mid'])
            if direction == "BUY" and current_price > fvg['top'] and dist < atr_m5 * 3:
                valid_fvgs.append((dist, fvg))
            elif direction == "SELL" and current_price < fvg['bot'] and dist < atr_m5 * 3:
                valid_fvgs.append((dist, fvg))

    if valid_fvgs:
        valid_fvgs.sort(key=lambda x: x[0])  # Ambil yang terdekat
        nearest_fvg = valid_fvgs[0][1]
        entry_zone  = nearest_fvg['mid']
        entry_type  = f"FVG {fvg_target} [{nearest_fvg['bot']:.{dec}f}–{nearest_fvg['top']:.{dec}f}]"

    # OB fallback jika tidak ada FVG
    if not entry_zone and ob_list:
        ob_target  = "BULLISH_OB" if direction == "BUY" else "BEARISH_OB"
        valid_obs  = []
        for ob in reversed(ob_list[-30:]):
            if ob['type'] == ob_target:
                dist = abs(current_price - ob['mid'])
                if dist < atr_m5 * 3:
                    valid_obs.append((dist, ob))
        if valid_obs:
            valid_obs.sort(key=lambda x: x[0])
            nearest_ob = valid_obs[0][1]
            entry_zone = nearest_ob['mid']
            entry_type = f"OB {ob_target} [{nearest_ob['bot']:.{dec}f}–{nearest_ob['top']:.{dec}f}]"

    # Fallback: entry di harga saat ini jika di dalam zona (tight entry)
    if not entry_zone:
        entry_zone = current_price
        entry_type = "Market Entry (No FVG/OB)"

    # ── 7. SL / TP ATR-Based ─────────────────────────────────────────────────
    swing_highs, swing_lows = find_swing_points(df_m5, lookback=4)
    sl_mult = cfg['atr_mult_sl']
    tp_mult = cfg['atr_mult_tp']
    min_sl  = cfg['min_sl']
    max_sl  = cfg['max_sl']

    if direction == "BUY":
        if swing_lows:
            recent_sl_levels = sorted([sl[1] for sl in swing_lows[-5:]])
            raw_sl = recent_sl_levels[0] - (atr_m5 * sl_mult * 0.3)
        else:
            raw_sl = entry_zone - (atr_m5 * sl_mult)
        sl_dist = max(min_sl, min(entry_zone - raw_sl, max_sl))
        sl = entry_zone - sl_dist

        # TP ke liquidity pool (swing high)
        tp_min = entry_zone + (sl_dist * tp_mult)
        if swing_highs:
            tp_liq = max([sh[1] for sh in swing_highs[-5:]])
            tp = tp_liq if tp_liq > tp_min else entry_zone + (sl_dist * 2.5)
        else:
            tp = entry_zone + (sl_dist * 2.5)

    else:  # SELL
        if swing_highs:
            recen