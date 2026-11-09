
import os
import hmac
import requests
from flask import Flask, request
from datetime import datetime, timezone
app = Flask(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

INFO_MESSAGE = """
🎬 <b>Streaming Radar</b>

Your weekly guide to what's new in streaming.

Discover the latest movie releases across streaming platforms — from subscription premieres to digital rentals and purchases.

Every Friday, get a curated digest with movie details, cast, directors, plot summaries, and where to watch.

Less scrolling. More watching. 🍿
"""

WELCOME_MESSAGE = """
🎬 <b>Welcome to Streaming Radar!</b>

You are now subscribed to our weekly newsletter.

Every Friday, I'll send you a curated digest of new full-length movies available on streaming platforms.

You'll get movie details, cast, directors, plot summaries, and where to watch.

Less scrolling. More watching. 🍿

To unsubscribe, send /stop.
"""

STOP_MESSAGE = """
You have been unsubscribed from Streaming Radar.

You won't receive any more weekly digests.

If you change your mind, just send /start. 🎬
"""


def send_message(chat_id, message):
    if not BOT_TOKEN:
        raise RuntimeError("Bot token is not configured")

    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        },
        timeout=15
    )
    response.raise_for_status()


def supabase_request(method, telegram_id, data=None):
    if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
        raise RuntimeError("Supabase credentials are not configured")

    url = f"{SUPABASE_URL}/rest/v1/subscribers"

    headers = {
        "apikey": SUPABASE_SECRET_KEY,
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }

    if method == "POST":
        headers["Prefer"] = "resolution=merge-duplicates,return=minimal"

        response = requests.post(
            url,
            params={"on_conflict": "telegram_id"},
            headers=headers,
            json=data,
            timeout=15
        )

    elif method == "PATCH":
        response = requests.patch(
            url,
            params={"telegram_id": f"eq.{telegram_id}"},
            headers=headers,
            json=data,
            timeout=15
        )

    else:
        raise ValueError("Unsupported Supabase method")

    response.raise_for_status()


@app.route("/", methods=["GET"])
def home():
    return "Streaming Radar bot is running!"


@app.route("/webhook", methods=["POST"])
def webhook():

    if not WEBHOOK_SECRET:
        return "Webhook secret is not configured", 500

    received_secret = request.headers.get(
        "X-Telegram-Bot-Api-Secret-Token", ""
    )

    if not hmac.compare_digest(received_secret, WEBHOOK_SECRET):
        return "Unauthorized", 403

    update = request.get_json(silent=True) or {}
    message = update.get("message", {})

    text = message.get("text", "")
    chat = message.get("chat", {})
    sender = message.get("from", {})

    chat_id = chat.get("id")
    telegram_id = sender.get("id")

    if not text or not chat_id:
        return "OK", 200

    command = text.split()[0].split("@")[0]

    if command == "/start" and telegram_id:

        if chat.get("type") != "private":
            return "OK", 200

        supabase_request(
            "POST",
            telegram_id,
            {
                "telegram_id": telegram_id,
                "username": sender.get("username"),
                "first_name": sender.get("first_name"),
                "is_active": True,
                "unsubscribed_at": None
            }
        )

        send_message(chat_id, WELCOME_MESSAGE)

    elif command == "/stop" and telegram_id:

        if chat.get("type") != "private":
            return "OK", 200

        supabase_request(
            "PATCH",
            telegram_id,
            {
                "is_active": False,
                "unsubscribed_at": datetime.now(timezone.utc).isoformat()
            }
        )

        send_message(chat_id, STOP_MESSAGE)

    elif command == "/info":

        send_message(chat_id, INFO_MESSAGE)

    return "OK", 200

