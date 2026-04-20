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
# Discord embed color palette
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
    """
    Comprehensive economic calendar scanner:
      • Pre-event alerts at T-15, T-5, T-1 minutes (ALL impacts)
      • Live result with Beat / Miss / Inline analysis
      • ICT market note after each release
    """
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    try:
        events = requests.get(url, timeout=10).json()
    except Exception as e:
        print(f"    ✗ Calendar fetch: {e}")
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

        # ── PRE-EVENT ALERTS ──────────────────────────────────────────────────
        for mins in [15, 5, 1]:
            lo, hi = mins - 0.4, mins + 0.4
            if lo <= diff_min <= hi:
                aid = f"PRE_{title}_{event['date']}_{mins}"
                if aid not in reported_alerts:
                    urgency = "🚨 IMMINENT!" if mins == 1 else ("⚠️ ALERT" if mins == 5 else "📢 NOTICE")

                    body = (
                        f"{urgency} _{mins} menit lagi_\n\n"
                        f"📋 *Event:*  {title}\n"
                        f"🏛️ *Currency:*  {currency}  |  *Impact:*  {imp_icon} {impact}\n"
                        f"🕒 *Waktu:*  {wib_str}\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"📊 *Forecast:*  {event.get('forecast', 'N/A')}\n"
                        f"📜 *Previous:*  {event.get('previous', 'N/A')}\n"
                        f"━━━━━━━━━━━━━━━━\n"
                    )

                    if impact == "HIGH":
                        body += (
                            "🔴 *HIGH IMPACT* — Volatilitas ekstrim!\n"
                            "• Pertimbangkan tutup/perkecil posisi terbuka\n"
                            "• Pasang SL ketat / trail stop\n"
                            "• Tunggu spike + retest setelah data keluar\n"
                            "• _ICT: Wait for displacement & FVG to form_"
                        )
                    elif impact == "MEDIUM":
                        body += (
                            "🟡 *MEDIUM IMPACT* — Potensi 20–50 pip movement\n"
                            "• Monitor candle M5 setelah rilis\n"
                            "• _ICT: Look for OB retest after spike_"
                        )
                    else:
                        body += "🟢 *LOW IMPACT* — Minimal movement expected, tetap monitor."

                    send_news(
                        f"📡 PRE-EVENT: {title}", body,
                        imp_icon, impact=impact, category="economic"
                    )
                    reported_alerts.add(aid)

        # ── POST-EVENT RESULT ─────────────────────────────────────────────────
        if -10 <= diff_min <= 0:
            rid = f"RESULT_{title}_{event['date']}"
            if rid not in reported_alerts:
                actual = event.get("actual")
                if actual:
                    forecast = event.get("forecast", "N/A")
                    previous = event.get("previous", "N/A")

                    # Beat / Miss / Inline
                    beat_miss   = ""
                    implication = ""
                    try:
                        def parse_num(s):
                            return float(
                                str(s).replace("%", "").replace("K", "e3")
                                .replace("M", "e6").replace("B", "e9")
                                .replace(",", "")
                            )
                        av = parse_num(actual)
                        fv = parse_num(forecast)
                        if av > fv:
                            beat_miss   = "✅ *BEAT FORECAST* 🚀"
                            implication = (
                                f"Positif untuk *{currency}* → potensi penguatan.\n"
                                f"_ICT: Bullish displacement candle mungkin terbentuk._"
                            )
                        elif av < fv:
                            beat_miss   = "❌ *MISS FORECAST* 📉"
                            implication = (
                                f"Negatif untuk *{currency}* → potensi pelemahan.\n"
                                f"_ICT: Bearish displacement candle mungkin terbentuk._"
                            )
                        else:
                            beat_miss   = "➖ *INLINE*"
                            implication = "Minimal impact. Market sudah price in."
                    except Exception:
                        beat_miss = "⚡ Data released"

                    body = (
                        f"📊 *Actual:*  `{actual}`  {beat_miss}\n"
                        f"🎯 *Forecast:*  {forecast}\n"
                        f"📜 *Previous:*  {previous}\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"🏛️ *Currency:*  {currency}  |  *Impact:*  {imp_icon} {impact}\n"
                    )
                    if implication:
                        body += f"\n💡 *Market Implication:*\n{implication}"

                    body += (
                        f"\n\n_ICT Tip: Tunggu candle M5/M15 konfirmasi, cari OB / FVG "
                        f"sebelum entry — jangan masuk langsung saat spike!_"
                    )

                    send_news(
                        f"📈 RESULT: {title}", body,
                        "📊", impact=impact, category="economic"
                    )
                    reported_alerts.add(rid)


