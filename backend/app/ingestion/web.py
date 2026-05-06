import re
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup


@dataclass(frozen=True)
class WebpageContent:
    url: str
    title: str
    html: str
    text: str


def fetch_webpage(url: str, timeout_seconds: int = 20) -> WebpageContent:
    response = requests.get(
        url,
        timeout=timeout_seconds,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
            )
        },
    )
    response.raise_for_status()
    response.encoding = response.encoding or response.apparent_encoding
    html = response.text
    title, text = extract_title_and_text(html)
    return WebpageContent(url=url, title=title or url, html=html, text=text)


def extract_title_and_text(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg", "canvas"]):
        tag.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = normalize_text(soup.title.string)

    main = soup.find("article") or soup.find("main") or soup.body or soup
    paragraphs = []
    for tag in main.find_all(["h1", "h2", "h3", "p", "li", "td", "th"], recursive=True):
        text = normalize_text(tag.get_text(" ", strip=True))
        if text and len(text) >= 2:
            paragraphs.append(text)

    if not paragraphs:
        paragraphs.append(normalize_text(main.get_text(" ", strip=True)))

    return title, "\n".join(dict.fromkeys(paragraphs))


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
