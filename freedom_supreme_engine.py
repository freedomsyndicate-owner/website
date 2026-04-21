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

# Proxy Tor (Socks5) - Rotate identity
PROXIES = {'http': 'socks5://127.0.0.1:9150', 'https': 'socks5://127.0.0.1:9150'}

TOR_CONTROL_PORT = 9051  # Port control Tor untuk ganti IP
TOR_PASSWORD     = ""    # Kosongkan jika tidak ada password di torrc

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
]

def rotate_tor_ip():
    """Minta Tor ganti IP baru via Control Port"""
    try:
        import socket
        s = socket.socket()
        s.connect(('127.0.0.1', TOR_CONTROL_PORT))
        s.send(b'AUTHENTICATE "' + TOR_PASSWORD.encode() + b'"\r\n')
        s.recv(128)
        s.send(b'SIGNAL NEWNYM\r\n')
        s.recv(128)
        s.close()
        time.sleep(3)  # Tunggu IP baru aktif
        print("🔄 Tor IP rotated.")
    except Exception as e:
        print(f"⚠️ Tor rotate failed: {e}")

def get_headers():
    """Ambil random User-Agent header"""
    return {"User-Agent": random.choice(USER_AGENTS)}

# ─── PAIRS & IMPACT ─────────────────────────────────────────────────────────────
PAIRS = {
    "XAUUSD": {"ex": "OANDA", "scr": "cfd", "dec": 2},
    "GBPUSD": {"ex": "OANDA", "scr": "forex", "dec": 5},
    "EURUSD": {"ex": "OANDA", "scr": "forex", "dec": 5},
    "USDJPY": {"ex": "OANDA", "scr": "forex", "dec": 3},
    "BTCUSDT": {"ex": "BINANCE", "scr": "crypto", "dec": 2}
}

IMPACT_MAP = {"High": "🔴 HIGH", "Medium": "🟡 MEDIUM", "Low": "🟢 LOW"}

# ─── ANTI-SPAM TRACKER ──────────────────────────────────────────────────────────
sent_fundamentals = set()   # Simpan event ID yang sudah dikirim
last_signal_time  = {}      # Simpan waktu signal terakhir per pair

# ─── CORE ENGINE FUNCTIONS ──────────────────────────────────────────────────────

def get_killzone():
    """Logic ICT Killzones (WIB)"""
    hr = datetime.now(WIB).hour
    if 7 <= hr <= 10: return "ASIA KILLZONE"
    if 14 <= hr <= 17: return "LONDON KILLZONE"
    if 20 <= hr <= 23: return "NEW YORK KILLZONE"
    return "MACRO/OFF-SESSION"

def get_active_session():
    """Return sesi aktif: ASIA, LONDON, NEWYORK, atau OFF"""
    hr = datetime.now(WIB).hour
    if 7 <= hr <= 10:   return "ASIA"
    if 14 <= hr <= 17:  return "LONDON"
    if 20 <= hr <= 23:  return "NEWYORK"
    return "OFF"

def get_macro_window():
    """
    ICT Macro Windows (WIB) - 90 menit micro cycle
    Macro windows aktif: saat pasar cari likuiditas sebelum expansion
    """
    now = datetime.now(WIB)
    hr, mn = now.hour, now.minute
    total_min = hr * 60 + mn

    macros = [
        ((7*60+50),  (8*60+10),   "ASIA OPEN MACRO"),
        ((9*60+50),  (10*60+10),  "ASIA CLOSE MACRO"),
        ((14*60+50), (15*60+10),  "LONDON OPEN MACRO"),
        ((16*60+50), (17*60+10),  "LONDON CLOSE / NY PRE-MACRO"),
        ((20*60+50), (21*60+10),  "NEW YORK OPEN MACRO"),
        ((22*60+50), (23*60+10),  "NY LUNCH MACRO"),
    ]
    for start, end, label in macros:
        if start <= total_min <= end:
            return f"⏰ MACRO WINDOW AKTIF: {label}"

    # 90-menit micro cycle check
    cycle_starts = [7*60, 8*60+30, 10*60, 11*60+30, 14*60, 15*60+30, 17*60, 18*60+30, 20*60, 21*60+30, 23*60]
    for cs in cycle_starts:
        if cs <= total_min <= cs + 90:
            elapsed = total_min - cs
            if elapsed <= 20:   phase = "ACCUMULATION (awal cycle)"
            elif elapsed <= 60: phase = "MANIPULATION / JUDAS SWING"
            else:               phase = "DISTRIBUTION / EXPANSION"
            return f"🔄 90-MIN CYCLE ({elapsed}m): {phase}"

    return "📍 OFF-MACRO (Hindari entry baru)"