# ══════════════════════════════════════════════════════════════════════════════
#  WEEKLY CALENDAR BRIEF  (every Monday 07:00 UTC)
# ══════════════════════════════════════════════════════════════════════════════
def send_weekly_brief():
    now = datetime.now(timezone.utc)
    if now.weekday() != 0 or not (7 <= now.hour < 8):
        return

    wk_id = f"WEEKLY_{now.strftime('%Y-W%W')}"
    if wk_id in reported_alerts:
        return

    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    try:
        events = requests.get(url, timeout=10).json()
    except Exception:
        return

    highs = [e for e in events if e.get("impact", "").upper() == "HIGH"]
    meds  = [e for e in events if e.get("impact", "").upper() == "MEDIUM"]

    body = f"📅 *THIS WEEK HIGH-IMPACT EVENTS ({len(highs)} events):*\n━━━━━━━━━━━━━━━━\n"
    for e in highs[:12]:
        try:
            et  = datetime.strptime(e["date"], "%Y-%m-%dT%H:%M:%S%z")
            wib = (et + timedelta(hours=7)).strftime("%a %d/%m %H:%M WIB")
            body += f"🔴 `{wib}` — *{e['title']}*  ({e.get('currency', e.get('country',''))})\n"
        except Exception:
            pass

    if meds:
        body += f"\n🟡 *MEDIUM IMPACT ({len(meds)} events):*\n"
        for e in meds[:8]:
            try:
                et  = datetime.strptime(e["date"], "%Y-%m-%dT%H:%M:%S%z")
                wib = (et + timedelta(hours=7)).strftime("%a %d/%m %H:%M WIB")
                body += f"🟡 `{wib}` — {e['title']}  ({e.get('currency', e.get('country',''))})\n"
            except Exception:
                pass

    body += (
        "\n━━━━━━━━━━━━━━━━\n"
        "_ICT Note: Minggu ini perhatikan sell-side & buy-side liquidity "
        "sebelum High-Impact events. Market sering manipulation H-1 sebelum data._\n"
        "_Freedom Syndicate — Plan your week, trade the setup._"
    )

    send_news("🗓️ WEEKLY CALENDAR BRIEF", body, "📅", impact="MEDIUM", category="economic")
    reported_alerts.add(wk_id)


# ══════════════════════════════════════════════════════════════════════════════
#  SESSION BRIEF  (Asia / London / NY open)
# ══════════════════════════════════════════════════════════════════════════════
SESSION_BRIEFS = {
    0: {
        "name": "Asia", "icon": "🌏",
        "pairs": "USDJPY, AUDUSD, NZDUSD, XAUUSD",
        "wib":  "07:00–10:00 WIB",
        "ict":  "Asia sets the range. London will sweep it. "
                "Look for equal highs/lows forming = liquidity being built."
    },
    7: {
        "name": "London", "icon": "🇬🇧",
        "pairs": "EURUSD, GBPUSD, XAUUSD, USDCAD",
        "wib":  "14:00–17:00 WIB",
        "ict":  "London Kill Zone. Expect manipulation of Asia range first "
                "(sweep of highs or lows), then true institutional move begins. "
                "Watch for CHoCH on M15 post-sweep = entry signal."
    },
    13: {
        "name": "New York", "icon": "🗽",
        "pairs": "EURUSD, GBPUSD, XAUUSD, USDJPY, BTCUSDT",
        "wib":  "20:00–23:00 WIB",
        "ict":  "NY Kill Zone. Highest volume, clearest moves. "
                "Continuation of London or full reversal. "
                "Look for NY Open Rejection / AM Kill Zone entries at OB/FVG."
    },
}


