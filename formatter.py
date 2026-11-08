
SOURCE_URL = "https://whentostream.com/whats-streaming-this-week-11-8-11-15/"


def format_film(film):
    release_type = film["release_type"]
    platform = film["platform"]

    if release_type == "subscription":
        release_label = f"📺 {platform} · Подписка"

    elif release_type == "digital_purchase":
        release_label = f"💳 Покупка · {platform}"

    elif release_type == "digital_rental":
        release_label = f"🎬 Аренда · {platform}"

    elif release_type == "digital_purchase_and_rental":
        release_label = f"💳 Покупка / аренда · {platform}"

    else:
        release_label = platform

    lines = [
        f"<b>{film['title']}</b>",
        release_label,
    ]

    if film.get("director"):
        lines.append(f"Режиссёр: {film['director']}")

    if film.get("cast"):
        lines.append(f"Актёры: {film['cast']}")

    if film.get("synopsis"):
        lines.append(film["synopsis"])

    return "\n".join(lines)



def format_digest(films, source_url=SOURCE_URL):
    if not films:
        return "На этой неделе новых релизов не найдено."

    lines = [
        "🎬 <b>STREAMING RADAR</b>",
        "",
        f"Найдено фильмов: {len(films)}",
        "",
    ]

    current_date = None

    for film in films:
        release_date = film.get("release_date") or "Дата не указана"

        if release_date != current_date:
            current_date = release_date
            lines.append(f"\n📅 <b>{current_date}</b>\n")

        lines.append(format_film(film))
        lines.append("")

    lines.append(
       f"🔗 <a href=\"{source_url}\">Источник: When to Stream</a>"
    )

    return "\n".join(lines) 
if __name__ == "__main__":
    from parser import parse_article

    films = parse_article(SOURCE_URL)
    message = format_digest(films)

    print(message)

