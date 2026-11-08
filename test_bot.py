import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise ValueError("Не найден TELEGRAM_BOT_TOKEN в файле .env")

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

data = {
    "chat_id": "7440713711",
    "text": "🎬 Привет! Это Streaming Radar.\n\nБот успешно подключён. Скоро здесь появятся новинки кино!"
}

response = requests.post(url, json=data)

print("Ответ Telegram:")
print(response.json())