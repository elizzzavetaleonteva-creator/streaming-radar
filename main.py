import json
from pathlib import Path

from parser import find_latest_weekly_article, parse_article
from formatter import format_digest
from telegram_bot import send_telegram_message
from tmdb import enrich_films


STATE_FILE = Path(__file__).parent / "data" / "last_article.json"


def main():
    print("Запускаем Streaming Radar...")

    # Находим свежую еженедельную статью
    article_url = find_latest_weekly_article()
    print(f"Найдена статья: {article_url}")

    # Загружаем информацию о последней отправленной статье
    if STATE_FILE.exists():
        with STATE_FILE.open("r", encoding="utf-8") as file:
            state = json.load(file)
    else:
        state = {}

    # Проверяем, не отправляли ли эту статью раньше
    if state.get("last_article_url") == article_url:
        print("Эта статья уже отправлялась. Повторная отправка не нужна.")
        return

    # Парсим статью и формируем дайджест
    films = parse_article(article_url)
    print(f"Найдено фильмов: {len(films)}")

    # Обогащаем фильмы данными TMDB
    films = enrich_films(films)
    print("Фильмы обогащены данными TMDB")

    message = format_digest(films, article_url)

    # Отправляем дайджест в Telegram
    send_telegram_message(message)

    # Сохраняем URL только после успешной отправки
    with STATE_FILE.open("w", encoding="utf-8") as file:
        json.dump(
            {"last_article_url": article_url},
            file,
            ensure_ascii=False,
            indent=2
        )

    print("Streaming Radar завершил работу!")


if __name__ == "__main__":
    main()