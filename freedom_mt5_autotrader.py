"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          DOMS FREEDOM SYNDICATE — MT5 ICT AUTO TRADER                       ║
║          Michael J. Huddleston Logic | Connect MT5 Laptop                   ║
║          Account: 15968176 | Broker: Headway-Real                           ║
╚══════════════════════════════════════════════════════════════════════════════╝

INSTALL DULU:
    pip install MetaTrader5 numpy pandas requests

CARA PAKAI:
    1. Buka MT5 di laptop, login ke akun 15968176
    2. MT5 → Tools → Options → Expert Advisors → centang "Allow automated trading"
    3. Jalankan: python freedom_mt5_autotrader.py
"""

import MetaTrader5 as mt5
import numpy as np
import pandas as pd
import time
import requests
import random
from datetime import datetime, timezone, timedelta

# ─── KONFIGURASI ───────────────────────────────────────────────────────────────
MT5_LOGIN    = 15968176
MT5_PASSWORD = "Winongo*03"
MT5_SERVER   = "Headway-Real"

WIB = timezone(timedelta(hours=7))
UTC = timezone.utc

BOT_NAME = "Doms Freedom Syndicate MT5"

# Telegram notifikasi (pakai token dari engine utama)
TOKEN_TG   = "8196511062:AAGyfWcRUk9uw_lc_aQgUW6vLyyRmgF1hcE"
CHAT_ID_TG = "-1003660980986"
TOPIC_ID   = 18

# ─── PAIRS TRADING ─────────────────────────────────────────────────────────────
# Sesuaikan dengan yang tersedia di broker Headway
PAIRS_CONFIG = {
    "XAUUSD": {"lot": 0.01, "dec": 2, "min_sl": 2.0,   "max_sl": 20.0,  "spread_max": 30},
    "GBPUSD": {"lot": 0.01, "dec": 5, "min_sl": 0.0010, "max_sl": 0.006, "spread_max": 20},
    "EURUSD": {"lot": 0.01, "dec": 5, "min_sl": 0.0010, "max_sl": 0.006, "spread_max": 15},
    "USDJPY": {"lot": 0.01, "dec": 3, "min_sl": 0.10,   "max_sl": 0.60,  "spread_max": 20},
    "BTCUSD": {"lot": 0.01, "dec": 2, "min_sl": 150.0,  "max_sl": 1500.0,"spread_max": 500},
}

# ─── RISK MANAGEMENT ───────────────────────────────────────────────────────────
RISK_PER_TRADE_PCT   = 1.0   # Max 1% balance per trade
MAX_OPEN_TRADES      = 3     # Max posisi terbuka sekaligus
MAX_DAILY_LOSS_PCT   = 5.0   # Bot berhenti jika rugi 5% balance hari ini
MAX_DRAWDOWN_PCT     = 10.0  # Bot berhenti total jika DD > 10%
MAGIC_NUMBER         = 202604  # ID unik bot ini di MT5

# ─── STATE ─────────────────────────────────────────────────────────────────────
daily_start_balance  = None
session_traded_pairs = set()   # Pair yang sudah entry di sesi ini
last_candle_time     = {}      # Untuk deteksi candle baru

# ══════════════════════════════════════════════════════════════════════════════
# MT5 CONNECTION
# ══════════════════════════════════════════════════════════════════════════════

def connect_mt5():
    """Connect ke MT5 di laptop"""
    if not mt5.initialize():
        print(f"❌ MT5 initialize gagal: {mt5.last_error()}")
        return False

    auth = mt5.login(MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER)
    if not auth:
        print(f"❌ MT5 login gagal: {mt5.last_error()}")
        mt5.shutdown()
        return False

    info = mt5.account_info()
    print(f"✅ MT5 Connected!")
    print(f"   Akun    : {info.login} — {info.name}")
    print(f"   Server  : {info.server}")
    print(f"   Balance : ${info.balance:.2f}")
    print(f"   Equity  : ${info.equity:.2f}")
    return True

# ══════════════════════════════════════════════════════════════════════════════
# SESSION & ICT TIME LOGIC
# ══════════════════════════════════════════════════════════════════════════════

def get_active_session():
    hr = datetime.now(WIB).hour
    if 7 <= hr <= 10:   return "ASIA"
    if 14 <= hr <= 17:  return "LONDON"
    if 20 <= hr <= 23:  return "NEWYORK"
    return "OFF"

def get_killzone_label():
    hr = datetime.now(WIB).hour
    if 7 <= hr <= 10:   return "ASIA KILLZONE"
    if 14 <= hr <= 17:  return "LONDON KILLZONE"
    if 20 <= hr <= 23:  return "NEW YORK KILLZONE"
    return "OFF-SESSION"

def get_macro_phase():
    """Deteksi phase dalam 90 menit cycle ICT"""
    now = datetime.now(WIB)
    total_min = now.hour * 60 + now.minute

    # Macro windows (20 menit) — momen pasar cari likuiditas sebelum move
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

    # 90-menit micro cycle
    cycle_starts = [7*60, 8*60+30, 10*60, 11*60+30, 14*60, 15*60+30,
                    17*60, 18*60+30, 20*60, 21*60+30, 23*60]
    for cs in cycle_starts:
        if cs <= total_min <= cs + 90:
            elapsed = total_min - cs
            if elapsed <= 20:   return "ACCUMULATION", f"Cycle {elapsed}m - Akumulasi"
            elif elapsed <= 60: return "MANIPULATION",  f"Cycle {elapsed}m - Judas Swing"
            else:               return "EXPANSION",     f"Cycle {elapsed}m - Expansion"

    return "OFF_MACRO", "Di luar macro window"

# ══════════════════════════════════════════════════════════════════════════════
# ICT MARKET STRUCTURE ANALYSIS (dari candle MT5)
# ══════════════════════════════════════════════════════════════════════════════

def get_ohlcv(symbol, timeframe=mt5.TIMEFRAME_M5, bars=100):
    """Ambil data OHLCV dari MT5"""
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
    if rates is None or len(rates) == 0:
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

def find_swing_points(df, lookback=5):
    """
    Cari Swing High & Swing Low dari candle MT5.
    Swing High: candle high tertinggi dalam window lookback
    Swing Low:  candle low terendah dalam window lookback
    ICT: ini adalah level di mana liquidity pool berada
    """
    highs = df['high'].values
    lows  = df['low'].values
    n = len(highs)

    swing_highs = []
    swing_lows  = []

    for i in range(lookback, n - lookback):
        # Swing High: high[i] lebih tinggi dari semua high di sekitarnya
        if highs[i] == max(highs[i-lookback:i+lookback+1]):
            swing_highs.append((i, highs[i]))
        # Swing Low: low[i] lebih rendah dari semua low di sekitarnya
        if lows[i] == min(lows[i-lookback:i+lookback+1]):
            swing_lows.append((i, lows[i]))

    return swing_highs, swing_lows

def detect_fvg(df):
    """
    Deteksi Fair Value Gap (FVG) / Imbalance
    FVG Bullish: Low[i+1] > High[i-1] — ada gap naik tidak terisi
    FVG Bearish: High[i+1] < Low[i-1] — ada gap turun tidak terisi
    ICT: FVG adalah magnet harga & zona entry optimal
    """
    fvg_list = []
    for i in range(1, len(df) - 1):
        # Bullish FVG
        if df['low'].iloc[i+1] > df['high'].iloc[i-1]:
            fvg_list.append({
                'type': 'BULLISH',
                'top':  df['low'].iloc[i+1],
                'bot':  df['high'].iloc[i-1],
                'mid':  (df['low'].iloc[i+1] + df['high'].iloc[i-1]) / 2,
                'idx':  i
            })
        # Bearish FVG
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
    """
    Deteksi Order Block (OB)
    Bullish OB: Candle bearish terakhir sebelum impulse naik kuat
    Bearish OB: Candle bullish terakhir sebelum impulse turun kuat
    ICT: OB = zona di mana institusi memasang order besar
    """
    obs = []
    for i in range(2, len(df) - 2):
        body_size = abs(df['close'].iloc[i] - df['open'].iloc[i])
        next_move = abs(df['close'].iloc[i+2] - df['close'].iloc[i])

        if direction == "BUY":
            # Bullish OB: candle merah diikuti impulse naik 2x body
            if (df['close'].iloc[i] < df['open'].iloc[i] and
                df['close'].iloc[i+1] > df['open'].iloc[i+1] and
                next_move > body_size * 1.5):
                obs.append({
                    'type': 'BULLISH_OB',
                    'top':  df['open'].iloc[i],   # Top of bearish candle
                    'bot':  df['low'].iloc[i],
                    'mid':  (df['open'].iloc[i] + df['low'].iloc[i]) / 2,
                    'idx':  i
                })
        else:
            # Bearish OB: candle hijau diikuti impulse turun 2x body
            if (df['close'].iloc[i] > df['open'].iloc[i] and
                df['close'].iloc[i+1] < df['open'].iloc[i+1] and
                next_move > body_size * 1.5):
                obs.append({
                    'type': 'BEARISH_OB',
                    'top':  df['high'].iloc[i],
                    'bot':  df['open'].iloc[i],   # Bot of bullish candle
                    'mid':  (df['high'].iloc[i] + df['open'].iloc[i]) / 2,
                    'idx':  i
                })
    return obs

def detect_market_structure(df):
    """
    Deteksi Market Structure Break (MSB) / Change of Character (ChoCH)
    MSB Bullish: Break above previous Swing High dengan displacement candle
    MSB Bearish: Break below previous Swing Low dengan displacement candle
    ICT: MSB = konfirmasi direction, ChoCH = peringatan reversal
    """
    swing_highs, swing_lows = find_swing_points(df, lookback=3)
    current_close = df['close'].iloc[-1]
    current_open  = df['open'].iloc[-1]

    msb = "NONE"
    choch = "NONE"

    if len(swing_highs) >= 2:
        prev_sh = swing_highs[-2][1]  # Swing High sebelumnya
        last_sh = swing_highs[-1][1]
        if current_close > prev_sh and last_sh > prev_sh:
            # Break above previous high = MSB Bullish
            candle_body = abs(current_close - current_open)
            if candle_body > df['high'].iloc[-1] * 0.0005:  # Displacement filter
                msb = "BULLISH_MSB"

    if len(swing_lows) >= 2:
        prev_sl = swing_lows[-2][1]
        last_sl = swing_lows[-1][1]
        if current_close < prev_sl and last_sl < prev_sl:
            candle_body = abs(current_close - current_open)
            if candle_body > df['low'].iloc[-1] * 0.0005:
                msb = "BEARISH_MSB"

    return msb

def get_atr(df, period=14):
    """Hitung ATR manual dari data MT5"""
    high = df['high'].values
    low  = df['low'].values
    close = df['close'].values
    tr_list = []
    for i in range(1, len(close)):
        tr = max(high[i] - low[i],
                 abs(high[i] - close[i-1]),
                 abs(low[i] - close[i-1]))
        tr_list.append(tr)
    if len(tr_list) < period:
        return np.mean(tr_list) if tr_list else 0
    return np.mean(tr_list[-period:])

def get_daily_bias_from_htf(symbol):
    """
    Daily Bias dari HTF (H4 / Daily)
    Bullish: Close H4 terakhir > EMA 20 H4
    Bearish: Close H4 terakhir < EMA 20 H4
    """
    df_h4 = get_ohlcv(symbol, timeframe=mt5.TIMEFRAME_H4, bars=50)
    if df_h4 is None or len(df_h4) < 21:
        return "NEUTRAL", "HTF data tidak cukup"

    ema20 = df_h4['close'].ewm(span=20, adjust=False).mean().iloc[-1]
    close = df_h4['close'].iloc[-1]

    # Cek Higher High / Higher Low atau Lower High / Lower Low
    swing_h, swing_l = find_swing_points(df_h4, lookback=3)
    if len(swing_h) >= 2 and len(swing_l) >= 2:
        hh = swing_h[-1][1] > swing_h[-2][1]  # Higher High
        hl = swing_l[-1][1] > swing_l[-2][1]  # Higher Low
        lh = swing_h[-1][1] < swing_h[-2][1]  # Lower High
        ll = swing_l[-1][1] < swing_l[-2][1]  # Lower Low

        if hh and hl and close > ema20:
            return "BULLISH", f"H4: HH+HL+above EMA20 ({ema20:.5f})"
        elif lh and ll and close < ema20:
            return "BEARISH", f"H4: LH+LL+below EMA20 ({ema20:.5f})"
        elif close > ema20:
            return "BULLISH", f"H4: above EMA20 ({ema20:.5f})"
        elif close < ema20:
            return "BEARISH", f"H4: below EMA20 ({ema20:.5f})"

    return "NEUTRAL", "Struktur H4 tidak jelas"

# ══════════════════════════════════════════════════════════════════════════════
# ICT ENTRY LOGIC — FULL CONFLUENCE
# ══════════════════════════════════════════════════════════════════════════════

def analyze_pair_ict(symbol):
    """
    Full ICT analysis untuk 1 pair:
    1. Cek sesi aktif & macro phase
    2. Daily Bias dari H4
    3. Market Structure Break di M15
    4. FVG + OB entry zone di M5
    5. RR filter minimum 1:2
    Return: dict signal atau None jika tidak ada setup
    """
    cfg = PAIRS_CONFIG.get(symbol)
    if not cfg:
        return None

    # ── 1. Sesi & Macro ──────────────────────────────────────────────────────
    session = get_active_session()
    if session == "OFF":
        return None  # Tidak trading di luar sesi

    macro_phase, macro_label = get_macro_phase()

    # Hanya entry saat MACRO_WINDOW atau EXPANSION phase
    # Hindari entry saat MANIPULATION (Judas Swing sedang berjalan)
    if macro_phase == "MANIPULATION":
        print(f"  ⏳ {symbol}: Skip — MANIPULATION phase (Judas Swing)")
        return None

    # ── 2. Daily Bias HTF ────────────────────────────────────────────────────
    daily_bias, bias_detail = get_daily_bias_from_htf(symbol)
    if daily_bias == "NEUTRAL":
        print(f"  ⚖️  {symbol}: Skip — Daily bias NEUTRAL")
        return None

    # ── 3. MSB di M15 ────────────────────────────────────────────────────────
    df_m15 = get_ohlcv(symbol, timeframe=mt5.TIMEFRAME_M15, bars=60)
    if df_m15 is None:
        return None

    msb = detect_market_structure(df_m15)
    atr_m15 = get_atr(df_m15)

    # MSB harus searah Daily Bias
    if daily_bias == "BULLISH" and msb != "BULLISH_MSB":
        print(f"  🔍 {symbol}: Bias BULLISH tapi belum ada Bullish MSB di M15")
        return None
    if daily_bias == "BEARISH" and msb != "BEARISH_MSB":
        print(f"  🔍 {symbol}: Bias BEARISH tapi belum ada Bearish MSB di M15")
        return None

    direction = "BUY" if daily_bias == "BULLISH" else "SELL"

    # ── 4. FVG & OB Entry Zone di M5 ─────────────────────────────────────────
    df_m5 = get_ohlcv(symbol, timeframe=mt5.TIMEFRAME_M5, bars=80)
    if df_m5 is None:
        return None

    atr_m5   = get_atr(df_m5)
    fvg_list = detect_fvg(df_m5)
    ob_list  = detect_orderblock(df_m5, direction)
    current_price = df_m5['close'].iloc[-1]

    # Cari FVG terdekat searah bias
    entry_zone = None
    entry_type = ""
    fvg_type_target = "BULLISH" if direction == "BUY" else "BEARISH"

    # Filter FVG yang masih belum terisi (harga belum melewatinya)
    valid_fvgs = []
    for fvg in reversed(fvg_list[-20:]):  # 20 candle terakhir
        if fvg['type'] == fvg_type_target:
            if direction == "BUY" and current_price > fvg['top']:
                # Harga sudah di atas FVG bullish — kandidat entry saat pullback
                valid_fvgs.append(fvg)
            elif direction == "SELL" and current_price < fvg['bot']:
                # Harga sudah di bawah FVG bearish — kandidat entry saat pullback
                valid_fvgs.append(fvg)

    if valid_fvgs:
        nearest_fvg = valid_fvgs[0]
        entry_zone = nearest_fvg['mid']
        entry_type = f"FVG {fvg_type_target} (top:{nearest_fvg['top']:.{cfg['dec']}f} bot:{nearest_fvg['bot']:.{cfg['dec']}f})"

    # Cari OB terdekat jika tidak ada FVG
    if not entry_zone and ob_list:
        ob_type_target = "BULLISH_OB" if direction == "BUY" else "BEARISH_OB"
        valid_obs = [ob for ob in reversed(ob_list[-20:]) if ob['type'] == ob_type_target]
        if valid_obs:
            nearest_ob = valid_obs[0]
            entry_zone = nearest_ob['mid']
            entry_type = f"OrderBlock {ob_type_target} (top:{nearest_ob['top']:.{cfg['dec']}f} bot:{nearest_ob['bot']:.{cfg['dec']}f})"

    if not entry_zone:
        print(f"  🔍 {symbol}: Tidak ada FVG/OB entry zone yang valid")
        return None

    # ── 5. SL / TP ICT Proper ────────────────────────────────────────────────
    swing_highs, swing_lows = find_swing_points(df_m5, lookback=5)
    min_sl = cfg['min_sl']
    max_sl = cfg['max_sl']

    if direction == "BUY":
        # SL di bawah swing low terdekat, tambah buffer
        if swing_lows:
            recent_sl = min([sl[1] for sl in swing_lows[-3:]])
            raw_sl    = recent_sl - (atr_m5 * 0.2)
        else:
            raw_sl = entry_zone - (atr_m5 * 1.5)

        sl_dist = entry_zone - raw_sl
        sl_dist = max(min_sl, min(sl_dist, max_sl))  # Clamp ke min/max
        sl      = entry_zone - sl_dist

        # TP ke swing high / liquidity tertinggi dengan RR min 2:1
        tp_min  = entry_zone + (sl_dist * 2.0)  # RR 1:2 minimum
        if swing_highs:
            tp_liq = max([sh[1] for sh in swing_highs[-3:]])
            tp     = tp_liq if tp_liq > tp_min else entry_zone + (sl_dist * 3.0)
        else:
            tp     = entry_zone + (sl_dist * 3.0)

    else:  # SELL
        if swing_highs:
            recent_sh = max([sh[1] for sh in swing_highs[-3:]])
            raw_sl    = recent_sh + (atr_m5 * 0.2)
        else:
            raw_sl = entry_zone + (atr_m5 * 1.5)

        sl_dist = raw_sl - entry_zone
        sl_dist = max(min_sl, min(sl_dist, max_sl))
        sl      = entry_zone + sl_dist

        tp_min  = entry_zone - (sl_dist * 2.0)
        if swing_lows:
            tp_liq = min([sl[1] for sl in swing_lows[-3:]])
            tp     = tp_liq if tp_liq < tp_min else entry_zone - (sl_dist * 3.0)
        else:
            tp     = entry_zone - (sl_dist * 3.0)

    # RR filter
    rr = abs(tp - entry_zone) / max(abs(sl - entry_zone), 0.000001)
    if rr < 2.0:
        print(f"  ❌ {symbol}: RR {rr:.1f}:1 terlalu rendah, skip")
        return None

    # Cek spread tidak terlalu lebar
    tick = mt5.symbol_info_tick(symbol)
    if tick:
        spread_points = (tick.ask - tick.bid) / mt5.symbol_info(symbol).point
        if spread_points > cfg['spread_max']:
            print(f"  ⚠️  {symbol}: Spread {spread_points:.0f} pts terlalu lebar, skip")
            return None

    return {
        "symbol":      symbol,
        "direction":   direction,
        "entry":       entry_zone,
        "sl":          sl,
        "tp":          tp,
        "sl_dist":     sl_dist,
        "rr":          rr,
        "lot":         cfg['lot'],
        "entry_type":  entry_type,
        "daily_bias":  daily_bias,
        "bias_detail": bias_detail,
        "msb":         msb,
        "session":     session,
        "macro":       macro_label,
        "macro_phase": macro_phase,
        "dec":         cfg['dec'],
    }

# ══════════════════════════════════════════════════════════════════════════════
# LOT SIZE KALKULASI (Risk-Based)
# ══════════════════════════════════════════════════════════════════════════════

def calculate_lot(symbol, sl_distance, risk_pct=RISK_PER_TRADE_PCT):
    """
    Hitung lot berdasarkan % risk dari balance
    Formula: Lot = (Balance * Risk%) / (SL_distance * Pip_value)
    """
    account = mt5.account_info()
    if not account:
        return PAIRS_CONFIG[symbol]['lot']  # fallback default lot

    balance      = account.balance
    risk_amount  = balance * (risk_pct / 100.0)

    sym_info = mt5.symbol_info(symbol)
    if not sym_info:
        return PAIRS_CONFIG[symbol]['lot']

    # Pip value: 1 lot = berapa USD per pip
    # Contract size * point
    contract_size = sym_info.trade_contract_size
    point         = sym_info.point
    tick_value    = sym_info.trade_tick_value
    tick_size     = sym_info.trade_tick_size

    # SL dalam ticks
    sl_ticks    = sl_distance / tick_size
    value_per_lot = sl_ticks * tick_value

    if value_per_lot <= 0:
        return PAIRS_CONFIG[symbol]['lot']

    raw_lot = risk_amount / value_per_lot
    # Round ke volume step
    vol_step = sym_info.volume_step
    lot      = round(raw_lot / vol_step) * vol_step
    lot      = max(sym_info.volume_min, min(lot, sym_info.volume_max))

    print(f"  💰 {symbol}: Balance ${balance:.2f} | Risk {risk_pct}% = ${risk_amount:.2f} | Lot: {lot}")
    return lot

# ══════════════════════════════════════════════════════════════════════════════
# ORDER EXECUTION
# ══════════════════════════════════════════════════════════════════════════════

def place_order(signal):
    """Eksekusi order di MT5"""
    symbol    = signal['symbol']
    direction = signal['direction']
    sl        = signal['sl']
    tp        = signal['tp']
    sl_dist   = signal['sl_dist']
    dec       = signal['dec']

    # Hitung lot berdasarkan risk
    lot = calculate_lot(symbol, sl_dist)

    # Ambil harga terkini
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        print(f"❌ {symbol}: Tidak bisa ambil tick price")
        return False

    price     = tick.ask if direction == "BUY" else tick.bid
    order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
    deviation  = 20  # Slippage max 20 points

    # Sesuaikan SL/TP ke digits pair
    digits = mt5.symbol_info(symbol).digits

    request = {
        "action":       mt5.TRADE_ACTION_DEAL,
        "symbol":       symbol,
        "volume":       lot,
        "type":         order_type,
        "price":        round(price, digits),
        "sl":           round(sl, digits),
        "tp":           round(tp, digits),
        "deviation":    deviation,
        "magic":        MAGIC_NUMBER,
        "comment":      f"ICT-{signal['session']}-{signal['macro_phase'][:3]}",
        "type_time":    mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)

    if result.retcode == mt5.TRADE_RETCODE_DONE:
        msg = (
            f"✅ *ORDER MASUK: {symbol}* ✅\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📥 *{direction}* @ `{price:.{dec}f}`\n"
            f"🛑 *SL:* `{sl:.{dec}f}`\n"
            f"🏆 *TP:* `{tp:.{dec}f}`\n"
            f"📐 *RR:* {signal['rr']:.1f}:1\n"
            f"🎯 *Lot:* {lot}\n"
            f"📍 *Zone:* {signal['entry_type']}\n"
            f"🔥 *Setup:* {signal['msb']} | {signal['daily_bias']}\n"
            f"🕐 *Sesi:* {signal['session']} | {signal['macro']}\n"
            f"_Freedom Syndicate MT5 | {datetime.now(WIB).strftime('%H:%M WIB')}_"
        )
        send_telegram(msg)
        print(f"  ✅ ORDER MASUK #{result.order}: {direction} {symbol} @ {price:.{dec}f} | SL:{sl:.{dec}f} TP:{tp:.{dec}f}")
        return True
    else:
        print(f"  ❌ Order gagal [{symbol}]: {result.retcode} — {result.comment}")
        if result.retcode == 10004:  # Requote
            print("     Requote! Coba lagi...")
        elif result.retcode == 10013:
            print("     Invalid request — cek SL/TP minimum distance broker")
        return False

# ══════════════════════════════════════════════════════════════════════════════
# RISK MANAGEMENT — DAILY LOSS & DRAWDOWN GUARD
# ══════════════════════════════════════════════════════════════════════════════

def check_risk_guard():
    """
    Cek apakah bot boleh trading:
    - Jika daily loss > MAX_DAILY_LOSS_PCT → stop hari ini
    - Jika equity drawdown > MAX_DRAWDOWN_PCT → stop total
    """
    global daily_start_balance

    account = mt5.account_info()
    if not account:
        return False

    balance = account.balance
    equity  = account.equity

    if daily_start_balance is None:
        daily_start_balance = balance

    daily_pnl_pct = ((balance - daily_start_balance) / max(daily_start_balance, 1)) * 100
    dd_pct        = ((daily_start_balance - equity) / max(daily_start_balance, 1)) * 100

    if daily_pnl_pct <= -MAX_DAILY_LOSS_PCT:
        msg = f"🚨 *DAILY LOSS LIMIT*\nPnL hari ini: {daily_pnl_pct:.1f}%\nBot berhenti trading hari ini!"
        send_telegram(msg)
        print(f"🚨 Daily loss {daily_pnl_pct:.1f}% — melewati batas {MAX_DAILY_LOSS_PCT}%")
        return False

    if dd_pct >= MAX_DRAWDOWN_PCT:
        msg = f"🚨 *MAX DRAWDOWN*\nDD: {dd_pct:.1f}%\nBot BERHENTI TOTAL!"
        send_telegram(msg)
        print(f"🚨 MAX DRAWDOWN {dd_pct:.1f}% — bot berhenti total!")
        return False

    # Cek jumlah posisi terbuka
    positions = mt5.positions_get(magic=MAGIC_NUMBER)
    if positions and len(positions) >= MAX_OPEN_TRADES:
        print(f"  ⏸️  Max {MAX_OPEN_TRADES} posisi terbuka, skip scan")
        return False

    return True

def count_open_positions_by_symbol(symbol):
    """Cek apakah sudah ada posisi terbuka di pair ini"""
    positions = mt5.positions_get(symbol=symbol, magic=MAGIC_NUMBER)
    return len(positions) if positions else 0

# ══════════════════════════════════════════════════════════════════════════════
# TELEGRAM NOTIFIKASI
# ══════════════════════════════════════════════════════════════════════════════

def send_telegram(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN_TG}/sendMessage",
            json={"chat_id": CHAT_ID_TG, "message_thread_id": TOPIC_ID,
                  "text": msg, "parse_mode": "Markdown"},
            timeout=8
        )
    except:
        pass

# ══════════════════════════════════════════════════════════════════════════════
# MAIN LOOP
# ══════════════════════════════════════════════════════════════════════════════

def run_autotrader():
    global daily_start_balance, session_traded_pairs

    print(f"\n🚀 {BOT_NAME} STARTING...")
    print(f"   Pairs   : {list(PAIRS_CONFIG.keys())}")
    print(f"   Risk    : {RISK_PER_TRADE_PCT}% per trade")
    print(f"   Max DD  : {MAX_DRAWDOWN_PCT}%")
    print(f"   Magic # : {MAGIC_NUMBER}\n")

    if not connect_mt5():
        print("❌ Tidak bisa connect MT5. Pastikan MT5 sudah dibuka dan login.")
        return

    send_telegram(f"🚀 *{BOT_NAME}* ONLINE\nPairs: {', '.join(PAIRS_CONFIG.keys())}\nRisk: {RISK_PER_TRADE_PCT}%/trade")

    last_session = None
    scan_interval = 60  # Scan setiap 60 detik

    while True:
        try:
            now_wib = datetime.now(WIB)
            session = get_active_session()

            # Reset session_traded_pairs saat ganti sesi
            if session != last_session:
                session_traded_pairs = set()
                last_session = session
                if session != "OFF":
                    print(f"\n🔔 [{now_wib.strftime('%H:%M WIB')}] Sesi {session} dimulai!")

            print(f"\n[{now_wib.strftime('%H:%M:%S WIB')}] Sesi: {session} | {get_killzone_label()}")

            # Cek risk guard
            if not check_risk_guard():
                time.sleep(300)  # Tunggu 5 menit sebelum cek lagi
                continue

            # OFF session — tidak scan
            if session == "OFF":
                print("  💤 OFF Session — menunggu sesi berikutnya...")
                time.sleep(scan_interval)
                continue

            # Scan setiap pair
            for symbol in PAIRS_CONFIG.keys():
                # Skip jika sudah ada posisi di pair ini
                if count_open_positions_by_symbol(symbol) > 0:
                    print(f"  ⏭️  {symbol}: Sudah ada posisi terbuka, skip")
                    continue

                # Skip jika sudah entry di sesi ini
                if symbol in session_traded_pairs:
                    print(f"  ⏭️  {symbol}: Sudah entry di sesi {session} ini")
                    continue

                print(f"  🔍 Analisa {symbol}...")
                signal = analyze_pair_ict(symbol)

                if signal:
                    print(f"  🎯 SETUP DITEMUKAN: {symbol} {signal['direction']} | RR {signal['rr']:.1f}:1")
                    print(f"     Entry Zone : {signal['entry_type']}")
                    print(f"     Daily Bias : {signal['daily_bias']} — {signal['bias_detail']}")
                    print(f"     MSB        : {signal['msb']}")
                    print(f"     Macro      : {signal['macro']}")

                    success = place_order(signal)
                    if success:
                        session_traded_pairs.add(symbol)
                else:
                    print(f"  💭 {symbol}: Tidak ada setup ICT valid")

                time.sleep(2)  # Jeda antar pair

            # Update daily balance di jam 00:00 WIB
            if now_wib.hour == 0 and now_wib.minute < 2:
                acc = mt5.account_info()
                if acc:
                    daily_start_balance = acc.balance
                    print(f"📅 Daily balance reset: ${daily_start_balance:.2f}")

            print(f"  ✅ Scan selesai. Next scan dalam {scan_interval}s...")
            time.sleep(scan_interval)

        except KeyboardInterrupt:
            print("\n⛔ Bot dihentikan manual.")
            send_telegram("⛔ Freedom MT5 Bot dihentikan manual.")
            mt5.shutdown()
            break
        except Exception as e:
            print(f"❌ Error utama: {e}")
            time.sleep(30)
            # Reconnect jika terputus
            if not mt5.account_info():
                print("🔄 Reconnecting MT5...")
                connect_mt5()

if __name__ == "__main__":
    run_autotrader()
