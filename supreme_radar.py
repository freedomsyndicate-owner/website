import requests
import time
from datetime import datetime, timezone, timedelta

WIB = timezone(timedelta(hours=7))
UTC = timezone.utc

TOKEN_TG              = "8196511062:AAGyfWcRUk9uw_lc_aQgUW6vLyyRmgF1hcE"
CHAT_ID_TG            = "-1003660980986"
TOPIC_ID_FUNDA_TG     = 18
DISCORD_WEBHOOK_FUNDA = "https://discord.com/api/webhooks/1489314765074595840/BRby0L3L4cfUUGyDpihSBjRlHPpNutFiZWF5mFYU6CpCkjoEA9Hw1A2W0c6LEUgO30i7"
FIREBASE_DB_URL       = "https://freedomsyndicatecloud-default-rtdb.firebaseio.com"

PROXIES = {'http': 'socks5://127.0.0.1:9150', 'https': 'socks5://127.0.0.1:9150'}
CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
IMPACT_MAP = {"High": {"emoji": "🔴", "label": "HIGH"}, "Medium": {"emoji": "🟡", "label": "MEDIUM"}, "Low": {"emoji": "🟢", "label": "LOW"}}
ALARM_LEVELS = [15, 5, 1]
alerted = {}

def send_funda(msg, firebase_data=None):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN_TG}/sendMessage",
                      json={"chat_id": CHAT_ID_TG, "message_thread_id": TOPIC_ID_FUNDA_TG, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass
    try: requests.post(DISCORD_WEBHOOK_FUNDA, json={"content": msg}, timeout=10)
    except: pass

def fetch_calendar():
    try: return requests.get(CALENDAR_URL, proxies=PROXIES, timeout=15).json()
    except: return []

def parse_event_time(ev):
    try: return datetime.fromisoformat(ev['date']).astimezone(UTC)
    except: return None

def build_pre_event_msg(ev, minutes_left, impact_info):
    ts_wib = datetime.now(WIB).strftime("%Y-%m-%d %H:%M WIB")
    ev_dt = parse_event_time(ev)
    ev_wib_str = ev_dt.astimezone(WIB).strftime("%H:%M WIB") if ev_dt else "N/A"
    
    msg = (f"{impact_info['emoji']}📡 *PRE-EVENT: {ev['title']}*\n\n"
           f"⚠️ ALERT *{int(round(minutes_left))} menit lagi*\n"
           f"🏛 *Curr:* {ev['country']} | *Impact:* {impact_info['label']}\n"
           f"🕐 *Waktu:* {ev_wib_str}\n──────────────────\n"
           f"📊 *Forecast:* {ev.get('forecast','—')}\n"
           f"📋 *Previous:* {ev.get('previous','—')}\n\n"
           f"_Freedom Syndicate | {ts_wib}_")
    return msg

if __name__ == "__main__":
    print("\n📡 SUPREME RADAR V1 (JAKARTA TIME)")
    send_funda(f"🦅 *SYSTEM SUPREME ONLINE*\n⏰ Time: {datetime.now(WIB).strftime('%H:%M WIB')}\n_Freedom Syndicate_")
    
    while True:
        events = fetch_calendar()
        for ev in events:
            impact = ev.get('impact', '')
            if impact not in IMPACT_MAP: continue
            uid = f"{ev.get('country')}-{ev.get('title')}-{ev.get('date')}"
            ev_dt = parse_event_time(ev)
            if not ev_dt: continue
            
            mins = (ev_dt - datetime.now(UTC)).total_seconds() / 60
            if uid not in alerted: alerted[uid] = set()
            
            for lvl in ALARM_LEVELS:
                if str(lvl) not in alerted[uid] and 0 < mins <= (lvl + 0.9):
                    send_funda(build_pre_event_msg(ev, mins, IMPACT_MAP[impact]))
                    alerted[uid].add(str(lvl))
                    break
        time.sleep(60)
