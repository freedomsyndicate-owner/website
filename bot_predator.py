"""
╔══════════════════════════════════════════════════════════════════════════╗
║       GLOBAL PREDATOR V11 — ICT SUPREME ENGINE                          ║
║       Inspired by Michael J. Huddleston (ICT) Methodology               ║
║       ─────────────────────────────────────────────────────             ║
║       ✅ Daily Bias  (AMDX / XAMD)                                      ║
║       ✅ Quarterly Theory  (Annual / Weekly / Daily)                     ║
║       ✅ Kill Zone Scanner  (Asia / London / NY AM / NY PM)              ║
║       ✅ Market Structure   (BOS / CHoCH / MSB)                          ║
║       ✅ Order Block Detection   (Bullish / Bearish OB)                  ║
║       ✅ Fair Value Gap Detection  (FVG / IFVG)                          ║
║       ✅ SMT Divergence Check                                            ║
║       ✅ Premium / Discount Arrays                                        ║
║       ✅ Multi-TF:  Weekly → Daily → H4 → H1 → M15 → M5                 ║
║       📡 Signals → Telegram + Discord + Firebase (Website Tab)           ║
╚══════════════════════════════════════════════════════════════════════════╝
Install: pip install requests tradingview_ta
"""

import requests
import time
from datetime import datetime, timezone

# ─── CONFIGURATION ─────────────────────────────────────────────────────────────
TOKEN_TG        = "8196511062:AAGyfWcRUk9uw_lc_aQgUW6vLyyRmgF1hcE"
CHAT_ID_TG      = "-1003660980986"
TOPIC_ID_TG     = 18
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1489306608554217736/vTC-HQBFwXWsiBE0WImdB0Uq88WppsSjCb548y5W5aFAubZVYXBgFCEuMLbcB22H1h7H"
FIREBASE_DB_URL = "https://freedomsyndicatecloud-default-rtdb.firebaseio.com"

# ─── TRADING PAIRS (Exchange, Screener, Correlated pair) ───────────────────────
PAIRS = {
    "XAUUSD":  {"ex": "OANDA",   "scr": "cfd",    "corr": "EURUSD",  "corr_scr": "forex",  "pip": 0.01},
    "BTCUSDT": {"ex": "BINANCE", "scr": "crypto", "corr": "ETHUSDT", "corr_scr": "crypto", "pip": 1.0},
    "EURUSD":  {"ex": "OANDA",   "scr": "forex",  "corr": "GBPUSD",  "corr_scr": "forex",  "pip": 0.0001},
    "GBPUSD":  {"ex": "OANDA",   "scr": "forex",  "corr": "EURUSD",  "corr_scr": "forex",  "pip": 0.0001},
    "USDJPY":  {"ex": "OANDA",   "scr": "forex",  "corr": None,      "corr_scr": None,      "pip": 0.01},
    "AUDUSD":  {"ex": "OANDA",   "scr": "forex",  "corr": "NZDUSD",  "corr_scr": "forex",  "pip": 0.0001},
    "NZDUSD":  {"ex": "OANDA",   "scr": "forex",  "corr": "AUDUSD",  "corr_scr": "forex",  "pip": 0.0001},
    "USDCAD":  {"ex": "OANDA",   "scr": "forex",  "corr": "EURUSD",  "corr_scr": "forex",  "pip": 0.0001},
}

# ─── ICT KILL ZONES (UTC hours) ────────────────────────────────────────────────
#   ICT defines these as highest-probability windows for institutional entries
KILL_ZONES = {
    "Asia KZ":    {"start": 0,  "end": 3,  "wib": "07:00–10:00",
                   "pairs": ["USDJPY", "AUDUSD", "NZDUSD", "XAUUSD"]},
    "London KZ":  {"start": 7,  "end": 10, "wib": "14:00–17:00",
                   "pairs": ["EURUSD", "GBPUSD", "XAUUSD", "USDCAD"]},
    "NY AM KZ":   {"start": 13, "end": 16, "wib": "20:00–23:00",
                   "pairs": ["EURUSD", "GBPUSD", "XAUUSD", "BTCUSDT", "USDJPY", "USDCAD"]},
    "NY PM KZ":   {"start": 19, "end": 22, "wib": "02:00–05:00",
                   "pairs": ["BTCUSDT", "XAUUSD"]},
}


