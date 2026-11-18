
import os
import hmac
import hashlib
import random
import requests
from flask import Flask, request
from datetime import datetime, timezone

from formatter import format_digest, format_film
from parser import find_latest_weekly_article, parse_article
from telegram_bot import send_poster_album, split_message
from tmdb import enrich_films
app = Flask(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

INFO_MESSAGE = """
🎬 <b>Streaming Radar</b>

Your weekly guide to what's new in streaming.

Discover the latest movie releases across streaming platforms — from subscription premieres to digital rentals and purchases.

Every Monday, get a curated digest with movie details, cast, directors, plot summaries, and where to watch.

Less scrolling. More watching. 🍿

Movie data and posters: <a href="https://www.themoviedb.org/">TMDB</a>.
This product uses the TMDB API but is not endorsed or certified by TMDB.
"""

WELCOME_MESSAGE = """
🎬 <b>Welcome to Streaming Radar!</b>

You are now subscribed to our weekly newsletter.

Every Monday, I'll send you a curated digest of new full-length movies available on streaming platforms.

You'll get movie details, cast, directors, plot summaries, and where to watch.

Less scrolling. More watching. 🍿

Send /latest anytime to get this week's digest.

To unsubscribe, send /stop.
"""

LATEST_ERROR_MESSAGE = "Sorry, I could not load the latest digest right now. Please try again later."
RANDOM_ERROR_MESSAGE = "Sorry, I could not pick a movie right now. Please try again later."

STOP_MESSAGE = """
You have been unsubscribed from Streaming Radar.

You won't receive any more weekly digests.

If you change your mind, just send /start. 🎬
"""


def _telegram_request(method, payload):
    if not BOT_TOKEN:
        raise RuntimeError("Bot token is not configured")

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
            json=payload,
            timeout=15
        )
    except requests.RequestException as error:
        # Avoid logging the token-bearing request URL from requests exceptions.
        raise RuntimeError(
            f"Telegram {method} request failed ({type(error).__name__})"
        ) from None

    try:
        result = response.json()
    except ValueError:
        result = {}

    if not response.ok or not result.get("ok"):
        description = result.get("description") or "Unknown Telegram API error"
        if BOT_TOKEN and BOT_TOKEN in description:
            description = description.replace(BOT_TOKEN, "[redacted]")
        raise RuntimeError(
            f"Telegram {method} failed (HTTP {response.status_code}): {description}"
        )

    return result.get("result")


def send_message(chat_id, message):
    return _telegram_request(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
    )


def edit_message(chat_id, message_id, message):
    return _telegram_request(
        "editMessageText",
        {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": message,
            "parse_mode": "HTML"
        }
    )


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


def get_latest_films():
    article_url = find_latest_weekly_article()
    films = parse_article(article_url)
    if not films:
        raise ValueError("The latest article contains no movie releases")

    try:
        films = enrich_films(films)
    except Exception:
        app.logger.exception("TMDB enrichment failed; using article details")

    return films


def build_latest_digest():
    films = get_latest_films()
    return films, split_message(format_digest(films))


def build_latest_digest_messages():
    return build_latest_digest()[1]


def build_random_pick():
    film = random.choice(get_latest_films())
    release_date = (film.get("release_date") or "Date unavailable").upper()
    message = (
        "<b>🎲 Your random pick</b>\n\n"
        f"<b>{release_date}</b>\n\n"
        f"{format_film(film)}"
    )
    return film, split_message(message)


def build_random_pick_messages():
    return build_random_pick()[1]


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

    expected_secret = hashlib.sha256(WEBHOOK_SECRET.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(received_secret, expected_secret):
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

    elif command == "/latest" and telegram_id:

        if chat.get("type") != "private":
            return "OK", 200

        loading_message = None
        try:
            loading_message = send_message(
                chat_id,
                "⏳ Working on it…"
            )
            films, messages = build_latest_digest()
            posters_sent = False
            try:
                posters_sent = send_poster_album(chat_id, films)
            except Exception as error:
                app.logger.warning(
                    "Poster album failed; continuing with latest digest (%s)",
                    type(error).__name__
                )
            for digest_message in messages:
                send_message(chat_id, digest_message)
            status_message = (
                "✅ Your latest digest is ready — posters and details are below."
                if posters_sent else
                "✅ Your latest digest is ready — details are below."
            )
            try:
                edit_message(
                    chat_id,
                    loading_message["message_id"],
                    status_message
                )
            except Exception:
                app.logger.exception("Failed to update the latest-digest status")
        except Exception:
            app.logger.exception("Failed to send the latest digest")
            if loading_message:
                try:
                    edit_message(
                        chat_id,
                        loading_message["message_id"],
                        LATEST_ERROR_MESSAGE
                    )
                except Exception:
                    app.logger.exception("Failed to update the latest-digest status")
                    send_message(chat_id, LATEST_ERROR_MESSAGE)
            else:
                send_message(chat_id, LATEST_ERROR_MESSAGE)

    elif command == "/random" and telegram_id:

        if chat.get("type") != "private":
            return "OK", 200

        loading_message = None
        try:
            loading_message = send_message(chat_id, "⏳ Working on it…")
            film, messages = build_random_pick()
            posters_sent = False
            try:
                posters_sent = send_poster_album(chat_id, [film])
            except Exception as error:
                app.logger.warning(
                    "Poster send failed; continuing with random pick (%s)",
                    type(error).__name__
                )
            for random_message in messages:
                send_message(chat_id, random_message)
            status_message = (
                "✅ Your random pick is ready — poster and details are below."
                if posters_sent else
                "✅ Your random pick is ready — details are below."
            )
            try:
                edit_message(
                    chat_id,
                    loading_message["message_id"],
                    status_message
                )
            except Exception:
                app.logger.exception("Failed to update the random-pick status")
        except Exception:
            app.logger.exception("Failed to send a random movie pick")
            if loading_message:
                try:
                    edit_message(
                        chat_id,
                        loading_message["message_id"],
                        RANDOM_ERROR_MESSAGE
                    )
                except Exception:
                    app.logger.exception("Failed to update the random-pick status")
                    send_message(chat_id, RANDOM_ERROR_MESSAGE)
            else:
                send_message(chat_id, RANDOM_ERROR_MESSAGE)

    elif command == "/info":

        send_message(chat_id, INFO_MESSAGE)

    return "OK", 200