def send_session_brief():
    now  = datetime.now(timezone.utc)
    hour = now.hour
    if hour not in SESSION_BRIEFS:
        return
    if now.minute > 5:
        return   # Only fire within the first 5 min of the session hour

    s = SESSION_BRIEFS[hour]
    brief_id = f"BRIEF_{s['name']}_{now.strftime('%Y-%m-%d')}"
    if brief_id in reported_alerts:
        return

    # Fetch upcoming events in next 4 hours
    upcoming_lines = ""
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    try:
        events = requests.get(url, timeout=10).json()
        cnt = 0
        for e in events:
            try:
                et   = datetime.strptime(e["date"], "%Y-%m-%dT%H:%M:%S%z").replace(tzinfo=None)
                diff = (et - now.replace(tzinfo=None)).total_seconds() / 3600
                if 0 <= diff <= 4 and e.get("impact", "").upper() in ("HIGH", "MEDIUM"):
                    imp_icon = "🔴" if e.get("impact","").upper() == "HIGH" else "🟡"
                    wib = (et + timedelta(hours=7)).strftime("%H:%M WIB")
                    upcoming_lines += f"{imp_icon} `{wib}` *{e['title']}*  ({e.get('currency', e.get('country',''))})\n"
                    cnt += 1
                    if cnt >= 5:
                        break
            except Exception:
                pass
    except Exception:
        pass

    upcoming_block = f"\n📅 *Upcoming Events (next 4h):*\n{upcoming_lines}" if upcoming_lines else ""

    body = (
        f"{s['icon']} *{s['name'].upper()} SESSION OPEN*\n"
        f"🕒 {s['wib']}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📊 *Active Pairs:* {s['pairs']}\n\n"
        f"🧠 *ICT Note:*\n_{s['ict']}_"
        f"{upcoming_block}\n\n"
        f"_Trade smart. No FOMO. — Freedom Syndicate_"
    )

    send_news(
        f"{s['icon']} {s['name']} Session Brief", body,
        s["icon"], impact="MEDIUM", category="session_brief"
    )
    reported_alerts.add(brief_id)


# ══════════════════════════════════════════════════════════════════════════════
#  GEOPOLITICAL INTEL — KEYWORDS
# ══════════════════════════════════════════════════════════════════════════════
HIGH_GEO_KEYS = [
    "war", "nuclear", "missile", "attack", "invasion", "explosion", "airstrike",
    "bomb", "drone attack", "coup", "collapse", "bank collapse", "default",
    "fed rate", "fomc", "cpi", "nfp", "rate hike", "rate cut", "emergency",
]
MED_GEO_KEYS = [
    "sanctions", "tariff", "trade war", "inflation", "recession", "opec",
    "oil cut", "gdp", "rate decision", "debt ceiling", "geopolitical",
    "ceasefire", "negotiation", "tension",
]
ALL_GEO_KEYS = HIGH_GEO_KEYS + MED_GEO_KEYS + [
    "trump", "biden", "xi jinping", "putin", "zelensky", "netanyahu",
    "iran", "israel", "ukraine", "russia", "china", "taiwan", "north korea",
    "saudi arabia", "opec", "oil", "gold", "xau", "fed", "ecb", "boj",
]


def _classify_geo(title: str) -> tuple:
    tl = title.lower()
    if any(k in tl for k in HIGH_GEO_KEYS):
        return "HIGH", "🚨", "GEOPOLITICAL"
    if any(k in tl for k in MED_GEO_KEYS):
        return "MEDIUM", "⚡", "GEOPOLITICAL"
    return "LOW", "🌍", "GEOPOLITICAL"


# ── Source 1: CryptoPanic ──────────────────────────────────────────────────────
def check_cryptopanic():
    url = "https://cryptopanic.com/api/v1/posts/?kind=news&public=true"
    try:
        res = requests.get(url, timeout=10).json()
    except Exception as e:
        print(f"    ✗ CryptoPanic: {e}")
        return

    for post in res.get("results", [])[:25]:
        pid = str(post.get("id", ""))
        if pid in reported_alerts:
            continue

        title_en = post.get("title", "")
        if not any(k in title_en.lower() for k in ALL_GEO_KEYS):
            continue

        title_id   = translate(title_en)
        source_dom = post.get("source", {}).get("domain", "cryptopanic")
        url_post   = post.get("url", "")
        img        = (post.get("metadata") or {}).get("image")

        impact, icon, cat = _classify_geo(title_en)

        body = (
            f"🇮🇩 *{title_id}*\n\n"
            f"🇺🇸 _{title_en}_\n\n"
            f"📰 *Source:* {source_dom}\n"
            f"🔗 [Baca selengkapnya]({url_post})"
        )

        send_news("🌍 GLOBAL INTEL", body, icon, image_url=img, impact=impact, category=cat)
        reported_alerts.add(pid)
        time.sleep(2)


# ── Source 2: RSS Feed (BBC / Reuters-style) ───────────────────────────────────
RSS_FEEDS = [
    ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml"),
]


