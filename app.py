import os
import hmac
import requests

from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

INFO_MESSAGE = """
🎬 <b>Streaming Radar</b>

Your weekly guide to what's new in streaming.

Discover the latest movie releases across streaming platforms — from subscription premieres to digital rentals and purchases.

Every week, get a curated digest with movie details, cast, directors, plot summaries, and where to watch.

Less scrolling. More watching. 🍿
"""


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
    chat_id = chat.get("id")

    if text and text.split()[0].split("@")[0] == "/info" and chat_id:
        if not BOT_TOKEN:
            return "Bot token is not configured", 500

        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": INFO_MESSAGE,
                "parse_mode": "HTML"
            },
            timeout=15
        ).raise_for_status()

    return "OK", 200
