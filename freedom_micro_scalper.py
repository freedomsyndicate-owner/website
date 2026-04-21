"""
╔══════════════════════════════════════════════════════════════════════════════╗
║   FREEDOM AGGRESSIVE SCALPER — EVERY CANDLE M1                              ║
║   Setiap candle M1 close → langsung analisa → langsung order                ║
║   Compound lot agresif — tanpa drawdown/daily loss limit                    ║
║   ⚠️  HIGH RISK — bisa profit cepat, bisa blow account cepat                ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import MetaTrader5 as mt5
import numpy as np
import pandas as pd
import time
import requests
from datetime import datetime, timezone, timedelta

# ── AKUN ──────────────────────────────────────────────────────────────────────
MT5_LOGIN    = 15968176
MT5_PASSWORD = "Winongo*03"
MT5_SERVER   = "Headway-Real"
SYMBOL       = "XAUUSD"
MAGIC        = 888111
WIB          = timezone(timedelta(hours=7))
BOT_NAME     = "Freedom Aggressive Scalper"

# ── TELEGRAM ──────────────────────────────────────────────────────────────────
TOKEN_TG   = "8196511062:AAGyfWcRUk9uw_lc_aQgUW6vLyyRmgF1hcE"
CHAT_ID_TG = "-1003660980986"
TOPIC_ID   = 18

# ── COMPOUND LOT AGRESIF ──────────────────────────────────────────────────────
# Semakin besar balance → lot naik otomatis
# Mulai 0.01 di $14, naik terus seiring profit
RISK_PCT   = 3.0     # 3% per trade — agresif
MIN_LOT    = 0.01
MAX_LOT    = 5.0     # Batas lot tinggi untuk growth maksimal

# ── SCALP PARAMETERS ──────────────────────────────────────────────────────────
ATR_PERIOD  = 7      # ATR cepat untuk M1
SL_MULT     = 0.8    # SL ketat = 0.8 × ATR
TP_MULT     = 1.8    # TP = 1.8 × ATR → RR 2.25:1
MAX_SPREAD  = 50     # Tolak spread ekstrem saja
EMA_FAST    = 5
EMA_SLOW    = 13

# ── BREAKEVEN ─────────────────────────────────────────────────────────────────
BE_TRIGGER  = 0.6    # Breakeven super cepat di 0.6 × SL
TRAIL_MULT  = 0.5    # Trail distance = 0.5 × ATR (ketat, lock profit cepat)

# ── STATE ─────────────────────────────────────────────────────────────────────
trade_states = {}
last_candle  = None

# ══════════════════════════════════════════════════════════════════════════════

def tg(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN_TG}/sendMessage",
            json={"chat_id": CHAT_ID_TG, "message_thread_id": TOPIC_ID,
                  "text": msg, "parse_mode": "Markdown"},
            timeout=5
        )
    except:
        pass

def connect():
    if not mt5.initialize():
        print(f"❌ {mt5.last_error()}"); return False
    if not mt5.login(MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER):
        print(f"❌ Login gagal: {mt5.last_error()}"); mt5.shutdown(); return False
    a = mt5.account_info()
    print(f"✅ {a.login} | {a.name} | ${a.balance:.2f}")
    return True

def get_bars(n=30):
    r = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, n)
    if r is None or len(r) < 5: return None
    df = pd.DataFrame(r)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df['ema_fast'] = df['close'].ewm(span=EMA_FAST, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=EMA_SLOW, adjust=False).mean()
    return df

def get_atr(df):
    h, l, c = df['high'].values, df['low'].values, df['close'].values
    tr = [max(h[i]-l[i], abs(h[i]-c[i-1]), abs(l[i]-c[i-1]))
          for i in range(1, len(c))]
    p = ATR_PERIOD
    return float(np.mean(tr[-p:])) if len(tr) >= p else float(np.mean(tr)) if tr else 1.0

def calc_lot(sl_dist):
    """Compound lot — naik otomatis seiring balance tumbuh"""
    acc = mt5.account_info()
    sym = mt5.symbol_info(SYMBOL)
    if not acc or not sym: return MIN_LOT
    risk   = acc.balance * (RISK_PCT / 100.0)
    lot    = risk / (sl_dist * sym.trade_contract_size)
    step   = sym.volume_step or 0.01
    lot    = round(round(lot / step) * step, 2)
    return max(sym.volume_min, min(lot, min(MAX_LOT, sym.volume_max)))

# ══════════════════════════════════════════════════════════════════════════════
# SINYAL — SETIAP CANDLE M1
# ══════════════════════════════════════════════════════════════════════════════

def get_signal(df):
    """
    Setiap candle M1 close:
    BIRU  (close > open) + EMA fast > EMA slow → BUY
    MERAH (close < open) + EMA fast < EMA slow → SELL
    Tidak ada filter session, tidak ada filter hari.
    """
    tick = mt5.symbol_info_tick(SYMBOL)
    sym  = mt5.symbol_info(SYMBOL)
    if not tick or not sym: return None

    spread = (tick.ask - tick.bid) / sym.point
    if spread > MAX_SPREAD:
        print(f"  ⚠️  Spread {spread:.0f} pts. Lewati candle ini.")
        return None

    # Pakai candle yang baru close (index -2, karena -1 masih terbentuk)
    c     = df.iloc[-2]
    atr_v = get_atr(df)
    ef    = df['ema_fast'].iloc[-2]
    es    = df['ema_slow'].iloc[-2]

    bull = c['close'] > c['open']
    bear = c['close'] < c['open']

    if bull and ef >= es:
        entry   = tick.ask
        sl_dist = atr_v * SL_MULT
        tp_dist = atr_v * TP_MULT
        return {"dir": "BUY",  "entry": entry,
                "sl": entry - sl_dist, "tp": entry + tp_dist,
                "sl_dist": sl_dist, "atr": atr_v,
                "candle_size": abs(c['close']-c['open']),
                "spread": spread}

    if bear and ef <= es:
        entry   = tick.bid
        sl_dist = atr_v * SL_MULT
        tp_dist = atr_v * TP_MULT
        return {"dir": "SELL", "entry": entry,
                "sl": entry + sl_dist, "tp": entry - tp_dist,
                "sl_dist": sl_dist, "atr": atr_v,
                "candle_size": abs(c['close']-c['open']),
                "spread": spread}

    return None

# ══════════════════════════════════════════════════════════════════════════════
# ORDER
# ══════════════════════════════════════════════════════════════════════════════

def place(sig):
    digits = mt5.symbol_info(SYMBOL).digits
    lot    = calc_lot(sig['sl_dist'])
    otype  = mt5.ORDER_TYPE_BUY if sig['dir'] == "BUY" else mt5.ORDER_TYPE_SELL

    r = mt5.order_send({
        "action":       mt5.TRADE_ACTION_DEAL,
        "symbol":       SYMBOL,
        "volume":       lot,
        "type":         otype,
        "price":        round(sig['entry'], digits),
        "sl":           round(sig['sl'], digits),
        "tp":           round(sig['tp'], digits),
        "deviation":    30,
        "magic":        MAGIC,
        "comment":      "FSA",
        "type_time":    mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    })

    if r and r.retcode == mt5.TRADE_RETCODE_DONE:
        acc = mt5.account_info()
        rr  = sig['atr'] * TP_MULT / max(sig['atr'] * SL_MULT, 0.001)
        trade_states[r.order] = {
            "entry":    sig['entry'],
            "sl_dist":  sig['sl_dist'],
            "atr":      sig['atr'],
            "direction": sig['dir'],
            "trail_dist": sig['atr'] * TRAIL_MULT,
            "be_done":  False,
            "trail_on": False,
            "tp":       sig['tp'],
        }
        icon = "🟢" if sig['dir'] == "BUY" else "🔴"
        msg  = (
            f"{icon} *{sig['dir']} {SYMBOL}*\n"
            f"💵 `{sig['entry']:.2f}`  Lot: `{lot}`\n"
            f"🛑 SL `{sig['sl']:.2f}` → 🏆 TP `{sig['tp']:.2f}`\n"
            f"📐 RR `{rr:.1f}:1` | Spread `{sig['spread']:.0f}`\n"
            f"💰 Bal `${acc.balance:.2f}`  Eq `${acc.equity:.2f}`\n"
            f"_{datetime.now(WIB).strftime('%H:%M:%S WIB')}_"
        )
        tg(msg)
        print(f"  ✅ #{r.order} {sig['dir']} @ {sig['entry']:.2f} | "
              f"SL:{sig['sl']:.2f} TP:{sig['tp']:.2f} | Lot:{lot:.2f}")
        return True
    else:
        err = {10004:"Requote",10013:"SL terlalu dekat",
               10014:"Lot terlalu kecil",10019:"Saldo kurang"}
        code = r.retcode if r else 0
        print(f"  ❌ {err.get(code, f'retcode={code}')}")
        return False

# ══════════════════════════════════════════════════════════════════════════════
# BREAKEVEN & TRAILING (tetap ada — ini bukan proteksi, ini PROFIT LOCK)
# ══════════════════════════════════════════════════════════════════════════════

def manage():
    pos = mt5.positions_get(magic=MAGIC)
    if not pos: return

    for p in pos:
        tk  = p.ticket
        d   = "BUY" if p.type == 0 else "SELL"
        e   = p.price_open
        sl  = p.sl
        tp  = p.tp
        now = p.price_current
        dg  = mt5.symbol_info(p.symbol).digits

        st = trade_states.get(tk)
        if not st:
            sl_d = abs(e-sl) if sl>0 else 2.0
            trade_states[tk] = {
                "entry":e,"sl_dist":sl_d,"atr":sl_d,
                "direction":d,"be_done":False,"trail_on":False,
                "trail_dist":sl_d*TRAIL_MULT,"tp":tp
            }
            st = trade_states[tk]

        profit = (now-e) if d=="BUY" else (e-now)
        sl_d   = st['sl_dist']
        new_sl = None

        # Breakeven cepat
        if not st['be_done'] and profit >= sl_d * BE_TRIGGER:
            buf = st['atr'] * 0.03
            be  = (e+buf) if d=="BUY" else (e-buf)
            if (d=="BUY" and be>(sl or 0)) or (d=="SELL" and (be<sl or sl==0)):
                new_sl = be
                st['be_done'] = True
                print(f"  🔒 #{tk} BE @ {be:.{dg}f}")
                tg(f"🔒 BE #{tk} {d} — profit terkunci!")

        # Trailing
        if st['be_done']:
            if not st['trail_on'] and profit >= sl_d:
                st['trail_on'] = True
            if st['trail_on']:
                td = st['trail_dist']
                if d=="BUY":
                    ideal = now-td
                    if ideal>(sl or 0) and (new_sl is None or ideal>new_sl):
                        new_sl = ideal
                else:
                    ideal = now+td
                    if (ideal<sl or sl==0) and (new_sl is None or ideal<new_sl):
                        new_sl = ideal

        if new_sl:
            r = mt5.order_send({
                "action":mt5.TRADE_ACTION_SLTP,"symbol":p.symbol,
                "position":tk,"sl":round(new_sl,dg),"tp":round(tp,dg)
            })
            if r and r.retcode==mt5.TRADE_RETCODE_DONE:
                print(f"  🔧 #{tk} SL→{new_sl:.{dg}f}")

# ══════════════════════════════════════════════════════════════════════════════
# MAIN LOOP
# ══════════════════════════════════════════════════════════════════════════════

def run():
    global last_candle

    print(f"\n{'═'*55}")
    print(f"  🔥  {BOT_NAME}")
    print(f"  Mode   : Setiap candle M1 close → analisa → order")
    print(f"  Lot    : Compound {RISK_PCT}% per trade (auto naik)")
    print(f"  SL/TP  : ATR {SL_MULT}× / {TP_MULT}× (RR ~{TP_MULT/SL_MULT:.1f}:1)")
    print(f"  Proteksi: NONE — pure aggressive mode")
    print(f"{'═'*55}\n")

    if not connect(): return

    acc = mt5.account_info()
    tg(
        f"🔥 *{BOT_NAME}* ONLINE\n"
        f"`{acc.login}` | `{MT5_SERVER}`\n"
        f"💰 Balance: `${acc.balance:.2f}`\n"
        f"⚡ Mode: *AGGRESSIVE — setiap candle M1*\n"
        f"📐 Risk: `{RISK_PCT}%/trade` compound\n"
        f"⚠️ Tanpa drawdown limit — full gas!"
    )

    last_mgmt = 0
    trade_count = 0

    while True:
        try:
            # Manage BE & trail tiap 3 detik
            if time.time() - last_mgmt >= 3:
                manage()
                last_mgmt = time.time()

            df = get_bars(30)
            if df is None:
                time.sleep(1); continue

            current_ts = df['time'].iloc[-1]

            # Candle baru terbentuk = candle sebelumnya baru close
            if last_candle != current_ts:
                last_candle = current_ts

                now  = datetime.now(WIB)
                c    = df.iloc[-2]
                clr  = "🔵" if c['close'] > c['open'] else "🔴"
                body = abs(c['close'] - c['open'])
                rng  = c['high'] - c['low']
                bpct = f"{body/rng*100:.0f}%" if rng > 0 else "-"

                acc = mt5.account_info()
                pos = mt5.positions_get(magic=MAGIC) or []
                fl  = sum(p.profit for p in pos)

                print(f"\n[{now.strftime('%H:%M:%S')}] {clr} | Body:{bpct} | "
                      f"Bal:${acc.balance:.2f} Eq:${acc.equity:.2f} Float:${fl:.2f} | "
                      f"Trades:{trade_count}")

                # Jika ada posisi terbuka, tidak entry baru
                if len(pos) >= 1:
                    print(f"  ⏭️  Posisi terbuka ({len(pos)}). Tunggu close.")
                    time.sleep(1); continue

                sig = get_signal(df)
                if sig:
                    ok = place(sig)
                    if ok:
                        trade_count += 1
                else:
                    ef = df['ema_fast'].iloc[-2]
                    es = df['ema_slow'].iloc[-2]
                    print(f"  ─ Skip | EMA5:{ef:.2f} EMA13:{es:.2f} — "
                          f"{'EMA searah tidak terpenuhi' if ef==es else 'Arah tidak sesuai EMA'}")

            time.sleep(1)

        except KeyboardInterrupt:
            print("\n⛔ Dihentikan.")
            mt5.shutdown(); break
        except Exception as e:
            print(f"❌ {e}")
            time.sleep(5)
            if not mt5.account_info():
                connect()

if __name__ == "__main__":
    run()
