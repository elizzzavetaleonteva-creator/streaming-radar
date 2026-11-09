
SOURCE_URL = "https://whentostream.com/whats-streaming-this-week-11-8-11-15/"


def format_film(film):
    release_type = film["release_type"]
    platform = film["platform"]

    if release_type == "subscription":
        release_label = f" {platform} · Subscription"

    elif release_type == "digital_purchase":
        release_label = f" {platform} · Digital purchase"

    elif release_type == "digital_rental":
        release_label = f" {platform} · Digital rental"

    elif release_type == "digital_purchase_and_rental":
        release_label = f" {platform} · Digital purchase / rental"

    else:
        release_label = platform

    original_title = film.get("original_title") or film["title"]

    lines = [
        f"<b>{original_title}</b>",
        release_label,
    ]

    if film.get("director"):
        lines.append(f"<b>Director:</b> {film['director']}")

    if film.get("cast"):
        lines.append(f"<b>Cast:</b> {film['cast']}")

    if film.get("synopsis"):
        lines.append("")
        lines.append("<b>Plot</b>")
        lines.append(film["synopsis"])

    return "\n".join(lines)


def format_digest(films, source_url=SOURCE_URL):
    if not films:
        return "No new releases found this week."

    lines = [
        "🎬 <b>STREAMING RADAR</b>",
        "",
        f"Found {len(films)} movies:",
        "",
    ]

    current_date = None

    for film in films:
        release_date = film.get("release_date") or "Date unavailable"

        if release_date != current_date:
            current_date = release_date
            lines.append(f"\n <b>{current_date}</b>\n")

        lines.append(format_film(film))
        lines.append("")

    lines.append(
        f' <a href="{source_url}">Source: When to Stream</a>'
    )

    return "\n".join(lines)


if __name__ == "__main__":
    from parser import parse_article
    from tmdb import enrich_films

    films = parse_article(SOURCE_URL)
    films = enrich_films(films)

    message = format_digest(films)

    print(message)
