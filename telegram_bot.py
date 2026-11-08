
import os
import requests
from dotenv import load_dotenv

from parser import parse_article
from formatter import format_digest, SOURCE_URL

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


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


def send_telegram_message(text):
    if not TOKEN:
        raise ValueError("Не найден TELEGRAM_BOT_TOKEN в файле .env")

    if not CHAT_ID:
        raise ValueError("Не найден TELEGRAM_CHAT_ID в файле .env")

    messages = split_message(text)

    for message in messages:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

        response = requests.post(
            url,
            json={
                "chat_id": CHAT_ID,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=30,
        )

        response.raise_for_status()

        result = response.json()

        if not result.get("ok"):
            raise RuntimeError(f"Ошибка Telegram: {result}")

    print(f"Успешно отправлено сообщений: {len(messages)}")


if __name__ == "__main__":
    films = parse_article(SOURCE_URL)
    message = format_digest(films)
    send_telegram_message(message)