def get_daily_bias(bias_str, pair):
    """
    Tentukan Daily Bias ICT berdasarkan rekomendasi dan pair.
    BULLISH = expect harga ke Premium (atas PDH, equilibrium ke atas)
    BEARISH = expect harga ke Discount (bawah PDL, equilibrium ke bawah)
    """
    if "STRONG_BUY" in bias_str:
        db = "📈 BULLISH BIAS"
        detail = "HTF struktur bullish. Cari Discount Array (OB/FVG di bawah EQ) untuk BUY."
    elif "BUY" in bias_str:
        db = "📈 BULLISH BIAS (Moderate)"
        detail = "Struktur bullish lemah. Konfirmasi MSB pada LTF sebelum BUY."
    elif "STRONG_SELL" in bias_str:
        db = "📉 BEARISH BIAS"
        detail = "HTF struktur bearish. Cari Premium Array (OB/FVG di atas EQ) untuk SELL."
    elif "SELL" in bias_str:
        db = "📉 BEARISH BIAS (Moderate)"
        detail = "Struktur bearish lemah. Konfirmasi MSB pada LTF sebelum SELL."
    else:
        db = "⚖️ NEUTRAL / CONSOLIDATION"
        detail = "Market di equilibrium. Tunggu displacement sebelum entry."
    return db, detail

def get_ict_context(proto, direction, pair, bias_str="BUY"):
    """Logika Michael J. Huddleston (ICT) - Daily Bias + Macro + XAMD/AMDX"""
    session   = get_killzone()
    macro_win = get_macro_window()
    daily_bias, bias_detail = get_daily_bias(bias_str, pair)
    active_session = get_active_session()

    if proto == "AMDX":
        logic    = f"ICT {session} - AMDX (ACCUMULATION→MANIPULATION→DISTRIBUTION→EXPANSION)"
        analysis = (
            f"• *Phase:* MANIPULATION sedang berlangsung (Judas Swing)\n"
            f"• Likuiditas di sisi {pair} {'LOW' if direction=='BUY' else 'HIGH'} sedang disweep.\n"
            f"• Expect REJECTION kuat di HTF PD Array (OB/FVG/Breaker).\n"
            f"• Entry setelah konfirmasi displacement candle ke arah {direction}.\n"
            f"• *Sesi:* {active_session} — {'Volume tinggi, valid!' if active_session != 'OFF' else 'OFF sesi, hati-hati!'}"
        )
    else:
        logic    = f"ICT {session} - XAMD (EXPANSION PHASE)"
        analysis = (
            f"• *Phase:* EXPANSION — Market Structure Break (MSB) terkonfirmasi.\n"
            f"• Entry optimal pada FVG / Orderblock terdekat arah {direction}.\n"
            f"• Mengikuti Daily Bias: {daily_bias}.\n"
            f"• Hindari entry saat harga di {('Premium Zone (terlalu tinggi)' if direction=='BUY' else 'Discount Zone (terlalu rendah)')}.\n"
            f"• *Sesi:* {active_session} — {'Volume tinggi, valid!' if active_session != 'OFF' else 'OFF sesi, hati-hati!'}"
        )

    # Tambah info macro window
    analysis += f"\n• *Macro:* {macro_win}"
    analysis += f"\n• *Daily Bias Detail:* {bias_detail}"

    return logic, analysis

# ─── ICT SL/TP ENGINE ───────────────────────────────────────────────────────────

# Minimum SL distance per pair (dalam satuan price, bukan pip)
# XAUUSD: min $2.0 | Forex major: min 10 pip (0.00100) | USDJPY: min 10 pip (0.100) | BTC: min $150
PAIR_MIN_SL = {
    "XAUUSD":  2.00,
    "GBPUSD":  0.00100,
    "EURUSD":  0.00100,
    "USDJPY":  0.100,
    "BTCUSDT": 150.0,
}

# Maximum SL distance (terlalu lebar = entry buruk)
PAIR_MAX_SL = {
    "XAUUSD":  15.0,
    "GBPUSD":  0.00600,
    "EURUSD":  0.00600,
    "USDJPY":  0.600,
    "BTCUSDT": 1500.0,
}

