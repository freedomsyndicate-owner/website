"""
╔══════════════════════════════════════════════════════════════════════════╗
║       SUPREME RADAR V1 — FUNDAMENTAL + SYNDICATE (MERGED)               ║
║       ─────────────────────────────────────────────────────              ║
║       ✅ Impact Filter : 🔴 HIGH  🟡 MEDIUM  🟢 LOW                      ║
║       ✅ Pre-Event Alarm: H-15 · H-5 · H-1                               ║
║       ✅ Live Result   : Actual vs Forecast vs Previous                   ║
║       ✅ Output        : Telegram (topic #fundamental) + Discord          ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import requests
import time
from datetime import datetime, timezone, timedelta

# ─── TIMEZONE ────────────────────────────────────────────────────────────────
WIB = timezone(timedelta(hours=7))
UTC = timezone.utc

# ─── CONFIGURATION ──────────────────────────────────────────────────────────
TOKEN_TG              = "8196511062:AAGyfWcRUk9uw_lc_aQgUW6vLyyRmgF1hcE"
CHAT_ID_TG            = "-1003660980986"
TOPIC_ID_FUNDA_TG     = 18
DISCORD_WEBHOOK_FUNDA = "https://discord.com/api/webhooks/1489314765074595840/BRby0L3L4cfUUGyDpihSBjRlHPpNutFiZWF5mFYU6CpCkjoEA9Hw1A2W0c6LEUgO30i7"
FIREBASE_DB_URL       = "https://freedomsyndicatecloud-default-rtdb.firebaseio.com"

PROXIES = {
    'http':  'socks5://127.0.0.1:9150',
    'https': 'socks5://127.0.0.1:9150'
}

CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

# ─── IMPACT MAPPING ──────────────────────────────────────────────────────────
IMPACT_MAP = {
    "High":   {"emoji": "🔴", "label": "HIGH"},
    "Medium": {"emoji": "🟡", "label": "MEDIUM"},
    "Low":    {"emoji": "🟢", "label": "LOW"},
}

# Alarm levels dalam menit sebelum event
ALARM_LEVELS = [15, 5, 1]   # H-15, H-5, H-1

# ─── ALERT MEMORY (anti-duplikat) ───────────────────────────────────────────
# { "event_unique_id": {"15", "5", "1", "result"} }
alerted = {}


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def push_to_firebase(path: str, data: dict):
    """Push data ke Firebase Realtime DB"""
    try:
        requests.post(f"{FIREBASE_DB_URL}/{path}.json", json=data, timeout=10)
    except: pass

def send_funda(msg, firebase_data=None):
    """Kirim ke Telegram + Discord + Firebase"""
    # ── Telegram ──────────────────────────────────────────────────────────
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN_TG}/sendMessage",
            json={
                "chat_id":            CHAT_ID_TG,
                "message_thread_id":  TOPIC_ID_FUNDA_TG,
                "text":               msg,
                "parse_mode":         "Markdown"
            }, timeout=10
        )
    except: pass
    # ── Discord ───────────────────────────────────────────────────────────
    try:
        requests.post(DISCORD_WEBHOOK_FUNDA, json={"content": msg}, timeout=10)
    except: pass
    # ── Firebase ──────────────────────────────────────────────────────────
    if firebase_data:
        push_to_firebase("signals/fundamental", firebase_data)

def fetch_calendar():
    """Ambil data kalender ekonomi minggu ini"""
    try:
        r = requests.get(CALENDAR_URL, proxies=PROXIES, timeout=15)
        return r.json()
    except Exception as e:
        print(f"  ⚠ Calendar fetch error: {e}")
        return []

def event_uid(ev):
    """Buat ID unik per event (country + title + date)"""
    return f"{ev.get('country','')}-{ev.get('title','')}-{ev.get('date','')}"

def parse_event_time(ev):
    """Parse datetime event ke UTC. API mengembalikan ISO-8601 dengan offset."""
    try:
        dt = datetime.fromisoformat(ev['date'])     # e.g. "2026-04-20T13:00:00-04:00"
        return dt.astimezone(UTC)
    except:
        return None

def minutes_until(dt_utc):
    """Selisih menit dari sekarang ke event"""
    now = datetime.now(UTC)
    return (dt_utc - now).total_seconds() / 60


# ══════════════════════════════════════════════════════════════════════════════
#  MESSAGE BUILDERS
# ══════════════════════════════════════════════════════════════════════════════

def build_pre_event_msg(ev, minutes_left, impact_info):
    """
    Format pre-event alert persis seperti gambar 'Doms Fundamental':

    🟢📡 PRE-EVENT: German Buba Monthly Report
    ⚠️ ALERT 5 menit lagi [H-5]
    📋 Event: ...
    🏛 Currency: EUR | Impact: 🟢 LOW
    🕐 Waktu: 13:00 WIB
    ──────────────────
    📊 Forecast: —
    📋 Previous: —
    Freedom Syndicate | 2026-04-20 05:54 UTC
    """
    ts_utc = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    # Waktu event dalam WIB
    ev_dt = parse_event_time(ev)
    ev_wib_str = ev_dt.astimezone(WIB).strftime("%H:%M WIB") if ev_dt else "N/A"

    # Label H-xx
    for lvl in ALARM_LEVELS:
        if minutes_left <= lvl + 0.9:
            level_label = f"H-{lvl}"
            mnt_text    = f"{int(round(minutes_left))} menit lagi"
            break
    else:
        level_label = f"{int(round(minutes_left))}m"
        mnt_text    = f"{int(round(minutes_left))} menit lagi"

    forecast = ev.get('forecast') or '—'
    previous = ev.get('previous') or '—'
    imp_e    = impact_info['emoji']
    imp_l    = impact_info['label']

    msg = (
        f"{imp_e}📡 *PRE-EVENT: {ev['title']}*\n\n"
        f"⚠️ ALERT *{mnt_text}* [{level_label}]\n\n"
        f"📋 *Event:* {ev['title']}\n"
        f"🏛 *Currency:* {ev['country']} | *Impact:* {imp_e} {imp_l}\n"
        f"🕐 *Waktu:* {ev_wib_str}\n"
        f"──────────────────\n"
        f"📊 *Forecast:* {forecast}\n"
        f"📋 *Previous:* {previous}\n\n"
        f"_Freedom Syndicate | {ts_utc}_"
    )
    return msg

def build_result_msg(ev, impact_info):
    """
    Format notifikasi setelah event rilis (Actual tersedia):

    🔴📊 LIVE RESULT: US Core CPI m/m
    📈 BETTER THAN FORECAST
    ...
    ✅ Actual:    0.4%
    📊 Forecast:  0.3%
    📋 Previous:  0.4%
    """
    ts_utc = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    actual   = ev.get('actual')   or '—'
    forecast = ev.get('forecast') or '—'
    previous = ev.get('previous') or '—'
    imp_e    = impact_info['emoji']
    imp_l    = impact_info['label']

    ev_dt = parse_event_time(ev)
    ev_wib_str = ev_dt.astimezone(WIB).strftime("%H:%M WIB") if ev_dt else "N/A"

    # Sentimen hasil vs forecast
    def clean_num(s):
        if not s or s == '—': return None
        try:
            return float(
                s.replace('%', '').replace('K', 'e3').replace('M', 'e6')
                 .replace('B', 'e9').replace(',', '').strip()
            )
        except:
            return None

    a_val = clean_num(actual)
    f_val = clean_num(forecast)
    if a_val is not None and f_val is not None:
        if a_val > f_val:
            result_tag = "📈 *BETTER THAN FORECAST*"
        elif a_val < f_val:
            result_tag = "📉 *WORSE THAN FORECAST*"
        else:
            result_tag = "➡️ *IN LINE WITH FORECAST*"
    else:
        result_tag = "📊 *RESULT AVAILABLE*"

    msg = (
        f"{imp_e}📊 *LIVE RESULT: {ev['title']}*\n\n"
        f"{result_tag}\n\n"
        f"📋 *Event:* {ev['title']}\n"
        f"🏛 *Currency:* {ev['country']} | *Impact:* {imp_e} {imp_l}\n"
        f"🕐 *Waktu:* {ev_wib_str}\n"
        f"──────────────────\n"
        f"✅ *Actual:*   `{actual}`\n"
        f"📊 *Forecast:* `{forecast}`\n"
        f"📋 *Previous:* `{previous}`\n\n"
        f"_Freedom Syndicate | {ts_utc}_"
    )
    return msg


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN RUNNER
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "="*55)
    print("📡 SUPREME RADAR V1 — FUNDAMENTAL + SYNDICATE")
    print("="*55 + "\n")

    ts_boot = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    send_funda(
        "🦅 *SYSTEM SUPREME ONLINE*\n\n"
        "*V1 FULL DATA AKTIF!*\n\n"
        "✅ Alarm 🟢🟡🔴 (H-15, H-5 & H-1)\n"
        "✅ Live Result (Actual/Forecast/Prev)\n"
        "✅ Geopolitik Visual\n"
        "✅ Auto-Clean Memory\n\n"
        f"_Freedom Syndicate | {ts_boot}_"
    )

    while True:
        events = fetch_calendar()
        now_utc = datetime.now(UTC)

        for ev in events:
            impact = ev.get('impact', '')
            if impact not in IMPACT_MAP:
                continue    # Skip: Holiday / event tanpa impact

            impact_info = IMPACT_MAP[impact]
            uid  = event_uid(ev)
            ev_dt = parse_event_time(ev)

            if not ev_dt:
                continue

            mins = minutes_until(ev_dt)

            # Inisialisasi memory jika belum ada
            if uid not in alerted:
                alerted[uid] = set()

            # ── Pre-Event Alarms: H-15, H-5, H-1 ────────────────────────────
            for lvl in ALARM_LEVELS:
                key = str(lvl)
                # Kirim kalau dalam window [0, lvl+0.9] menit sebelum event
                if key not in alerted[uid] and 0 < mins <= (lvl + 0.9):
                    msg = build_pre_event_msg(ev, mins, impact_info)
                    fb_data = {
                        "type": "pre_event", "level": f"H-{lvl}",
                        "title": ev.get("title",""), "country": ev.get("country",""),
                        "impact": impact, "time_wib": ev_dt.astimezone(WIB).strftime("%H:%M WIB"),
                        "forecast": ev.get("forecast",""), "previous": ev.get("previous",""),
                        "timestamp": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
                    }
                    send_funda(msg, fb_data)
                    alerted[uid].add(key)
                    print(f"  📢 [{impact_info['label']}] "
                          f"{ev['country']} — {ev['title']} → H-{lvl} Alert!")
                    break   # Satu level per iterasi

            # ── Live Result (setelah event, actual tersedia) ─────────────────
            actual = ev.get('actual', '')
            if actual and actual.strip() and "result" not in alerted[uid] and mins < -1:
                msg = build_result_msg(ev, impact_info)
                fb_data = {
                    "type": "result", "title": ev.get("title",""), "country": ev.get("country",""),
                    "impact": impact, "actual": actual,
                    "forecast": ev.get("forecast",""), "previous": ev.get("previous",""),
                    "timestamp": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
                }
                send_funda(msg, fb_data)
                alerted[uid].add("result")
                print(f"  ✅ [{impact_info['label']}] "
                      f"{ev['country']} — {ev['title']} → Result: {actual}")

        # ── Auto-clean memory untuk event lebih dari 24 jam lalu ─────────────
        for ev in events:
            ev_dt = parse_event_time(ev)
            if ev_dt and minutes_until(ev_dt) < -1440:
                alerted.pop(event_uid(ev), None)

        ts_now = datetime.now(UTC).strftime("%H:%M UTC")
        active_count = sum(
            1 for ev in events if ev.get('impact') in IMPACT_MAP
        )
        print(f"[{ts_now}] Checked {len(events)} events "
              f"({active_count} L/M/H) | Sleep 60s...")
        time.sleep(60)   # Cek setiap 1 menit