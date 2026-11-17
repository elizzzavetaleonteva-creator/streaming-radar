
import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()

TMDB_ACCESS_TOKEN = os.getenv("TMDB_ACCESS_TOKEN")
TMDB_BASE_URL = "https://api.themoviedb.org/3"


def normalize_title(title):
    return re.sub(r"[^a-z0-9]", "", title.lower())


def get_movie_details(title):
    if not TMDB_ACCESS_TOKEN:
        raise ValueError("TMDB_ACCESS_TOKEN is not configured")

    headers = {
        "Authorization": f"Bearer {TMDB_ACCESS_TOKEN}",
        "accept": "application/json"
    }

    search_response = requests.get(
        f"{TMDB_BASE_URL}/search/movie",
        headers=headers,
        params={
            "query": title,
            "language": "en-US"
        },
        timeout=20
    )
    search_response.raise_for_status()

    results = search_response.json().get("results", [])

    if not results:
        return None

    normalized_source = normalize_title(title)

    movie = next(
        (
            item for item in results
            if normalized_source in (
                normalize_title(item.get("title", "")),
                normalize_title(item.get("original_title", ""))
            )
        ),
        None
    )

    if not movie:
        return None

    details_response = requests.get(
        f"{TMDB_BASE_URL}/movie/{movie['id']}",
        headers=headers,
        params={
            "append_to_response": "credits",
            "language": "en-US"
        },
        timeout=20
    )
    details_response.raise_for_status()

    details = details_response.json()
    credits = details.get("credits", {})

    directors = [
        person["name"]
        for person in credits.get("crew", [])
        if person.get("job") == "Director"
    ]

    cast = [
        person["name"]
        for person in credits.get("cast", [])[:10]
    ]

    poster_path = details.get("poster_path")

    return {
        "original_title": details.get("original_title") or title,
        "release_date": details.get("release_date", ""),
        "poster_url": (
            f"https://image.tmdb.org/t/p/w500{poster_path}"
            if poster_path else ""
        ),
        "original_language": details.get("original_language", ""),
        "director": ", ".join(directors),
        "cast": ", ".join(cast),
        "synopsis": details.get("overview", "")
    }
def enrich_films(films):
    enriched_films = []

    for film in films:
        tmdb_data = get_movie_details(film["title"])

        if tmdb_data:
            film = film.copy()

            for field in [
                "original_title",
                "poster_url",
                "director",
                "cast",
                "synopsis"
            ]:
                if tmdb_data.get(field):
                    film[field] = tmdb_data[field]

        enriched_films.append(film)

    return enriched_films