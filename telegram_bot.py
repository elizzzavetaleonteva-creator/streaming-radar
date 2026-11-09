

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "").strip()


def split_message(text, max_length=4000):
    paragraphs = text.split("\n\n")
    messages = []
    current_message = ""

    for paragraph in paragraphs:
        candidate = (
            current_message + "\n\n" + paragraph
            if current_message
            else paragraph
        )

        if len(candidate) <= max_length:
            current_message = candidate
        else:
            if current_message:
                messages.append(current_message)
            current_message = paragraph

    if current_message:
        messages.append(current_message)

    return messages


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
