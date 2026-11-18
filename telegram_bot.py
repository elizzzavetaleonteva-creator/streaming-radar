

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "").strip()


def split_message(text, max_length=4000):
    """Split a formatted digest between complete film cards."""
    if max_length <= 0:
        raise ValueError("max_length must be positive")

    blocks = text.split("\n\n")
    if len(blocks) == 1:
        return [text] if len(text) <= max_length else _oversized_block(text)

    header = blocks[0]
    source = None
    if blocks[-1].startswith("<a href="):
        source = blocks.pop()

    # A film card starts with a bold title and contains further lines. A date
    # heading is a standalone bold block and is kept with the next card.
    cards = []
    pending_date = None
    for block in blocks[1:]:
        if block.startswith("<b>") and "\n" not in block:
            pending_date = block if pending_date is None else pending_date + "\n\n" + block
            continue
        if block:
            card = (pending_date + "\n\n" if pending_date else "") + block
            cards.append(card)
            pending_date = None
    if pending_date:
        # Keep an unusual trailing heading intact rather than dropping it.
        cards.append(pending_date)

    messages = []
    current = header
    for card in cards:
        candidate = current + "\n\n" + card
        if len(candidate) <= max_length:
            current = candidate
            continue
        if current != header:
            messages.append(current)
            current = card
        else:
            # If the first card does not fit with the header, retain it whole
            # in its own message and leave the header in the first message.
            if len(header) <= max_length:
                messages.append(header)
                current = card
            else:
                raise ValueError("Digest header exceeds Telegram message limit")
        if len(current) > max_length:
            raise ValueError("A complete film card exceeds Telegram message limit")

    if source:
        candidate = current + "\n\n" + source
        if len(candidate) <= max_length:
            current = candidate
        else:
            if current:
                messages.append(current)
            if len(source) > max_length:
                raise ValueError("Digest source exceeds Telegram message limit")
            current = source

    if current:
        messages.append(current)
    return messages


def _oversized_block(block):
    raise ValueError("A complete digest block exceeds Telegram message limit")


def get_active_subscribers():
    if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
        raise ValueError("Не настроены данные Supabase")

    url = f"{SUPABASE_URL}/rest/v1/subscribers"

    headers = {
        "apikey": SUPABASE_SECRET_KEY,
        "Content-Type": "application/json",
    }

    response = requests.get(
        url,
        params={
            "select": "telegram_id",
            "is_active": "eq.true",
        },
        headers=headers,
        timeout=30,
    )

    response.raise_for_status()

    subscribers = response.json()

    return [subscriber["telegram_id"] for subscriber in subscribers]


def _telegram_post(method, payload, timeout=30):
    if not TOKEN:
        raise ValueError("Не найден TELEGRAM_BOT_TOKEN")

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/{method}",
            json=payload,
            timeout=timeout,
        )
    except requests.RequestException as error:
        # Do not let requests print the token-bearing URL in the exception.
        raise RuntimeError(
            f"Telegram {method} request failed ({type(error).__name__})"
        ) from None

    try:
        result = response.json()
    except ValueError:
        result = {}

    if not response.ok or not result.get("ok"):
        description = result.get("description") or "Unknown Telegram API error"
        if TOKEN and TOKEN in description:
            description = description.replace(TOKEN, "[redacted]")
        raise RuntimeError(
            f"Telegram {method} failed (HTTP {response.status_code}): {description}"
        )

    return result.get("result")


def send_one_message(chat_id, text):
    _telegram_post(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
    )


def send_one_photo(chat_id, photo_url):
    _telegram_post(
        "sendPhoto",
        {
            "chat_id": chat_id,
            "photo": photo_url,
        },
    )


def send_poster_photos(chat_id, films):
    posters = [film.get("poster_url") for film in films if film.get("poster_url")]
    sent = 0

    for index, photo_url in enumerate(posters, start=1):
        if index > 1:
            time.sleep(1)
        try:
            send_one_photo(chat_id, photo_url)
            sent += 1
        except Exception as error:
            print(f"Poster {index} failed; skipping: {error}")

    return sent > 0


def send_poster_album(chat_id, films):
    posters = [
        film.get("poster_url")
        for film in films
        if film.get("poster_url")
    ][:10]

    if not posters:
        return False

    if len(posters) == 1:
        send_one_photo(chat_id, posters[0])
    else:
        media = [
            {"type": "photo", "media": photo_url}
            for photo_url in posters
        ]
        _telegram_post(
            "sendMediaGroup",
            {"chat_id": chat_id, "media": media},
            timeout=60,
        )
    time.sleep(0.05)
    return True


def send_telegram_message(text, films=None):
    if not TOKEN:
        raise ValueError("Не найден TELEGRAM_BOT_TOKEN")

    subscribers = get_active_subscribers()

    if not subscribers:
        print("Активных подписчиков пока нет.")
        return

    messages = split_message(text)

    successful = 0
    failed = 0

    print(f"Активных подписчиков: {len(subscribers)}")

    for telegram_id in subscribers:
        try:
            if films:
                try:
                    send_poster_album(telegram_id, films)
                except Exception as error:
                    print(
                        "Poster album failed; continuing with digest "
                        f"({type(error).__name__})"
                    )

            for message in messages:
                send_one_message(telegram_id, message)
                time.sleep(0.05)

            successful += 1

        except Exception:
            failed += 1
            print("Ошибка отправки одному из подписчиков")

        time.sleep(0.05)

    print(f"Успешно: {successful}")
    print(f"Ошибок: {failed}")

    if failed:
        raise RuntimeError(
            f"Не удалось отправить дайджест {failed} подписчикам"
        )
