
SOURCE_URL = "https://whentostream.com/whats-streaming-this-week-11-8-11-15/"


def format_film(film):
    release_type = film["release_type"]
    platform = film["platform"]

    if release_type == "subscription":
        release_label = f"{platform} · Subscription"
    elif release_type == "digital_purchase":
        release_label = "Digital purchase"
    elif release_type == "digital_rental":
        release_label = "Digital rental"
    elif release_type == "digital_purchase_and_rental":
        release_label = "Digital purchase / rental"
    else:
        release_label = platform

    original_title = film.get("original_title") or film["title"]

    lines = [
        f"<b>{original_title}</b>",
        release_label,
    ]

    if film.get("director"):
        lines.append(f"Director: {film['director']}")

    if film.get("cast"):
        cast_members = [name.strip() for name in film["cast"].split(",")]
        cast_text = ", ".join(cast_members[:5])
        lines.append(f"Cast: {cast_text}")

    if film.get("synopsis"):
        lines.append(f"<i>{film['synopsis']}</i>")

    return "\n".join(lines)


def format_digest(films, source_url=SOURCE_URL):
    if not films:
        return "No new releases found this week."

    blocks = [
        "<b>🎬 STREAMING RADAR</b>\n"
        f"<i>{len(films)} movies · This week</i>"
    ]

    current_date = None

    for film in films:
        release_date = film.get("release_date") or "Date unavailable"

        if release_date != current_date:
            current_date = release_date
            blocks.append(f"<b>{current_date.upper()}</b>")

        blocks.append(format_film(film))

    blocks.append(
        f'<a href="{source_url}">Source: When to Stream</a>'
    )

    return "\n\n".join(blocks)


if __name__ == "__main__":
    from parser import find_latest_weekly_article, parse_article
    from tmdb import enrich_films

    article_url = find_latest_weekly_article()
    films = parse_article(article_url)
    films = enrich_films(films)

    message = format_digest(films, article_url)

    print(message)