def calculate_ict_sltp(pair, direction, entry, atr, indicators):
    """
    Kalkulasi SL/TP ICT proper:
    - SL: di balik swing high/low struktur (pakai Pivot High/Low dari indikator)
    - TP: ke liquidity target berikutnya (PDH/PDL atau RR 1:2 minimum, 1:3 ideal)
    - Validasi: SL tidak terlalu dekat (min pip) & tidak terlalu jauh (max pip)
    - RR filter: tolak signal jika RR < 1:2
    """
    min_sl = PAIR_MIN_SL.get(pair, atr * 0.5)
    max_sl = PAIR_MAX_SL.get(pair, atr * 5.0)

    # ── Cari Swing Low/High dari indikator Pivot ──────────────────────────────
    # TradingView TA menyediakan: Pivot.M.Classic.S1/S2/R1/R2 sebagai proxy level
    pivot_s1 = indicators.get('Pivot.M.Classic.S1')  # Support 1 = proxy swing low
    pivot_s2 = indicators.get('Pivot.M.Classic.S2')  # Support 2 = swing low lebih dalam
    pivot_r1 = indicators.get('Pivot.M.Classic.R1')  # Resistance 1 = proxy swing high
    pivot_r2 = indicators.get('Pivot.M.Classic.R2')  # Resistance 2 = swing high lebih jauh

    # Fallback jika pivot tidak tersedia
    if not pivot_s1: pivot_s1 = entry - (atr * 1.2)
    if not pivot_s2: pivot_s2 = entry - (atr * 2.0)
    if not pivot_r1: pivot_r1 = entry + (atr * 1.2)
    if not pivot_r2: pivot_r2 = entry + (atr * 2.0)

    if direction == "BUY":
        # ── SL: Di bawah swing low (S1), tambah buffer 10% ATR ──────────────
        raw_sl = pivot_s1 - (atr * 0.1)   # Sedikit di bawah S1 (OB/FVG buffer)
        sl_distance = entry - raw_sl

        # Validasi minimum SL distance (tidak terlalu dekat)
        if sl_distance < min_sl:
            raw_sl  = entry - min_sl       # Paksa minimum
            sl_distance = min_sl
            sl_note = f"⚠️ SL diperlebar ke minimum {min_sl}"
        elif sl_distance > max_sl:
            raw_sl  = entry - max_sl       # Terlalu jauh, pangkas
            sl_distance = max_sl
            sl_note = f"⚠️ SL dipersempit ke maksimum {max_sl}"
        else:
            sl_note = "✅ SL di bawah Swing Low / OB Zone"

        # ── TP: Ke liquidity target R1/R2, minimal RR 1:2 ──────────────────
        tp_rr2 = entry + (sl_distance * 2.0)   # Minimum RR 1:2
        tp_rr3 = entry + (sl_distance * 3.0)   # Target ideal RR 1:3

        # Pilih TP: pakai R1 jika lebih jauh dari RR 1:2, else pakai RR 1:3
        if pivot_r1 and pivot_r1 > tp_rr2:
            raw_tp  = pivot_r1
            tp_note = f"🎯 TP di Liquidity Target R1 (RR {(pivot_r1-entry)/sl_distance:.1f}:1)"
        elif pivot_r2 and pivot_r2 > tp_rr2:
            raw_tp  = pivot_r2
            tp_note = f"🎯 TP di Liquidity Target R2 (RR {(pivot_r2-entry)/sl_distance:.1f}:1)"
        else:
            raw_tp  = tp_rr3
            tp_note = "🎯 TP di RR 1:3 (ATR-based)"

    else:  # SELL
        # ── SL: Di atas swing high (R1), tambah buffer 10% ATR ──────────────
        raw_sl = pivot_r1 + (atr * 0.1)
        sl_distance = raw_sl - entry

        if sl_distance < min_sl:
            raw_sl      = entry + min_sl
            sl_distance = min_sl
            sl_note = f"⚠️ SL diperlebar ke minimum {min_sl}"
        elif sl_distance > max_sl:
            raw_sl      = entry + max_sl
            sl_distance = max_sl
            sl_note = f"⚠️ SL dipersempit ke maksimum {max_sl}"
        else:
            sl_note = "✅ SL di atas Swing High / OB Zone"

        tp_rr2 = entry - (sl_distance * 2.0)
        tp_rr3 = entry - (sl_distance * 3.0)

        if pivot_s1 and pivot_s1 < tp_rr2:
            raw_tp  = pivot_s1
            tp_note = f"🎯 TP di Liquidity Target S1 (RR {(entry-pivot_s1)/sl_distance:.1f}:1)"
        elif pivot_s2 and pivot_s2 < tp_rr2:
            raw_tp  = pivot_s2
            tp_note = f"🎯 TP di Liquidity Target S2 (RR {(entry-pivot_s2)/sl_distance:.1f}:1)"
        else:
            raw_tp  = tp_rr3
            tp_note = "🎯 TP di RR 1:3 (ATR-based)"

    # ── RR Validasi Final ────────────────────────────────────────────────────
    rr_actual = abs(raw_tp - entry) / max(abs(raw_sl - entry), 0.00001)

    if rr_actual < 2.0:
        # Signal buruk — RR terlalu rendah, tolak
        return None, None, None, None, f"❌ SIGNAL DITOLAK: RR {rr_actual:.1f}:1 < 2:1 minimum"

    rr_label = f"RR {rr_actual:.1f}:1 {'🔥 EXCELLENT' if rr_actual >= 3 else '✅ GOOD'}"
    zone_info = f"{sl_note}\n• {tp_note}\n• 📐 {rr_label}"

    return raw_sl, raw_tp, sl_distance, rr_actual, zone_info