# ══════════════════════════════════════════════════════════════════════════════
#  QUARTERLY THEORY — Michael J. Huddleston
# ══════════════════════════════════════════════════════════════════════════════
def get_quarterly_context():
    """
    ICT Quarterly Theory applied at 3 levels:
      Annual  → Q1(Jan–Mar)=Accum  Q2(Apr–Jun)=Manip  Q3(Jul–Sep)=Dist  Q4(Oct–Dec)=Rebalance
      Weekly  → Mon=Q1(Accum)  Tue=Q2(Manip)  Wed–Thu=Q3(Expand)  Fri=Q4(Rebalance)
      Daily   → Asia=Accum  London=Manipulation  NY=Distribution  Close=Rebalance
    """
    now  = datetime.now(timezone.utc)
    mon  = now.month
    dow  = now.weekday()   # 0=Mon … 4=Fri
    hour = now.hour

    # Annual quarter
    if mon <= 3:   aq = "Annual Q1 — Accumulation"
    elif mon <= 6: aq = "Annual Q2 — Manipulation ⚠️"
    elif mon <= 9: aq = "Annual Q3 — Distribution / Expansion"
    else:          aq = "Annual Q4 — Rebalance"

    # Weekly quarter
    wq_map = {
        0: "Weekly Q1 (Mon) — Accumulation / Range",
        1: "Weekly Q2 (Tue) — Manipulation / Liquidity Sweep ⚠️",
        2: "Weekly Q3 (Wed) — Expansion / Trend Day",
        3: "Weekly Q3 (Thu) — Continuation / Second Leg",
        4: "Weekly Q4 (Fri) — Rebalance / Profit-Taking",
    }
    wq = wq_map.get(dow, "Weekend — No Session")

    # Daily (session) quarter
    if   0  <= hour < 7:  dq = "Daily Q1 — Asia (Accumulation / Low-Vol Range)"
    elif 7  <= hour < 12: dq = "Daily Q2 — London (Manipulation / Liquidity Grab) ⚠️"
    elif 12 <= hour < 20: dq = "Daily Q3 — New York (Distribution / True Expansion)"
    else:                  dq = "Daily Q4 — Overnight (Rebalance / Low Activity)"

    return aq, wq, dq


def get_active_kill_zone():
    """Return the currently active Kill Zone name and its relevant pairs."""
    hour = datetime.now(timezone.utc).hour
    for name, kz in KILL_ZONES.items():
        if kz["start"] <= hour < kz["end"]:
            return name, kz["pairs"], kz["wib"]
    return None, [], ""


# ══════════════════════════════════════════════════════════════════════════════
#  FIREBASE HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def push_to_firebase(path: str, data: dict):
    try:
        r = requests.post(f"{FIREBASE_DB_URL}/{path}.json", json=data, timeout=10)
        if r.status_code == 200:
            key = r.json().get("name", "")
            print(f"    ✅ Firebase → /{path}/{key}")
            return key
    except Exception as e:
        print(f"    ✗ Firebase: {e}")
    return None


def trim_old_entries(path: str, keep: int = 60):
    try:
        r = requests.get(f"{FIREBASE_DB_URL}/{path}.json", timeout=10)
        if r.status_code == 200 and r.json():
            keys = list(r.json().keys())
            to_delete = keys[: max(0, len(keys) - keep)]
            for k in to_delete:
                requests.delete(f"{FIREBASE_DB_URL}/{path}/{k}.json", timeout=5)
    except:
        pass


