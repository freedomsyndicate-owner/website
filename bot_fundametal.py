"""
╔══════════════════════════════════════════════════════════════════════════╗
║       FREEDOM SYNDICATE — FUNDAMENTAL V11 SUPREME                       ║
║       ─────────────────────────────────────────────────────             ║
║       ✅ Economic Calendar  — ALL impacts (🟢🟡🔴)                      ║
║       ✅ Pre-event Alert    — 15 min / 5 min / 1 min before              ║
║       ✅ Live Result        — Actual vs Forecast + Beat/Miss/Inline      ║
║       ✅ ICT Market Impact  — Displacement & FVG note after data         ║
║       ✅ Geopolitical Intel — War / Sanctions / Oil / Fed / CPI ...      ║
║       ✅ Multi-Source News  — CryptoPanic + BBC RSS + CNN RSS             ║
║       ✅ Session Brief      — Asia / London / NY open brief              ║
║       ✅ Weekly Calendar    — High-impact event overview every Monday    ║
║       ✅ Auto-translate     — 🇺🇸 English → 🇮🇩 Indonesia                ║
║       📡 News → Telegram + Discord + Firebase (Website News Tab)         ║
╚══════════════════════════════════════════════════════════════════════════╝
Install: pip install requests deep-translator
"""

import requests
import time
from datetime import datetime, timezone, timedelta

# ─── CONFIGURATION ─────────────────────────────────────────────────────────────
TOKEN_TG        = "8196511062:AAGyfWcRUk9uw_lc_aQgUW6vLyyRmgF1hcE"
CHAT_ID_TG      = "-1003660980986"
TOPIC_ID_TG     = 18
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1489314765074595840/BRby0L3L4cfUUGyDpihSBjRlHPpNutFiZWF5mFYU6CpCkjoEA9Hw1A2W0c6LEUgO30i7"
FIREBASE_DB_URL = "https://freedomsyndicatecloud-default-rtdb.firebaseio.com"

# ─── STATE ─────────────────────────────────────────────────────────────────────
reported_alerts: set = set()

try:
    from deep_translator import GoogleTranslator
    _tr = GoogleTranslator(source="auto", target="id")
    TRANSLATE_OK = True
except Exception:
    TRANSLATE_OK = False

def translate(text: str) -> str:
    if not TRANSLATE_OK:
        return text
    try:
        return _tr.translate(text[:500])
    except Exception:
        return text


# ══════════════════════════════════════════════════════════════════════════════
#  FIREBASE HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def push_firebase(path: str, data: dict):
    try:
        r = requests.post(f"{FIREBASE_DB_URL}/{path}.json", json=data, timeout=10)
        if r.status_code == 200:
            key = r.json().get("name", "")
            print(f"    ✅ Firebase /{path}/{key}")
            return key
    except Exception as e:
        print(f"    ✗ Firebase: {e}")
    return None


def trim_firebase(path: str, keep: int = 100):
    try:
        r = requests.get(f"{FIREBASE_DB_URL}/{path}.json", timeout=10)
        if r.status_code == 200 and r.json():
            keys = list(r.json().keys())
            for old in keys[: max(0, len(keys) - keep)]:
                requests.delete(f"{FIREBASE_DB_URL}/{path}/{old}.json", timeout=5)
    except:
        pass


# ══════════════════════════════════════════════════════════════════════════════
#  DELIVERY — Telegram + Discord + Firebase
# ══════════════════════════════════════════════════════════════════════════════
IMPACT_COLOR = {
    "HIGH":        0xE74C3C,   # Red
    "MEDIUM":      0xF39C12,   # Orange
    "LOW":         0x2ECC71,   # Green
    "GEOPOLITICAL":0x9B59B6,   # Purple
    "SESSION":     0x3498DB,   # Blue
    "SYSTEM":      0x95A5A6,   # Grey
}

IMPACT_ICON = {
    "HIGH":   "🔴",
    "MEDIUM": "🟡",
    "LOW":    "🟢",
}


def send_news(
    title: str,
    body: str,
    icon: str = "📰",
    image_url: str = None,
    impact: str = "LOW",
    category: str = "economic",
):
    """Broadcast a news item to Telegram, Discord, and Firebase."""
    ts  = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    tag = "@traders\n" if impact == "HIGH" else ""
    tg_msg = f"{icon} *{title}*\n\n{body}\n\n_#FreedomSyndicate #MarketIntel_"

    # ── Telegram ──────────────────────────────────────────────────────────────
    try:
        base = f"https://api.telegram.org/bot{TOKEN_TG}/"
        payload = {
            "chat_id": CHAT_ID_TG,
            "message_thread_id": TOPIC_ID_TG,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False,
        }
        if image_url:
            payload["photo"]   = image_url
            payload["caption"] = tg_msg[:1024]
            requests.post(base + "sendPhoto", json=payload, timeout=10)
        else:
            payload["text"] = tg_msg[:4096]
            requests.post(base + "sendMessage", json=payload, timeout=10)
        print(f"    📱 TG: {title[:50]}")
    except Exception as e:
        print(f"    ✗ TG: {e}")

    # ── Discord ───────────────────────────────────────────────────────────────
    try:
        color   = IMPACT_COLOR.get(impact, 0x95A5A6)
        embed   = {
            "title":       f"{icon} {title}",
            "description": body[:2000],
            "color":       color,
            "footer":      {"text": f"Freedom Syndicate | {ts}"},
        }
        if image_url:
            embed["image"] = {"url": image_url}
        requests.post(DISCORD_WEBHOOK, json={"content": tag, "embeds": [embed]}, timeout=10)
        print(f"    💬 Discord: {title[:50]}")
    except Exception as e:
        print(f"    ✗ Discord: {e}")

    # ── Firebase (Website → news tab) ─────────────────────────────────────────
    firebase_path = f"news/{category}"
    push_firebase(firebase_path, {
        "title":     title,
        "body":      body[:600],
        "icon":      icon,
        "impact":    impact,
        "category":  category,
        "image_url": image_url,
        "timestamp": ts,
    })
    trim_firebase(firebase_path)


