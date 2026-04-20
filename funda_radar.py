import requests
import time
from datetime import datetime, timezone

PROXIES = {'http': 'socks5://127.0.0.1:9150', 'https': 'socks5://127.0.0.1:9150'}
TOKEN_TG = "8196511062:AAGyfWcRUk9uw_lc_aQgUW6vLyyRmgF1hcE"
CHAT_ID_TG = "-1003660980986"

def send_funda(msg):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN_TG}/sendMessage", 
                     json={"chat_id": CHAT_ID_TG, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass

if __name__ == "__main__":
    print("📢 FUNDAMENTAL RADAR ACTIVE")
    while True:
        try:
            r = requests.get("https://nfs.faireconomy.media/ff_calendar_thisweek.json", proxies=PROXIES, timeout=15)
            for event in r.json():
                if event['country'] == 'USD' and event['impact'] == 'High':
                    msg = f"⚠️ **USD HIGH IMPACT**\nEvent: {event['title']}\nTime: {event['date']}"
                    send_funda(msg)
                    break
        except: pass
        time.sleep(14400) # Check 4 jam sekali