def send_to_all(msg, category="signal", data=None):
    """Broadcast ke Telegram, Discord, dan Firebase"""

    # ── Telegram ────────────────────────────────────────────────────────────────
    token = TOKEN_TG_PREDATOR if category == "signal" else TOKEN_TG_SUPREME
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": CHAT_ID_TG, "message_thread_id": TOPIC_ID_GENERAL,
                  "text": msg, "parse_mode": "Markdown"},
            timeout=10
        )
        if not r.ok:
            print(f"⚠️ Telegram [{category}] error {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"❌ Telegram [{category}] exception: {e}")

    # ── Discord ─────────────────────────────────────────────────────────────────
    # Discord limit: 2000 char untuk content biasa → pakai Embed agar aman sampai 4096 char
    webhook = DISCORD_PREDATOR if category == "signal" else DISCORD_FUNDA

    # Pilih warna embed berdasarkan kategori & isi pesan
    if category == "signal":
        color = 0x00FF99 if "BUY" in msg else 0xFF4444   # Hijau = BUY, Merah = SELL
    else:
        # Fundamental: merah = HIGH, kuning = MEDIUM, hijau = LOW
        if "HIGH" in msg:   color = 0xFF0000
        elif "MEDIUM" in msg: color = 0xFFAA00
        else:               color = 0x00CC44

    # Bersihkan Telegram Markdown agar bisa dibaca di Discord
    discord_msg = (msg
        .replace("*", "**")        # Telegram *bold* → Discord **bold**
        .replace("`", "`")         # backtick tetap sama
    )

    # Potong jika masih terlalu panjang (embed description max 4096)
    if len(discord_msg) > 4096:
        discord_msg = discord_msg[:4090] + "\n..."

    embed_payload = {
        "embeds": [{
            "description": discord_msg,
            "color": color,
            "footer": {"text": f"Freedom Syndicate • {datetime.now(WIB).strftime('%H:%M WIB')}"}
        }]
    }

    try:
        r = requests.post(webhook, json=embed_payload, timeout=10)
        if not r.ok:
            print(f"⚠️ Discord [{category}] error {r.status_code}: {r.text[:200]}")
        else:
            print(f"✅ Discord [{category}] terkirim.")
    except Exception as e:
        print(f"❌ Discord [{category}] exception: {e}")

    # ── Web (Firebase) ──────────────────────────────────────────────────────────
    if data:
        path = "signals/ict" if category == "signal" else "signals/fundamental"
        try:
            r = requests.post(f"{FIREBASE_URL}/{path}.json", json=data, timeout=10)
            if not r.ok:
                print(f"⚠️ Firebase [{category}] error {r.status_code}: {r.text[:100]}")
        except Exception as e:
            print(f"❌ Firebase [{category}] exception: {e}")

# ─── MAIN RUNNER ────────────────────────────────────────────────────────────────

def run_freedom_engine():
    print(f"🚀 {BOT_NAME} SUPREME ENGINE STARTING...")
    
    while True:
        try:
            # 1. CEK FUNDAMENTAL (Radar) — ANTI SPAM: hanya kirim 1x per event
            funda_url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
            try:
                events = requests.get(funda_url, proxies=PROXIES, headers=get_headers(), timeout=15).json()
            except Exception as e:
                print(f"❌ Funda fetch error: {e}")
                rotate_tor_ip()
                events = []

            for ev in events:
                ev_dt = datetime.fromisoformat(ev['date']).astimezone(UTC)
                # Buat unique ID per event supaya tidak spam
                ev_id = f"{ev.get('title','')}-{ev.get('date','')}-{ev.get('country','')}"
                # Cek: 1 jam ke depan DAN belum pernah dikirim
                time_diff = (ev_dt - datetime.now(UTC)).total_seconds()
                if 0 <= time_diff <= 3600 and ev_id not in sent_fundamentals:
                    impact = IMPACT_MAP.get(ev['impact'])
                    if impact:
                        news_msg = f"⚠️ *FUNDAMENTAL ALERT* ⚠️\n━━━━━━━━━━\n📋 {ev['title']}\n🏛 Currency: {ev['country']}\n🔥 Impact: {impact}\n🕐 Time: {ev_dt.astimezone(WIB).strftime('%H:%M WIB')}"
                        send_to_all(news_msg, category="news", data=ev)
                        sent_fundamentals.add(ev_id)  # Tandai sudah dikirim

            # Bersihkan tracker event lama (> 2 jam lalu) agar tidak penuh memory
            now_utc = datetime.now(UTC)
            for ev in (events or []):
                ev_dt = datetime.fromisoformat(ev['date']).astimezone(UTC)
                ev_id = f"{ev.get('title','')}-{ev.get('date','')}-{ev.get('country','')}"
                if (now_utc - ev_dt).total_seconds() > 7200:
                    sent_fundamentals.discard(ev_id)

            # 2. ANALISIS SIGNAL (Predator) — hanya saat sesi aktif
            active_session = get_active_session()
            if active_session == "OFF":
                print(f"[{datetime.now(WIB).strftime('%H:%M:%S')}] OFF Session. Skip signal scan.")
                time.sleep(600)
                continue

            for pair, cfg in PAIRS.items():
                try:
                    handler = TA_Handler(symbol=pair, exchange=cfg['ex'], screener=cfg['scr'], 
                                         interval=Interval.INTERVAL_5_MINUTES, proxies=PROXIES)
                    analysis = handler.get_analysis()
                    bias = analysis.summary['RECOMMENDATION']
                    
                    if "BUY" in bias or "SELL" in bias:
                        direction = "BUY" if "BUY" in bias else "SELL"
                        entry = analysis.indicators.get('close') or analysis.indicators.get('Pivot.M.Classic.Middle')
                        atr   = analysis.indicators.get('ATR') or analysis.indicators.get('ATR14')

                        # ATR fallback: pakai 0.1% dari entry jika ATR None
                        if not atr or atr == 0:
                            atr = (entry or 1) * 0.001
                            print(f"⚠️ ATR fallback untuk {pair}: {atr:.5f}")

                        # Anti-spam signal: minimal 15 menit per pair
                        now_ts = time.time()
                        if pair in last_signal_time and (now_ts - last_signal_time[pair]) < 900:
                            continue
                        last_signal_time[pair] = now_ts

                        # ICT Logic dengan bias
                        proto = "XAMD" if atr > (entry * 0.001) else "AMDX"
                        logic, ict_text = get_ict_context(proto, direction, pair, bias)

                        # ── ICT SL/TP Engine (bukan asal ATR) ───────────────
                        sl, tp, sl_dist, rr, zone_info = calculate_ict_sltp(
                            pair, direction, entry, atr, analysis.indicators
                        )

                        # Tolak signal jika RR < 2:1
                        if sl is None:
                            print(f"⛔ {pair} signal ditolak — {zone_info}")
                            continue

                        sig_msg = (
                            f"🦅 *GLOBAL SIGNAL: {pair}* 🦅\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"🔥 *Logic:* {logic}\n"
                            f"📥 *Action:* {direction}\n"
                            f"🎯 *Price:* `{entry:.{cfg['dec']}f}`\n"
                            f"🛑 *SL:* `{sl:.{cfg['dec']}f}` | 🎯 *TP:* `{tp:.{cfg['dec']}f}`\n\n"
                            f"📊 *ICT Zone Analysis:*\n{ict_text}\n\n"
                            f"📐 *SL/TP Structure:*\n• {zone_info}\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"🏛 *Market:* {cfg['ex']} | 🕐 *Macro Status:* ACTIVE\n"
                            f"⏰ *Update:* {datetime.now(WIB).strftime('%H:%M:%S WIB')}"
                        )
                        
                        send_to_all(sig_msg, category="signal", data={"pair": pair, "entry": entry, "tp": tp, "sl": sl})
                        time.sleep(30) # Anti-spam antar pair

                except Exception as e:
                    print(f"❌ Error [{pair}]: {e}")
                    rotate_tor_ip()  # Ganti IP saat error 403
                    time.sleep(10)
                    continue

            print(f"[{datetime.now(WIB).strftime('%H:%M:%S')}] Cycle Complete. Sleeping...")
            time.sleep(600) # Scan setiap 10 menit

        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_freedom_engine()