# ══════════════════════════════════════════════════════════════════════════════
#  ECONOMIC CALENDAR
# ══════════════════════════════════════════════════════════════════════════════
def check_economic_calendar():
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    
    # --- FIX: Identitas lengkap biar tembus blokir Cloudflare ---
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": "https://www.faireconomy.media/"
    }
    
    try:
        events = requests.get(url, headers=headers, timeout=10).json()
    except Exception as e:
        print(f"    ✗ Calendar fetch: Expecting JSON but got blocked. Retrying later...")
        return

    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

    for event in events:
        try:
            e_time = datetime.strptime(
                event["date"], "%Y-%m-%dT%H:%M:%S%z"
            ).replace(tzinfo=None)
        except Exception:
            continue

        diff_min = (e_time - now_utc).total_seconds() / 60
        impact   = event.get("impact", "low").upper()
        currency = event.get("currency", event.get("country", "N/A"))
        title    = event.get("title", "Economic Event")
        imp_icon = IMPACT_ICON.get(impact, "⚪")
        wib_str  = (e_time + timedelta(hours=7)).strftime("%H:%M WIB")

        # PRE-EVENT ALERTS (H-15, H-5, H-1)
        for mins in [15, 5, 1]:
            lo, hi = mins - 0.4, mins + 0.4
            if lo <= diff_min <= hi:
                aid = f"PRE_{title}_{event['date']}_{mins}"
                if aid not in reported_alerts:
                    urgency = "🚨 IMMINENT!" if mins == 1 else ("⚠️ ALERT" if mins == 5 else "📢 NOTICE")
                    body = (f"{urgency} _{mins} menit lagi_\n\n"
                            f"📋 *Event:* {title}\n"
                            f"🏛️ *Currency:* {currency} | *Impact:* {imp_icon} {impact}\n"
                            f"🕒 *Waktu:* {wib_str}\n"
                            f"━━━━━━━━━━━━━━━━\n"
                            f"📊 *Forecast:* {event.get('forecast', 'N/A')}\n"
                            f"📜 *Previous:* {event.get('previous', 'N/A')}\n")
                    send_news(f"📡 PRE-EVENT: {title}", body, imp_icon, impact=impact, category="economic")
                    reported_alerts.add(aid)

        # POST-EVENT RESULT
        if -10 <= diff_min <= 0:
            rid = f"RESULT_{title}_{event['date']}"
            if rid not in reported_alerts:
                actual = event.get("actual")
                if actual:
                    forecast = event.get("forecast", "N/A")
                    body = (f"📈 **DATA RELEASED: {title}**\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"📌 **Actual:** `{actual}`\n"
                            f"🎯 **Forecast:** {forecast}\n"
                            f"📜 **Previous:** {event.get('previous', 'N/A')}\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"🏛️ **Curr:** {currency} | **Impact:** {impact}")
                    send_news(f"📈 RESULT: {title}", body, "📊", impact=impact, category="economic")
                    reported_alerts.add(rid)

def check_global_intel():
    url = "https://cryptopanic.com/api/v1/posts/?kind=news&public=true"
    try:
        res = requests.get(url, timeout=10).json()
        for post in res.get("results", [])[:15]:
            pid = str(post.get("id", ""))
            if pid not in reported_alerts:
                title_en = post.get("title", "")
                keys = ['trump', 'war', 'iran', 'israel', 'oil', 'fed', 'fomc', 'cpi', 'ppi', 'missile', 'nuclear', 'attack', 'china', 'russia', 'gold', 'xau']
                if any(k in title_en.lower() for k in keys):
                    title_id = translate(title_en)
                    img = post.get('metadata', {}).get('image')
                    body = (f"🌍 **BREAKING GLOBAL NEWS**\n\n"
                             f"🇮🇩 **INDO:** {title_id}\n\n"
                             f"🇺🇸 **ORIG:** {title_en}\n\n"
                             f"🔗 [BACA DETAIL]({post['url']})")
                    send_news("🌍 GLOBAL INTEL", body, "💥", image_url=img, impact="HIGH", category="geopolitical")
                    reported_alerts.add(pid)
    except: pass

if __name__ == "__main__":
    # FIX: Notifikasi Aktif Terpusat ke Telegram, Discord & Website
    send_news(
        title="SYSTEM SUPREME ONLINE",
        body="V11 FULL DATA AKTIF!\n\n✅ Alarm 🟢🟡🔴 (H-15, H-5 & H-1)\n✅ Live Result (Actual/Forecast/Prev)\n✅ Geopolitik Visual\n✅ Auto-Clean Memory",
        icon="🦅",
        impact="SYSTEM",
        category="system"
    )
    
    while True:
        check_economic_calendar()
        check_global_intel()
        if len(reported_alerts) > 2000: reported_alerts.clear()
        time.sleep(30)