def _parse_rss_items(xml: str) -> list:
    """Minimal RSS parser without feedparser dependency."""
    items = []
    for chunk in xml.split("<i        events = requests.get(url, timeout=10).json()
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        
        for event in events:
            e_time = datetime.strptime(event['date'], '%Y-%m-%dT%H:%M:%S%z').replace(tzinfo=None)
            diff = (e_time - now_utc).total_seconds() / 60
            impact = event['impact'].upper()
            
            # 1. TRIGGER ALARM SEMUA IMPACT (H-5 & H-1)
            if (1 <= diff <= 1.5) or (5 <= diff <= 5.5):
                alert_id = f"ALARM_{event['title']}_{event['date']}_{int(diff)}"
                if alert_id not in reported_alerts:
                    wib = (e_time + timedelta(hours=7)).strftime('%H:%M')
                    icon = "🔴" if "HIGH" in impact else "🟡" if "MEDIUM" in impact else "🟢"
                    txt = f"⚡ **NEWS ALARM: {int(diff)} MENIT LAGI**\n\n🔥 **DATA:** {event['title']}\n🏛️ **CURR:** {event['country']} | **IMPACT:** {impact}\n🕒 **WAKTU WIB:** {wib}\n\n⚠️ *SYNDICATE READY!*"
                    send_alert("OMNISCIENCE RADAR", txt, icon, impact=impact)
                    reported_alerts.add(alert_id)

            # 2. TRIGGER LIVE RESULT SEMUA IMPACT (ACTUAL DATA)
            # Dicek dari menit ke-0 sampai 5 menit setelah rilis
            if (-5 <= diff <= 0):
                res_id = f"RESULT_{event['title']}_{event['date']}"
                if res_id not in reported_alerts:
                    # Hanya kirim jika data 'actual' sudah keluar dari server
                    actual = event.get('actual')
                    if actual:
                        forecast = event.get('forecast', 'N/A')
                        previous = event.get('previous', 'N/A')
                        icon = "📊"
                        
                        txt = (f"📈 **DATA RELEASED: {event['title']}**\n"
                               f"━━━━━━━━━━━━━━━━━━━━\n"
                               f"📌 **Actual:** `{actual}`\n"
                               f"🎯 **Forecast:** {forecast}\n"
                               f"📜 **Previous:** {previous}\n"
                               f"━━━━━━━━━━━━━━━━━━━━\n"
                               f"🏛️ **Curr:** {event['country']} | **Impact:** {impact}\n"
                               f"#{event['country']} #Gold #Forex")
                        send_alert("SUPREME DATA RESULT", txt, icon, impact=impact)
                        reported_alerts.add(res_id)
    except: pass

def check_global_intel():
    """RADAR GEOPOLITIK BRUTAL"""
    url = "https://cryptopanic.com/api/v1/posts/?kind=news"
    try:
        res = requests.get(url, timeout=10).json()
        for post in res['results'][:15]:
            if post['id'] not in reported_alerts:
                title_en = post['title']
                keys = ['trump', 'war', 'iran', 'israel', 'oil', 'fed', 'fomc', 'cpi', 'ppi', 'missile', 'nuclear', 'attack', 'china', 'russia', 'gold', 'xau']
                
                if any(k in title_en.lower() for k in keys):
                    try: indo = translator.translate(title_en)
                    except: indo = title_en
                    img = post.get('metadata', {}).get('image')
                    
                    pesan = (f"🌍 **BREAKING GLOBAL NEWS**\n\n"
                             f"🇮🇩 **INDO:** {indo}\n\n"
                             f"🇺🇸 **ORIG:** {title_en}\n\n"
                             f"🔗 [BACA DETAIL]({post['url']})")
                    
                    send_alert("MARKET BREAKER", pesan, "💥", image_url=img, impact="HIGH")
                    reported_alerts.add(post['id'])
    except: pass

if __name__ == "__main__":
    send_alert("SYSTEM SUPREME ONLINE", "V10 FULL DATA AKTIF!\n\n✅ Alarm 🟢🟡🔴 (H-5 & H-1)\n✅ Live Result (Actual/Forecast/Prev)\n✅ Geopolitik Visual\n✅ Auto-Clean Memory", "🦅", impact="MEDIUM")
    while True:
        check_economic_calendar()
        check_global_intel()
        if len(reported_alerts) > 2000: reported_alerts.clear()
        time.sleep(30)