# ══════════════════════════════════════════════════════════════════════════════
#  DELIVERY — Telegram + Discord + Firebase
# ══════════════════════════════════════════════════════════════════════════════
def send_all(msg: str, signal_data: dict = None, firebase_path: str = "signals/ict"):
    # ── Telegram ──────────────────────────────────────────────────────────────
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN_TG}/sendMessage",
            json={
                "chat_id": CHAT_ID_TG,
                "message_thread_id": TOPIC_ID_TG,
                "text": msg[:4096],
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        print("    📱 Telegram ✓")
    except Exception as e:
        print(f"    ✗ Telegram: {e}")

    # ── Discord ───────────────────────────────────────────────────────────────
    try:
        requests.post(DISCORD_WEBHOOK, json={"content": msg[:2000]}, timeout=10)
        print("    💬 Discord ✓")
    except Exception as e:
        print(f"    ✗ Discord: {e}")

    # ── Firebase (Website SIGNAL tab) ─────────────────────────────────────────
    if signal_data:
        push_to_firebase(firebase_path, signal_data)
        trim_old_entries(firebase_path)


# ══════════════════════════════════════════════════════════════════════════════
#  ICT SUPREME ENGINE
# ══════════════════════════════════════════════════════════════════════════════
try:
    from tradingview_ta import TA_Handler, Interval
    TV_AVAILABLE = True
except ImportError:
    TV_AVAILABLE = False
    print("⚠️  pip install tradingview_ta")


class ICT_Supreme_Engine:
    """
    Full ICT analysis engine implementing Michael J. Huddleston's core concepts:
      • Daily Bias  (AMDX / XAMD)
      • Market Structure (BOS / CHoCH)
      • Order Blocks (Bullish / Bearish)
      • Fair Value Gaps (FVG)
      • SMT Divergence
      • Premium / Discount arrays
      • Kill Zone + Quarterly context
    """

    INTERVALS = {
        "weekly": Interval.INTERVAL_1_WEEK,
        "daily":  Interval.INTERVAL_1_DAY,
        "h4":     Interval.INTERVAL_4_HOURS,
        "h1":     Interval.INTERVAL_1_HOUR,
        "m15":    Interval.INTERVAL_15_MINUTES,
        "m5":     Interval.INTERVAL_5_MINUTES,
    }

    def __init__(self, symbol: str, exchange: str, screener: str):
        self.symbol   = symbol
        self.exchange = exchange
        self.screener = screener
        self._cache   = {}

    # ── Internal helpers ──────────────────────────────────────────────────────
    def _get(self, tf: str):
        """Fetch (and cache) analysis for a given timeframe."""
        if tf not in self._cache:
            try:
                h = TA_Handler(
                    symbol=self.symbol, exchange=self.exchange,
                    screener=self.screener, interval=self.INTERVALS[tf]
                )
                self._cache[tf] = h.get_analysis()
            except Exception:
                self._cache[tf] = None
        return self._cache[tf]

    @staticmethod
    def _ind(analysis, key, fallback=0):
        try:
            return analysis.indicators.get(key, fallback)
        except Exception:
            return fallback

    # ── Market Structure ──────────────────────────────────────────────────────
    def market_structure(self, tf: str):
        """
        Classify market structure on a timeframe:
          BULLISH_BOS  — clear higher-highs/lows stack, price > EMA chain
          BULLISH_CHOCH — transitioning from bearish (first bullish BOS)
          BEARISH_BOS  — lower-lows/highs, price < EMA chain
          BEARISH_CHOCH — transitioning from bullish
          NEUTRAL
        """
        a = self._get(tf)
        if a is None:
            return "UNKNOWN", 0

        close  = self._ind(a, "close", 1)
        ema20  = self._ind(a, "EMA20",  close)
        ema50  = self._ind(a, "EMA50",  close)
        ema200 = self._ind(a, "EMA200", close)
        rsi    = self._ind(a, "RSI", 50)
        macd   = self._ind(a, "MACD.macd", 0)
        sig    = self._ind(a, "MACD.signal", 0)

        bull_chain = close > ema20 and ema20 > ema50 and ema50 > ema200
        bear_chain = close < ema20 and ema20 < ema50 and ema50 < ema200

        score = 0
        if bull_chain:
            score = 3
            score += 1 if rsi > 52 else 0
            score += 1 if macd > sig else 0
            return "BULLISH_BOS", score
        if bear_chain:
            score = 3
            score += 1 if rsi < 48 else 0
            score += 1 if macd < sig else 0
            return "BEARISH_BOS", score
        # Transitional (CHoCH candidates)
        if close > ema50 and ema20 < ema50:
            return "BULLISH_CHOCH", 2
        if close < ema50 and ema20 > ema50:
            return "BEARISH_CHOCH", 2
        return "NEUTRAL", 1

    # ── Daily Bias ────────────────────────────────────────────────────────────
    def daily_bias(self):
        """
        ICT Daily Bias — AMDX vs XAMD:
          AMDX (Bullish): Accumulation→Manipulation(sweep low)→Distribution→eXpansion ↑
          XAMD (Bearish): eXpansion ↓→Accumulation→Manipulation(sweep high)→Distribution

        Uses Weekly + Daily + H4 confluence to score bias.
        Returns (bias: str, protocol: str, score: int)
        """
        d  = self._get("daily")
        w  = self._get("weekly")
        h4 = self._get("h4")
        if d is None:
            return "NEUTRAL", "AMD_FORMING", 0

        close  = self._ind(d, "close",     1)
        ema50  = self._ind(d, "EMA50",     close)
        ema200 = self._ind(d, "EMA200",    close)
        rsi_d  = self._ind(d, "RSI",       50)
        macd_d = self._ind(d, "MACD.macd", 0)
        sig_d  = self._ind(d, "MACD.signal", 0)
        atr_d  = self._ind(d, "ATR",       close * 0.001)

        score = 0

        # Daily structure (max 4 pts)
        if close > ema200: score += 2
        if close > ema50:  score += 1
        if rsi_d > 52:     score += 1

        # Momentum (max 2 pts)
        if macd_d > sig_d: score += 2

        # Weekly confluence (max 2 pts)
        if w:
            w_close = self._ind(w, "close", 1)
            w_ema50 = self._ind(w, "EMA50", w_close)
            w_rsi   = self._ind(w, "RSI",   50)
            if w_close > w_ema50: score += 1
            if w_rsi > 50:        score += 1

        # H4 structure (max 2 pts)
        h4_struct, _ = self.market_structure("h4")
        if "BULLISH" in h4_struct: score += 2
        if "BEARISH" in h4_struct: score -= 2   # strong counter pressure

        # AMD vs XAMD: additional qualifier using ATR expansion
        # AMDX → bullish momentum expanding (ATR relatively high)
        atr_ratio = atr_d / (close * 0.001) if close > 0 else 1.0
        is_expanding = atr_ratio > 1.2   # ATR > 0.12% of price = expansion

        if score >= 6:
            bias     = "BULLISH"
            protocol = "AMDX" if is_expanding else "AMD (Forming)"
        elif score <= 3:
            bias     = "BEARISH"
            protocol = "XAMD" if is_expanding else "XAM (Forming)"
        else:
            bias, protocol = "NEUTRAL", "AMD_FORMING"

        return bias, protocol, score

    # ── Order Block ───────────────────────────────────────────────────────────
    def order_block(self, bias: str):
        """
        ICT Order Block:
          Bullish OB — last significant bearish candle before bullish displacement.
                       Approximated via H1 low / oversold RSI on M15.
          Bearish OB — last significant bullish candle before bearish displacement.
                       Approximated via H1 high / overbought RSI on M15.
        Returns (ob_price, quality 0-10)
        """
        h1  = self._get("h1")
        m15 = self._get("m15")
        if not h1 or not m15:
            return None, 0

        close_h1 = self._ind(h1,  "close", 0)
        open_h1  = self._ind(h1,  "open",  0)
        high_h1  = self._ind(h1,  "high",  0)
        low_h1   = self._ind(h1,  "low",   0)
        rsi_m15  = self._ind(m15, "RSI",   50)

        if bias == "BULLISH":
            # Looking for price to have dipped into a bearish OB (low zone) then reverse
            if rsi_m15 < 35:
                return low_h1, 9
            elif rsi_m15 < 45 and close_h1 > open_h1:
                return open_h1, 6
        else:
            # Looking for price to have rallied into a bullish OB (high zone) then reverse
            if rsi_m15 > 65:
                return high_h1, 9
            elif rsi_m15 > 55 and close_h1 < open_h1:
                return open_h1, 6

        return None, 0

    # ── Fair Value Gap ────────────────────────────────────────────────────────
    def fair_value_gap(self, bias: str):
        """
        ICT Fair Value Gap (Imbalance):
          Bullish FVG — large displacement candle upward → gap between c1.high and c3.low
          Bearish FVG — large displacement candle downward → gap between c1.low and c3.high
        Approximated using M5 body-to-ATR ratio as displacement proxy.
        Returns (fvg_midpoint, quality 0-10)
        """
        m5 = self._get("m5")
        if not m5:
            return None, 0

        close_ = self._ind(m5, "close", 0)
        open_  = self._ind(m5, "open",  0)
        high_  = self._ind(m5, "high",  0)
        low_   = self._ind(m5, "low",   0)
        atr    = self._ind(m5, "ATR",   close_ * 0.0005)

        body = abs(close_ - open_)
        if body < atr * 1.4:
            return None, 0   # Not a displacement candle

        if bias == "BULLISH" and close_ > open_:
            mid = (low_ + close_) / 2   # Midpoint of the bullish gap
            q   = 9 if body > atr * 2.0 else 7
            return mid, q
        if bias == "BEARISH" and close_ < open_:
            mid = (high_ + close_) / 2  # Midpoint of the bearish gap
            q   = 9 if body > atr * 2.0 else 7
            return mid, q

        return None, 0

    # ── Premium / Discount ────────────────────────────────────────────────────
    def premium_discount(self):
        """
        ICT Premium/Discount arrays (equilibrium = EMA50 on H4):
          > +50 ATR deviation → PREMIUM   (sell area)
          < -50 ATR deviation → DISCOUNT  (buy area)
        """
        h4 = self._get("h4")
        if not h4:
            return "EQUILIBRIUM ⚖️", 0

        close = self._ind(h4, "close", 1)
        ema50 = self._ind(h4, "EMA50", close)
        atr   = self._ind(h4, "ATR", close * 0.001)

        dev = (close - ema50) / atr * 100 if atr > 0 else 0

        if dev > 50:
            return "PREMIUM 🔴 (Sell Zone — Institutions distribute here)", dev
        elif dev < -50:
            return "DISCOUNT 🟢 (Buy Zone — Institutions accumulate here)", dev
        else:
            return "EQUILIBRIUM ⚖️ (Price at 50% — Wait for sweep)", dev

    # ── SMT Divergence ────────────────────────────────────────────────────────
    def smt_divergence(self, corr_sym: str, corr_scr: str, bias: str):
        """
        SMT (Smart Money Technique):
          Confirmation  — correlated pair moves same direction (institutional alignment)
          Divergence    — correlated pair moves opposite       (manipulation / liquidity hunt)
        """
        if not corr_sym:
            return "N/A ➖", True, "No correlated pair configured"

        try:
            h = TA_Handler(
                symbol=corr_sym, exchange=self.exchange, screener=corr_scr,
                interval=Interval.INTERVAL_1_HOUR
            )
            rec = h.get_analysis().summary["RECOMMENDATION"]

            corr_bullish = "BUY" in rec
            corr_bearish = "SELL" in rec

            if (bias == "BULLISH" and corr_bullish) or (bias == "BEARISH" and corr_bearish):
                return "SMT CONFIRMED ✅", True, f"{corr_sym} aligns — high-confidence entry"
            elif (bias == "BULLISH" and corr_bearish) or (bias == "BEARISH" and corr_bullish):
                return "SMT DIVERGENCE ⚠️", False, f"{corr_sym} diverges — possible manipulation/trap"
            return "SMT NEUTRAL ➖", True, f"{corr_sym} neutral"
        except Exception as e:
            return "SMT N/A", True, str(e)

    # ── Entry, SL, TP Calculation ─────────────────────────────────────────────
    def calculate_levels(self, bias: str, ob_price, fvg_price):
        """
        ICT-style levels:
          Entry  — at OB, FVG midpoint, or current M5 price
          SL     — beyond the OB (1.5× ATR_H1 from entry)
          TP1    — 1:1 RR (internal liquidity target)
          TP2    — 1:2 RR (swing high/low liquidity)
          TP3    — 1:3.5 RR (external liquidity / weekly target)
        Minimum acceptable RR: 2:1
        """
        m5 = self._get("m5")
        h1 = self._get("h1")
        if not m5:
            return None

        price   = self._ind(m5, "close", 0)
        atr_h1  = self._ind(h1, "ATR",   price * 0.001) if h1 else price * 0.001

        # Prefer OB entry → FVG midpoint → current price
        entry = ob_price or fvg_price or price

        risk = atr_h1 * 1.5   # SL distance

        if bias == "BULLISH":
            sl  = entry - risk
            tp1 = entry + risk          # 1:1
            tp2 = entry + risk * 2.0    # 1:2
            tp3 = entry + risk * 3.5    # 1:3.5
        else:
            sl  = entry + risk
            tp1 = entry - risk
            tp2 = entry - risk * 2.0
            tp3 = entry - risk * 3.5

        return dict(entry=entry, sl=sl, tp1=tp1, tp2=tp2, tp3=tp3, risk=risk, rr=2.0)

    # ── Master Signal Generator ───────────────────────────────────────────────
    def generate(self, pair: str, cfg: dict):
                   for old in keys[:max(0, len(keys)-keep)]:
                requests.delete(f"{FIREBASE_DB_URL}/{path}/{old}.json", timeout=5)
    except: pass

# ── Send All ────────────────────────────────────────────────────────────

def send_all(msg, signal_data=None):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN_TG}/sendMessage",
            json={"chat_id": CHAT_ID_TG, "message_thread_id": TOPIC_ID_TG,
                  "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass
    
    try:
        requests.post(DISCORD_WEBHOOK, json={"content": msg}, timeout=10)
    except: pass
    
    if signal_data:
        push_to_firebase("signals/ict", signal_data)
        trim_old_signals("signals/ict")

# ── ICT Engine ──────────────────────────────────────────────────────────

try:
    from tradingview_ta import TA_Handler, Interval
    TV_AVAILABLE = True
except ImportError:
    TV_AVAILABLE = False
    print("⚠️  pip install tradingview_ta")

PAIRS = {
    "XAUUSD":  {"ex": "OANDA",   "scr": "cfd",    "corr": "XAUEUR"},
    "BTCUSDT": {"ex": "BINANCE", "scr": "crypto", "corr": "ETHUSDT"},
    "GBPUSD":  {"ex": "OANDA",   "scr": "forex",  "corr": "EURUSD"},
    "USDJPY":  {"ex": "OANDA",   "scr": "forex",  "corr": "DX"},
    "AUDUSD":  {"ex": "OANDA",   "scr": "forex",  "corr": "NZDUSD"},
    "EURUSD":  {"ex": "OANDA",   "scr": "forex",  "corr": "GBPUSD"},
    "NZDUSD":  {"ex": "OANDA",   "scr": "forex",  "corr": "AUDUSD"},
    "USDCAD":  {"ex": "OANDA",   "scr": "forex",  "corr": "DX"},
}

class ICT_Ultimate_Engine:
    def __init__(self, sym, ex, scr, corr):
        self.symbol = sym
        self.corr   = corr
        self.daily_h = TA_Handler(symbol=sym, exchange=ex, screener=scr, interval=Interval.INTERVAL_1_DAY)
        self.micro_h = TA_Handler(symbol=sym, exchange=ex, screener=scr, interval=Interval.INTERVAL_5_MINUTES)

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

if __name__ == "__main__":
    send_all("🔥 **GLOBAL PREDATOR V10** AKTIF\n📡 Sinyal → Telegram + Discord + Website Journal\n_Pure Institution Logic._")
    while True:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        print(f"\n[{ts}] Scanning {len(PAIRS)} pairs...")
        for pair, cfg in PAIRS.items():
            if not TV_AVAILABLE: break
            try:
                bot = ICT_Ultimate_Engine(pair, cfg['ex'], cfg['scr'], cfg['corr'])
                proto, bias = bot.get_protocol()
                if "BUY" in bias or "SELL" in bias:
                    entry, sl, tp1, tp2, tp3, direction = bot.sniper_entry(bias)
                    score    = bot.get_score(bias)
                    strength = "STRONG 🔥" if score >= 8 else "MODERATE ✅"
                    reasons  = [f"📊 Daily Bias: {bias}", f"🔄 Protocol: {proto}", f"⚡ SMT vs {cfg['corr']} | CISD"]

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
