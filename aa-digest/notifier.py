import os
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

def send_telegram_message(message: str) -> bool:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "disable_web_page_preview": True,
    }

    r = requests.post(url, json=payload, timeout=15)
    if not r.ok:
        print("TELEGRAM STATUS:", r.status_code)
        print("TELEGRAM BODY:", r.text[:500])
    return r.ok
