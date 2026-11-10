

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


def send_one_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    response = requests.post(
        url,
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=30,
    )

    response.raise_for_status()

    result = response.json()

    if not result.get("ok"):
        raise RuntimeError(f"Ошибка Telegram: {result}")


def send_telegram_message(text):
    if not TOKEN:
        raise ValueError("Не найден TELEGRAM_BOT_TOKEN")

    subscribers = get_active_subscribers()

    if not subscribers:
        print("Активных подписчиков пока нет.")
        return

    messages = split_message(text)

    successful = 0
    failed = []

    print(f"Активных подписчиков: {len(subscribers)}")

    for telegram_id in subscribers:
        try:
            for message in messages:
                send_one_message(telegram_id, message)
                time.sleep(0.05)

            successful += 1
            print(f"Дайджест отправлен: {telegram_id}")

        except Exception as error:
            failed.append(telegram_id)
            print(f"Ошибка отправки для {telegram_id}: {error}")

        time.sleep(0.05)

    print(f"Успешно: {successful}")
    print(f"Ошибок: {len(failed)}")

    if failed:
        raise RuntimeError(
            f"Не удалось отправить дайджест подписчикам: {failed}"
        )
