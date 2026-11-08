
import requests
from bs4 import BeautifulSoup

URL = "https://whentostream.com/whats-streaming-this-week-11-8-11-15/"

headers = {
    "User-Agent": "Mozilla/5.0 (compatible; StreamingRadar/1.0)"
}

response = requests.get(URL, headers=headers, timeout=30)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")
article = soup.find("article")

if not article:
    print("Статья не найдена")
else:
    elements = article.find_all(
        ["h1", "h2", "h3", "h4", "p"],
        recursive=True
    )

    for i, element in enumerate(elements):
        text = element.get_text(" ", strip=True)

        if text:
            print(f"{i} | {element.name} | {text}")
