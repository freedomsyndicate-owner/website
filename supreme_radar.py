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
TOPIC_ID_FUNDA_TG     = 20   # Topic #fundamental

# Webhook Discord dari bot_fundamental.py milikmu
DISCORD_WEBHOOK_FUNDA = "https://discord.com/api/webhooks/1489314765074595840/BRby0L3L4cfUUGyDpihSBjRlHPpNutFiZWF5mFYU6CpCkjoEA9Hw1A2W0c6LEUg030i7"
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
alerted = {}


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def push_to_firebase(path: str, data: dict):
    try:
        requests.post(f"{FIREBASE_DB_URL}/{path}.json", json=data, timeout=10)
    except: pass

def send_funda(msg):
    """Kirim ke Telegram topic #fundamental + Discord #fundamental + Website"""
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
    try:
        requests.post(DISCORD_WEBHOOK_FUNDA, json={"content": msg}, timeout=10)
    except: pass
    try:
        push_to_firebase("signals/fundamental", {"message": msg, "timestamp": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")})
    except: pass

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
    """Parse datetime event ke UTC"""
    try:
        dt = datetime.fromisoformat(ev['date'])
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
    ts_utc = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    ev_dt = parse_event_time(ev)
    ev_wib_str = ev_dt.astimezone(WIB).strftime("%H:%M WIB") if ev_dt else "N/A"

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
    ts_utc = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    actual   = ev.get('actual')   or '—'
    forecast = ev.get('forecast') or '—'
    previous = ev.get('previous') or '—'
    imp_e    = impact_info['emoji']
    imp_l    = impact_info['label']

    ev_dt = parse_event_time(ev)
    ev_wib_str = ev_dt.astimezone(WIB).strftime("%H:%M WIB") if ev_dt else "N/A"

    def clean_num(s):
        if not s or s == '—': return None
        try:
            return float(s.replace('%', '').replace('K', 'e3').replace('M', 'e6').replace('B', 'e9').replace(',', '').strip())
        except: return None

    a_val = clean_num(actual)
    f_val = clean_num(forecast)
    if a_val is not None and f_val is not None:
        if a_val > f_val: result_tag = "📈 *BETTER THAN FORECAST*"
        elif a_val < f_val: result_tag = "📉 *WORSE THAN FORECAST*"
        else: result_tag = "➡️ *IN LINE WITH FORECAST*"
    else: result_tag = "📊 *RESULT AVAILABLE*"

    msg = (
        f"{imp_e}📊 *LIVE RESULT: {ev['title']}*\n\n"
        f"{result_tag}\n\n"
        f"📋 *Event:* {ev['title']}\n"
        f"🏛 *Currency:* {ev['country']} | *Impact:* {imp_e} {imp_l}\n"
        f"🕐 *Waktu:* {ev_wib_str}\n"
        f"──────────────────\n"
        f"✅ *Actual:* `{actual}`\n"
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
        for ev in events:
            impact = ev.get('impact', '')
            if impact not in IMPACT_MAP: continue

            impact_info = IMPACT_MAP[impact]
            uid  = event_uid(ev)
            ev_dt = parse_event_time(ev)
            if not ev_dt: continue

            mins = minutes_until(ev_dt)
            if uid not in alerted: alerted[uid] = set()

            for lvl in ALARM_LEVELS:
                key = str(lvl)
                if key not in alerted[uid] and 0 < mins <= (lvl + 0.9):
                    msg = build_pre_event_msg(ev, mins, impact_info)
                    send_funda(msg)
                    alerted[uid].add(key)
                    print(f"  📢 [{impact_info['label']}] {ev['country']} — {ev['title']} → H-{lvl} Alert!")
                    break

            actual = ev.get('actual', '')
            if actual and actual.strip() and "result" not in alerted[uid] and mins < -1:
                msg = build_result_msg(ev, impact_info)
                send_funda(msg)
                alerted[uid].add("result")
                print(f"  ✅ [{impact_info['label']}] {ev['country']} — {ev['title']} → Result: {actual}")

        ts_now = datetime.now(UTC).strftime("%H:%M UTC")
        print(f"[{ts_now}] Checked {len(events)} events | Sleep 60s...")
        time.sleep(60)
