import re
import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import date, timedelta


HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; StreamingRadar/1.0)"
}


def find_latest_weekly_article():

    homepage = "https://whentostream.com/" 

    response = requests.get(
        homepage,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    articles = []

    for link in soup.find_all("a", href=True):

        title = link.get_text(" ", strip=True)
        article_url = urljoin(homepage, link["href"])

        is_weekly_preview = re.search(
            r"what.?s streaming this week",
            title,
            re.IGNORECASE
        ) or re.search(
            r"whats-streaming-this-week",
            article_url,
            re.IGNORECASE
        )
        if not is_weekly_preview:
            continue

        match = re.search(
            r"this-week-(\d{1,2})-(\d{1,2})-(\d{1,2})-(\d{1,2})",
            article_url,
            re.IGNORECASE
        )

        if not match:
            continue

        start_month, start_day, end_month, end_day = map(
            int, match.groups()
        )

        today = date.today()

        article_date = date(
            today.year,
            start_month,
            start_day
        )

        # Учитываем переход между годами
        if article_date < today - timedelta(days=180):
            article_date = article_date.replace(year=today.year + 1)

        elif article_date > today + timedelta(days=180):
            article_date = article_date.replace(year=today.year - 1)
        articles.append((article_date, article_url))

    if not articles:
        raise ValueError(
            "Не удалось найти еженедельные статьи с датами в URL"
        )

    articles.sort(key=lambda article: article[0], reverse=True)

    return articles[0][1]


STREAMING_PLATFORMS = [
    "Netflix",
    "Paramount+",
    "Apple TV",
    "HBO Max",
    "Hulu",
    "Disney+",
    "Amazon Prime Video",
    "Prime Video",
    "Peacock",
    "Shudder",
    "Mubi",
    "Max",
]


def get_release_type(release_info):
    text = release_info.lower()

    if "$" in text:
        has_purchase = "sale" in text
        has_rental = "rental" in text

        if has_purchase and has_rental:
            return "digital_purchase_and_rental"
        elif has_purchase:
            return "digital_purchase"
        elif has_rental:
            return "digital_rental"

        return "unknown"

    return "subscription"


def is_release_info(text):
    if "$" in text:
        return True

    return text.strip() in STREAMING_PLATFORMS


def parse_article(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    article = soup.find("article")

    if not article:
        raise ValueError("Не удалось найти статью")

    films = []
    current_date = None
    current_film = None

    elements = article.find_all(["h2", "p"])

    for element in elements:
        text = element.get_text(" ", strip=True)

        if not text:
            continue

        # Определяем дату
        if element.name == "h2":
            date_match = re.search(
                r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+(.+)",
                text
            )

            if date_match:
                current_date = date_match.group(2)

            continue

        # Проверяем, является ли абзац началом релиза
        if " – " in text:
            title, release_info = text.split(" – ", 1)

            if not is_release_info(release_info):
                continue

            if current_film:
                films.append(current_film)

            current_film = {
                "title": title.strip(),
                "release_date": current_date,
                "platform": release_info.strip(),
                "release_type": get_release_type(release_info),
                "director": "",
                "cast": "",
                "synopsis": ""
            }

            continue

        if not current_film:
            continue

        # Извлекаем режиссёра
        if text.startswith("Director:"):
            current_film["director"] = text.replace(
                "Director:", "", 1
            ).strip()

        # Извлекаем актёров
        elif text.startswith("Cast:"):
            current_film["cast"] = text.replace(
                "Cast:", "", 1
            ).strip()

        # Извлекаем синопсис
        elif text.startswith("Synopsis:"):
            current_film["synopsis"] = text.replace(
                "Synopsis:", "", 1
            ).strip()

    if current_film:
        films.append(current_film)

    return films


if __name__ == "__main__":

    article_url = find_latest_weekly_article()

    print("Найдена статья:", article_url)

    films = parse_article(article_url)

    print(f"\nНАЙДЕНО ФИЛЬМОВ: {len(films)}\n")

    for film in films:
        print("=" * 50)
        print("Название:", film["title"])
        print("Дата:", film["release_date"])
        print("Платформа / цена:", film["platform"])
        print("Тип релиза:", film["release_type"])
        print("Режиссёр:", film["director"])
        print("Актёры:", film["cast"])
        print("Синопсис:", film["synopsis"])
        print()
