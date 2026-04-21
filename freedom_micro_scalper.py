"""
╔══════════════════════════════════════════════════════════════════════════════╗
║   FREEDOM MICRO SCALPER — MT5 M1 ENGINE                                      ║
║   Khusus Modal Kecil → Compound Growth                                        ║
║   Strategi: EMA Cross + Stochastic + RSI + Candle Pattern                    ║
║   Pair: XAUUSD | TF Entry: M1 | Konfirmasi: M5                               ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  INSTALL:  pip install MetaTrader5 numpy pandas requests                      ║
║  JALANKAN: python freedom_micro_scalper.py                                    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  ⚠️  TEST DI AKUN DEMO DULU MINIMAL 1 MINGGU SEBELUM LIVE                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import MetaTrader5 as mt5
import numpy as np
import pandas as pd
import time
import requests
from datetime import datetime, timezone, timedelta

# ══════════════════════════════════════════════════════════════════════════════
# ─── KONFIGURASI AKUN ─────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
MT5_LOGIN    = 15968176
MT5_PASSWORD = "Winongo*03"
MT5_SERVER   = "Headway-Real"

# ─── TELEGRAM ──────────────────────────────────────────────────────────────────
TOKEN_TG   = "8196511062:AAGyfWcRUk9uw_lc_aQgUW6vLyyRmgF1hcE"
CHAT_ID_TG = "-1003660980986"
TOPIC_ID   = 18

# ══════════════════════════════════════════════════════════════════════════════
# ─── PARAMETER SCALPING ───────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
SYMBOL       = "XAUUSD"
MAGIC        = 999111
WIB          = timezone(timedelta(hours=7))
BOT_NAME     = "Freedom Micro Scalper M1"

# ─── RISK MANAGEMENT (KUNCI UTAMA) ────────────────────────────────────────────
RISK_PCT          = 2.0    # % balance per trade — naik seiring balance tumbuh
MAX_RISK_PCT      = 3.0    # Cap maksimum risk saat balance sudah besar
MIN_LOT           = 0.01   # Lot terkecil (sesuai broker)
MAX_LOT           = 2.0    # Cap lot maksimum
MAX_DAILY_TRADES  = 5      # Maksimum trade per hari
MAX_DAILY_LOSS_PCT = 6.0   # Stop hari ini jika rugi > 6%
MAX_DD_PCT        = 12.0   # Berhenti total jika drawdown > 12%

# ─── SCALPING PARAMETERS ──────────────────────────────────────────────────────
# EMA untuk trend
EMA_FAST = 5
EMA_MED  = 13
EMA_SLOW = 21

# Stochastic (untuk timing entry presisi)
STOCH_K      = 5
STOCH_D      = 3
STOCH_SMOOTH = 3
STOCH_OB     = 75   # Overbought
STOCH_OS     = 25   # Oversold

# RSI
RSI_PERIOD = 7      # Lebih cepat untuk M1 scalping
RSI_BUY    = 55     # Min RSI untuk BUY entry
RSI_SELL   = 45     # Max RSI untuk SELL entry
RSI_OB     = 75     # RSI overbought — hindari buy di sini
RSI_OS     = 25     # RSI oversold — hindari sell di sini

# ATR untuk SL/TP
ATR_PERIOD   = 10
ATR_SL_MULT  = 1.0   # SL = 1.0 × ATR (ketat untuk scalp)
ATR_TP_MULT  = 2.2   # TP = 2.2 × ATR (RR 2.2:1)

# Breakeven & Trailing
BE_AT_RR      = 0.8   # Breakeven saat profit 0.8×SL (cepat aman)
TRAIL_TRIGGER = 1.2   # Trail aktif saat profit 1.2×SL
TRAIL_DIST    = 0.8   # Trail distance = 0.8×ATR

# ─── SESSION FILTER ────────────────────────────────────────────────────────────
# Hanya scalp saat market paling likuid (volume tinggi = spread kecil = lebih bisa profit)
ACTIVE_SESSIONS = {
    "LONDON":   (14, 18),    # 14:00–18:00 WIB
    "NEWYORK":  (20, 23),    # 20:00–23:00 WIB
    "LONDON_NY":(19, 21),    # Overlap paling volatile
}

# ─── STATE ─────────────────────────────────────────────────────────────────────
daily_start_balance = None
daily_trade_count   = 0
daily_date          = None
trade_states        = {}    # {ticket: state dict}
scan_count          = 0

# ══════════════════════════════════════════════════════════════════════════════
# KONEKSI
# ══════════════════════════════════════════════════════════════════════════════

def connect_mt5() -> bool:
    if not mt5.initialize():
        print(f"❌ MT5 init gagal: {mt5.last_error()}")
        return False
    if not mt5.login(MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER):
        print(f"❌ Login gagal: {mt5.last_error()}")
        mt5.shutdown()
        return False
    acc = mt5.account_info()
    print(f"✅ Connected: {acc.login} | {acc.name}")
    print(f"   Balance: ${acc.balance:.2f} | Equity: ${acc.equity:.2f}")
    return True

# ══════════════════════════════════════════════════════════════════════════════
# DATA
# ══════════════════════════════════════════════════════════════════════════════

def get_bars(symbol: str, tf, bars: int = 200):
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, bars)
    if rates is None or len(rates) < 50:
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

# ══════════════════════════════════════════════════════════════════════════════
# INDIKATOR
# ══════════════════════════════════════════════════════════════════════════════

def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, 1e-9)
    return 100 - (100 / (1 + rs))

def stochastic(df: pd.DataFrame, k: int = 5, d: int = 3, smooth: int = 3):
    """Stochastic %K dan %D"""
    low_min  = df['low'].rolling(k).min()
    high_max = df['high'].rolling(k).max()
    k_raw    = 100 * (df['close'] - low_min) / (high_max - low_min + 1e-9)
    k_smooth = k_raw.rolling(smooth).mean()
    d_line   = k_smooth.rolling(d).mean()
    return k_smooth, d_line

def atr(df: pd.DataFrame, period: int = 10) -> float:
    """ATR"""
    h, l, c = df['high'].values, df['low'].values, df['close'].values
    trs = []
    for i in range(1, len(c)):
        trs.append(max(h[i]-l[i], abs(h[i]-c[i-1]), abs(l[i]-c[i-1])))
    if len(trs) < period:
        return np.mean(trs) if trs else 1.0
    return float(np.mean(trs[-period:]))

def detect_candle_pattern(df: pd.DataFrame):
    """
    Deteksi pola candle untuk konfirmasi entry:
    - Bullish Engulfing
    - Bearish Engulfing
    - Hammer / Pin Bar
    - Shooting Star
    """
    if len(df) < 3:
        return "NONE"

    c1 = df.iloc[-3]   # 2 candle lalu
    c2 = df.iloc[-2]   # Candle sebelumnya
    c3 = df.iloc[-1]   # Candle terkini (sedang terbentuk / baru close)

    open2,  close2 = c2['open'],  c2['close']
    open3,  close3 = c3['open'],  c3['close']
    high3,  low3   = c3['high'],  c3['low']

    body2  = abs(close2 - open2)
    body3  = abs(close3 - open3)
    range3 = high3 - low3 + 1e-9

    # Bullish Engulfing — candle hijau menelan candle merah sebelumnya
    if (close2 < open2 and         # Candle sebelum = merah
        close3 > open3 and         # Candle ini = hijau
        close3 > open2 and         # Body hijau melewati open candle merah
        open3  < close2):          # Open di bawah close candle merah
        return "BULL_ENGULF"

    # Bearish Engulfing
    if (close2 > open2 and
        close3 < open3 and
        close3 < open2 and
        open3  > close2):
        return "BEAR_ENGULF"

    # Hammer (Bullish) — lower shadow panjang, body kecil di atas
    lower_shadow = min(open3, close3) - low3
    upper_shadow = high3 - max(open3, close3)
    if (lower_shadow > body3 * 2.0 and
        upper_shadow < body3 * 0.5 and
        close3 >= open3):          # Body bullish
        return "HAMMER"

    # Shooting Star (Bearish) — upper shadow panjang, body kecil di bawah
    if (upper_shadow > body3 * 2.0 and
        lower_shadow < body3 * 0.5 and
        close3 <= open3):          # Body bearish
        return "SHOOTING_STAR"

    # Bullish Pin Bar — sumbu bawah > 60% total range
    if lower_shadow / range3 > 0.6 and body3 / range3 < 0.3:
        return "BULL_PIN"

    # Bearish Pin Bar
    if upper_shadow / range3 > 0.6 and body3 / range3 < 0.3:
        return "BEAR_PIN"

    return "NONE"

def get_m5_bias(symbol: str):
    """
    Bias dari M5:
    Bullish: EMA13 > EMA21 dan harga > EMA13
    Bearish: EMA13 < EMA21 dan harga < EMA13
    """
    df = get_bars(symbol, mt5.TIMEFRAME_M5, 60)
    if df is None:
        return "NEUTRAL"
    e13  = ema(df['close'], 13).iloc[-1]
    e21  = ema(df['close'], 21).iloc[-1]
    price = df['close'].iloc[-1]
    if e13 > e21 and price > e13:
        return "BULLISH"
    elif e13 < e21 and price < e13:
        return "BEARISH"
    return "NEUTRAL"

# ══════════════════════════════════════════════════════════════════════════════
# SESSION CHECK
# ══════════════════════════════════════════════════════════════════════════════

def in_active_session() -> tuple[bool, str]:
    hr = datetime.now(WIB).hour
    for name, (start, end) in ACTIVE_SESSIONS.items():
        if start <= hr < end:
            return True, name
    return False, "OFF"

# ══════════════════════════════════════════════════════════════════════════════
# DYNAMIC LOT (COMPOUND)
# ══════════════════════════════════════════════════════════════════════════════

def calc_lot(symbol: str, sl_price_dist: float) -> float:
    """
    Compound lot — otomatis naik seiring balance tumbuh.
    Lot = (Balance × Risk%) / (SL_dist × contract_size)
    """
    acc      = mt5.account_info()
    sym_info = mt5.symbol_info(symbol)
    if not acc or not sym_info:
        return MIN_LOT

    balance  = acc.balance
    # Risk naik perlahan seiring balance tumbuh (compound booster)
    # Di bawah $50: pakai RISK_PCT, di atas $100: bisa sampai MAX_RISK_PCT
    dynamic_risk = RISK_PCT
    if balance > 50:
        extra = min((balance - 50) / 200, 1.0) * (MAX_RISK_PCT - RISK_PCT)
        dynamic_risk = RISK_PCT + extra

    risk_usd   = balance * (dynamic_risk / 100.0)
    contract   = sym_info.trade_contract_size  # 100 untuk XAUUSD
    sl_usd_lot = sl_price_dist * contract      # USD loss per 1 lot per unit SL

    if sl_usd_lot <= 0:
        return MIN_LOT

    lot  = risk_usd / sl_usd_lot
    lot  = max(MIN_LOT, min(round(lot, 2), MAX_LOT))
    step = sym_info.volume_step if sym_info.volume_step > 0 else 0.01
    lot  = round(lot / step) * step
    lot  = max(sym_info.volume_min, min(lot, sym_info.volume_max))

    print(f"  💰 Balance ${balance:.2f} | Risk {dynamic_risk:.1f}% (${risk_usd:.2f}) | Lot: {lot:.2f}")
    return lot

# ══════════════════════════════════════════════════════════════════════════════
# ANALISA & SINYAL M1
# ══════════════════════════════════════════════════════════════════════════════

def analyze_m1(symbol: str):
    """
    Full M1 Scalping Analysis:
    Confluence Score:
      [1] M5 Bias searah         → wajib
      [2] EMA5 > EMA13 > EMA21  → wajib
      [3] Stochastic cross       → wajib
      [4] RSI momentum           → wajib
      [5] Candle pattern         → +1 skor (bonus)
    Entry hanya jika semua 4 wajib terpenuhi.
    """
    df = get_bars(symbol, mt5.TIMEFRAME_M1, 150)
    if df is None or len(df) < 50:
        return None

    # ── Hitung indikator ──────────────────────────────────────────────────
    df['ema5']  = ema(df['close'], EMA_FAST)
    df['ema13'] = ema(df['close'], EMA_MED)
    df['ema21'] = ema(df['close'], EMA_SLOW)
    df['rsi']   = rsi(df['close'], RSI_PERIOD)
    df['stk'], df['std'] = stochastic(df, STOCH_K, STOCH_D, STOCH_SMOOTH)

    # Nilai terkini
    e5    = df['ema5'].iloc[-1]
    e13   = df['ema13'].iloc[-1]
    e21   = df['ema21'].iloc[-1]
    e5_p  = df['ema5'].iloc[-2]   # EMA5 candle sebelumnya
    rsi_v = df['rsi'].iloc[-1]
    stk_v = df['stk'].iloc[-1]
    std_v = df['std'].iloc[-1]
    stk_p = df['stk'].iloc[-2]
    std_p = df['std'].iloc[-2]
    price = df['close'].iloc[-1]

    atr_v   = atr(df, ATR_PERIOD)
    pattern = detect_candle_pattern(df)
    m5_bias = get_m5_bias(symbol)

    # ── Cari swing points untuk SL ────────────────────────────────────────
    lows  = df['low'].values[-30:]
    highs = df['high'].values[-30:]
    recent_low  = float(np.min(lows))
    recent_high = float(np.max(highs))

    # ── EVALUASI BUY ──────────────────────────────────────────────────────
    buy_conditions = {
        "m5_bias_bull":   m5_bias == "BULLISH",
        "ema_ribbon_bull": e5 > e13 > e21,
        "ema_cross_bull": e5 > e5_p and e5 > e13,        # EMA5 baru cross
        "stoch_cross_bull": stk_v > std_v and stk_p <= std_p,  # Stoch bullish cross
        "stoch_not_ob":   stk_v < STOCH_OB,               # Stoch tidak overbought
        "rsi_bull":       RSI_BUY <= rsi_v <= RSI_OB,     # RSI zona beli
        "price_above_ema": price > e5,
    }

    # ── EVALUASI SELL ─────────────────────────────────────────────────────
    sell_conditions = {
        "m5_bias_bear":   m5_bias == "BEARISH",
        "ema_ribbon_bear": e5 < e13 < e21,
        "ema_cross_bear": e5 < e5_p and e5 < e13,
        "stoch_cross_bear": stk_v < std_v and stk_p >= std_p,
        "stoch_not_os":   stk_v > STOCH_OS,
        "rsi_bear":       RSI_OS <= rsi_v <= RSI_SELL,
        "price_below_ema": price < e5,
    }

    # Wajib semua kondisi utama terpenuhi
    buy_mandatory  = ["m5_bias_bull", "ema_ribbon_bull", "stoch_cross_bull",
                      "stoch_not_ob", "rsi_bull", "price_above_ema"]
    sell_mandatory = ["m5_bias_bear", "ema_ribbon_bear", "stoch_cross_bear",
                      "stoch_not_os", "rsi_bear", "price_below_ema"]

    direction = None
    miss_list = []

    if all(buy_conditions[k] for k in buy_mandatory):
        direction = "BUY"
    elif all(sell_conditions[k] for k in sell_mandatory):
        direction = "SELL"
    else:
        # Tampilkan kondisi yang belum terpenuhi untuk debug
        for k in buy_mandatory:
            if not buy_conditions[k]:
                miss_list.append(f"BUY/{k}=❌")
        for k in sell_mandatory:
            if not sell_conditions[k]:
                miss_list.append(f"SELL/{k}=❌")
        return None

    # Candle pattern bonus — print info tapi tidak wajib
    pattern_bonus = pattern in ["BULL_ENGULF", "HAMMER", "BULL_PIN"] if direction == "BUY" \
               else pattern in ["BEAR_ENGULF", "SHOOTING_STAR", "BEAR_PIN"]

    # ── SL / TP ───────────────────────────────────────────────────────────
    sl_dist = atr_v * ATR_SL_MULT
    tp_dist = atr_v * ATR_TP_MULT

    # SL selalu di balik swing terdekat (lebih aman dari ATR saja)
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return None
    entry = tick.ask if direction == "BUY" else tick.bid

    if direction == "BUY":
        sl_swing = recent_low - (atr_v * 0.2)
        sl_atr   = entry - sl_dist
        sl       = max(sl_swing, sl_atr)  # Ambil yang paling konservatif (lebih jauh)
        tp       = entry + tp_dist
    else:
        sl_swing = recent_high + (atr_v * 0.2)
        sl_atr   = entry + sl_dist
        sl       = min(sl_swing, sl_atr)
        tp       = entry - tp_dist

    actual_sl_dist = abs(entry - sl)
    actual_tp_dist = abs(entry - tp)
    rr_ratio = actual_tp_dist / max(actual_sl_dist, 0.001)

    if rr_ratio < 1.5:
        print(f"  ❌ RR {rr_ratio:.1f} terlalu rendah (min 1.5). Skip.")
        return None

    # Spread check
    sym_info = mt5.symbol_info(symbol)
    spread   = (tick.ask - tick.bid) / sym_info.point
    if spread > 35:
        print(f"  ⚠️  Spread {spread:.0f} pts terlalu lebar. Skip.")
        return None

    return {
        "direction":   direction,
        "entry":       entry,
        "sl":          sl,
        "tp":          tp,
        "sl_dist":     actual_sl_dist,
        "tp_dist":     actual_tp_dist,
        "atr":         atr_v,
        "rr":          rr_ratio,
        "rsi":         rsi_v,
        "stk":         stk_v,
        "std":         std_v,
        "m5_bias":     m5_bias,
        "pattern":     pattern,
        "pattern_ok":  pattern_bonus,
        "spread":      spread,
        "ema5":        e5,
        "ema13":       e13,
        "ema21":       e21,
    }

# ══════════════════════════════════════════════════════════════════════════════
# ORDER EXECUTION
# ══════════════════════════════════════════════════════════════════════════════

def place_order(sig: dict) -> tuple[bool, int]:
    symbol    = SYMBOL
    direction = sig['direction']
    sl        = sig['sl']
    tp        = sig['tp']
    sl_dist   = sig['sl_dist']
    digits    = mt5.symbol_info(symbol).digits

    lot = calc_lot(symbol, sl_dist)
    if lot <= 0:
        return False, -1

    tick  = mt5.symbol_info_tick(symbol)
    price = tick.ask if direction == "BUY" else tick.bid
    otype = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL

    req = {
        "action":       mt5.TRADE_ACTION_DEAL,
        "symbol":       symbol,
        "volume":       lot,
        "type":         otype,
        "price":        round(price, digits),
        "sl":           round(sl, digits),
        "tp":           round(tp, digits),
        "deviation":    20,
        "magic":        MAGIC,
        "comment":      f"MScalp-{direction[:1]}{sig['pattern'][:4]}",
        "type_time":    mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    res = mt5.order_send(req)
    if res and res.retcode == mt5.TRADE_RETCODE_DONE:
        # Simpan state untuk BE & trailing
        trade_states[res.order] = {
            "entry":    price,
            "sl_dist":  sl_dist,
            "atr":      sig['atr'],
            "direction": direction,
            "lot":      lot,
            "be_done":  False,
            "trail_on": False,
            "trail_dist": sig['atr'] * TRAIL_DIST,
        }

        acc  = mt5.account_info()
        dec  = 2
        msg  = (
            f"🟢 *SCALP {direction}: {symbol}* 🟢\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💵 Entry  : `{price:.{dec}f}`  Lot: `{lot}`\n"
            f"🛑 SL     : `{sl:.{dec}f}`\n"
            f"🏆 TP     : `{tp:.{dec}f}`\n"
            f"📐 RR     : `{sig['rr']:.1f}:1`\n"
            f"📊 RSI    : `{sig['rsi']:.1f}` | Stoch: `{sig['stk']:.1f}`\n"
            f"🕯️ Pattern: `{sig['pattern']}`{'✅' if sig['pattern_ok'] else ''}\n"
            f"📈 M5 Bias: `{sig['m5_bias']}`\n"
            f"💰 Balance: `${acc.balance:.2f}`\n"
            f"_{BOT_NAME} | {datetime.now(WIB).strftime('%H:%M WIB')}_"
        )
        send_telegram(msg)
        print(f"  ✅ ORDER #{res.order}: {direction} @ {price:.2f} | "
              f"SL:{sl:.2f} TP:{tp:.2f} | Lot:{lot} | RR:{sig['rr']:.1f}")
        return True, res.order
    else:
        code = res.retcode if res else "?"
        print(f"  ❌ Order gagal: {code}")
        if res:
            err_map = {
                10004: "Requote",
                10013: "Invalid SL/TP — cek min distance broker",
                10014: "Volume terlalu kecil",
                10019: "Dana tidak cukup",
            }
            print(f"     {err_map.get(code, res.comment)}")
        return False, -1

# ══════════════════════════════════════════════════════════════════════════════
# BREAKEVEN & TRAILING STOP
# ══════════════════════════════════════════════════════════════════════════════

def manage_positions():
    """Kelola semua posisi terbuka — breakeven dulu, lalu trailing."""
    positions = mt5.positions_get(magic=MAGIC)
    if not positions:
        return

    for pos in positions:
        ticket    = pos.ticket
        direction = "BUY" if pos.type == 0 else "SELL"
        entry     = pos.price_open
        sl_now    = pos.sl
        tp        = pos.tp
        price_now = pos.price_current
        symbol    = pos.symbol
        digits    = mt5.symbol_info(symbol).digits

        state = trade_states.get(ticket)
        if not state:
            sl_d = abs(entry - sl_now) if sl_now > 0 else 3.0
            trade_states[ticket] = {
                "entry":    entry,
                "sl_dist":  sl_d,
                "atr":      sl_d,
                "direction": direction,
                "lot":      pos.volume,
                "be_done":  False,
                "trail_on": False,
                "trail_dist": sl_d * TRAIL_DIST,
            }
            state = trade_states[ticket]

        sl_d       = state['sl_dist']
        be_done    = state['be_done']
        trail_on   = state['trail_on']
        trail_dist = state['trail_dist']
        profit_d   = (price_now - entry) if direction == "BUY" else (entry - price_now)
        new_sl     = None
        action     = ""

        # ── Breakeven ─────────────────────────────────────────────────────
        if not be_done and profit_d >= sl_d * BE_AT_RR:
            buf = state['atr'] * 0.05   # Buffer 5% ATR di atas entry
            if direction == "BUY":
                be_sl = entry + buf
                if be_sl > (sl_now if sl_now > 0 else 0):
                    new_sl = be_sl
                    action = f"🔒 BE BUY → {be_sl:.2f}"
            else:
                be_sl = entry - buf
                if be_sl < sl_now or sl_now == 0:
                    new_sl = be_sl
                    action = f"🔒 BE SELL → {be_sl:.2f}"
            if new_sl:
                state['be_done'] = True

        # ── Trailing ──────────────────────────────────────────────────────
        if be_done:
            if not trail_on and profit_d >= sl_d * TRAIL_TRIGGER:
                state['trail_on'] = True
                action = f"🎯 TRAIL ON ({trail_dist:.2f})"

            if state['trail_on']:
                if direction == "BUY":
                    ideal = price_now - trail_dist
                    if ideal > (sl_now if sl_now > 0 else 0):
                        if new_sl is None or ideal > new_sl:
                            new_sl = ideal
                            action = f"📈 TRAIL → {ideal:.2f}"
                else:
                    ideal = price_now + trail_dist
                    if ideal < sl_now or sl_now == 0:
                        if new_sl is None or ideal < new_sl:
                            new_sl = ideal
                            action = f"📉 TRAIL → {ideal:.2f}"

        # ── Modifikasi ────────────────────────────────────────────────────
        if new_sl:
            mod = {
                "action":   mt5.TRADE_ACTION_SLTP,
                "symbol":   symbol,
                "position": ticket,
                "sl":       round(new_sl, digits),
                "tp":       round(tp, digits),
            }
            r = mt5.order_send(mod)
            if r and r.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"  🔧 #{ticket} {action}")
                if "BE" in action:
                    send_telegram(
                        f"🔒 *BREAKEVEN* #{ticket}\n"
                        f"{symbol} {direction} entry `{entry:.2f}`\n"
                        f"SL dipindah → sudah tidak bisa rugi!"
                    )
            else:
                err = r.retcode if r else "?"
                print(f"  ⚠️  Modify gagal #{ticket}: {err}")

# ══════════════════════════════════════════════════════════════════════════════
# RISK GUARD
# ══════════════════════════════════════════════════════════════════════════════

def check_risk() -> bool:
    global daily_start_balance, daily_trade_count, daily_date

    acc = mt5.account_info()
    if not acc:
        return False

    today = datetime.now(WIB).date()
    if daily_date != today:
        daily_date          = today
        daily_start_balance = acc.balance
        daily_trade_count   = 0
        print(f"\n📅 Hari baru: {today} | Balance: ${acc.balance:.2f}")

    if daily_start_balance is None:
        daily_start_balance = acc.balance

    daily_pnl = ((acc.balance - daily_start_balance) / max(daily_start_balance, 1)) * 100
    dd        = ((daily_start_balance - acc.equity)   / max(daily_start_balance, 1)) * 100

    if daily_pnl <= -MAX_DAILY_LOSS_PCT:
        msg = f"🚨 *DAILY LOSS {daily_pnl:.1f}%* — Bot stop hari ini!"
        print(f"🚨 Daily loss {daily_pnl:.1f}% > {MAX_DAILY_LOSS_PCT}%")
        send_telegram(msg)
        return False

    if dd >= MAX_DD_PCT:
        msg = f"🚨 *MAX DD {dd:.1f}%* — Bot BERHENTI TOTAL!"
        print(f"🚨 Drawdown {dd:.1f}% > {MAX_DD_PCT}%")
        send_telegram(msg)
        return False

    if daily_trade_count >= MAX_DAILY_TRADES:
        print(f"  ⏸️  Max {MAX_DAILY_TRADES} trade/hari tercapai")
        return False

    positions = mt5.positions_get(magic=MAGIC)
    if positions and len(positions) >= 1:
        return False   # Sudah ada posisi terbuka

    return True

# ══════════════════════════════════════════════════════════════════════════════
# TELEGRAM
# ══════════════════════════════════════════════════════════════════════════════

def send_telegram(msg: str):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN_TG}/sendMessage",
            json={
                "chat_id":           CHAT_ID_TG,
                "message_thread_id": TOPIC_ID,
                "text":              msg,
                "parse_mode":        "Markdown"
            },
            timeout=8
        )
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════════════════
# STATUS DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

def print_dashboard():
    acc = mt5.account_info()
    if not acc:
        return
    pos   = mt5.positions_get(magic=MAGIC) or []
    dpnl  = acc.balance - (daily_start_balance or acc.balance)
    dpct  = (dpnl / max(daily_start_balance or 1, 1)) * 100
    float_ = sum(p.profit for p in pos)

    now = datetime.now(WIB)
    print(f"\n╔{'═'*52}╗")
    print(f"║  {BOT_NAME:<50}║")
    print(f"╠{'═'*52}╣")
    print(f"║  🕐 {now.strftime('%H:%M:%S WIB'):<47}║")
    print(f"║  💰 Balance  : ${acc.balance:<10.2f} Equity: ${acc.equity:.2f}{'':<5}║")
    print(f"║  📅 Daily P&L: ${dpnl:+.2f} ({dpct:+.1f}%)  Trades: {daily_trade_count}/{MAX_DAILY_TRADES}     ║")
    print(f"║  💹 Floating : ${float_:<10.2f} Positions: {len(pos):<14}║")
    if pos:
        for p in pos:
            d = "BUY " if p.type == 0 else "SELL"
            print(f"║    #{p.ticket} {d} {p.volume:.2f}L @ {p.price_open:.2f} P&L:${p.profit:.2f}{'':<10}║")
    print(f"╚{'═'*52}╝")

# ══════════════════════════════════════════════════════════════════════════════
# MAIN LOOP
# ══════════════════════════════════════════════════════════════════════════════

def run():
    global daily_trade_count, scan_count

    print(f"\n{'═'*60}")
    print(f"  🚀  {BOT_NAME}")
    print(f"  Symbol  : {SYMBOL}")
    print(f"  TF Entry: M1 | Konfirmasi: M5")
    print(f"  Risk    : {RISK_PCT}% compound (auto naik)")
    print(f"  Max DD  : {MAX_DD_PCT}% | Daily Loss: {MAX_DAILY_LOSS_PCT}%")
    print(f"  Max Trade/Day: {MAX_DAILY_TRADES}")
    print(f"{'═'*60}\n")

    if not connect_mt5():
        return

    acc = mt5.account_info()
    send_telegram(
        f"🚀 *{BOT_NAME}* ONLINE\n"
        f"👤 Akun: `{acc.login}` | `{MT5_SERVER}`\n"
        f"💰 Balance: `${acc.balance:.2f}`\n"
        f"⚙️ Risk: `{RISK_PCT}%/trade` | Max: `{MAX_DAILY_TRADES} trade/hari`\n"
        f"🛡️ Daily loss limit: `{MAX_DAILY_LOSS_PCT}%` | Max DD: `{MAX_DD_PCT}%`\n"
        f"⏰ Session: London {ACTIVE_SESSIONS['LONDON']} | NY {ACTIVE_SESSIONS['NEWYORK']} WIB"
    )

    SCAN_INTERVAL   = 20    # Scan tiap 20 detik (M1 = lebih cepat)
    MANAGE_INTERVAL = 8     # Cek BE/trail tiap 8 detik
    DASH_INTERVAL   = 60    # Dashboard tiap 1 menit
    last_manage = 0
    last_dash   = 0
    last_candle_time = None

    while True:
        try:
            now = datetime.now(WIB)
            scan_count += 1

            # ── Manage positions ─────────────────────────────────────────
            if time.time() - last_manage >= MANAGE_INTERVAL:
                manage_positions()
                last_manage = time.time()

            # ── Dashboard ─────────────────────────────────────────────────
            if time.time() - last_dash >= DASH_INTERVAL:
                print_dashboard()
                last_dash = time.time()

            # ── Session check ─────────────────────────────────────────────
            active, session_name = in_active_session()
            if not active:
                hr = now.hour
                # Hitung waktu ke sesi berikutnya
                next_sessions = [(14, "LONDON"), (20, "NEWYORK")]
                wait_msg = "💤 OFF Session"
                for (start, name) in next_sessions:
                    if hr < start:
                        wait_h = start - hr
                        wait_msg = f"💤 OFF Session — LONDON mulai {start}:00 WIB (~{wait_h}j lagi)"
                        break
                print(f"  [{now.strftime('%H:%M')}] {wait_msg}")
                time.sleep(60)
                continue

            # ── Risk guard ────────────────────────────────────────────────
            if not check_risk():
                time.sleep(SCAN_INTERVAL)
                continue

            # ── Cek candle M1 baru ────────────────────────────────────────
            bars = get_bars(SYMBOL, mt5.TIMEFRAME_M1, 5)
            if bars is None:
                time.sleep(10)
                continue

            current_candle = bars['time'].iloc[-1]

            # Scan analisa setiap candle baru (tidak spam tiap 20 detik)
            print(f"  [{now.strftime('%H:%M:%S')}] Sesi: {session_name} | "
                  f"Trades: {daily_trade_count}/{MAX_DAILY_TRADES} | Scan #{scan_count}")

            # ── Analisa M1 ────────────────────────────────────────────────
            sig = analyze_m1(SYMBOL)

            if sig:
                pat_str = f" | 🕯️ {sig['pattern']}" if sig['pattern'] != "NONE" else ""
                print(f"\n  🎯 SIGNAL! {sig['direction']} | RR {sig['rr']:.1f}:1")
                print(f"     Entry : {sig['entry']:.2f} | SL: {sig['sl']:.2f} | TP: {sig['tp']:.2f}")
                print(f"     RSI   : {sig['rsi']:.1f} | Stoch K:{sig['stk']:.1f} D:{sig['std']:.1f}")
                print(f"     M5 Bias: {sig['m5_bias']}{pat_str}")

                ok, ticket = place_order(sig)
                if ok:
                    daily_trade_count += 1
            else:
                # Tampilkan status indikator untuk monitoring
                df_check = get_bars(SYMBOL, mt5.TIMEFRAME_M1, 50)
                if df_check is not None:
                    r_v = rsi(df_check['close'], RSI_PERIOD).iloc[-1]
                    k_v, d_v = stochastic(df_check, STOCH_K, STOCH_D, STOCH_SMOOTH)
                    print(f"     RSI:{r_v:.1f} Stoch K:{k_v.iloc[-1]:.1f} D:{d_v.iloc[-1]:.1f} "
                          f"M5:{get_m5_bias(SYMBOL)} — Menunggu konfluensi...")

            time.sleep(SCAN_INTERVAL)

        except KeyboardInterrupt:
            print("\n⛔ Bot dihentikan.")
            send_telegram(f"⛔ *{BOT_NAME}* dihentikan manual.")
            mt5.shutdown()
            break

        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(15)
            if not mt5.account_info():
                print("🔄 Reconnecting...")
                connect_mt5()


if __name__ == "__main__":
    run()
