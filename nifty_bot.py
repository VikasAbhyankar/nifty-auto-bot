import requests
import os
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    requests.post(url, data=data)

try:
    # Nifty Futures approximate price via Nifty 50 spot (free API)
    r = requests.get("https://api.niftytrader.in/api/fiis", timeout=10)
    # Simple message for test - you can add real logic later
    now = datetime.now().strftime("%d-%m-%Y %I:%M %p")
    message = f"🚀 *Nifty Auto Bot Active*\n\nTime: {now} IST\nBot is running perfectly on GitHub Actions!\n\nNext run: Tomorrow 9:15 AM"
    send_telegram(message)
    print("Message sent!")
except Exception as e:
    send_telegram(f"Bot Error: {e}")
    print(e)
