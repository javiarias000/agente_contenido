from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup


async def fetch_html(url: str, timeout: float = 30.0) -> tuple[str, str]:
    """Returns (html_text, final_url) following redirects."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Referer": "https://www.google.com/",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
    }
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.text, str(resp.url)


def extract_og_tags(soup: BeautifulSoup) -> dict[str, str]:
    """Extract Open Graph meta tags (useful for social media profiles)."""
    og_data = {}
    for meta in soup.find_all("meta", property=re.compile(r"^og:")):
        prop = meta.get("property", "").replace("og:", "")
        content = meta.get("content", "")
        if content and prop not in og_data:
            og_data[prop] = content
    return og_data


def extract_logo_urls(soup: BeautifulSoup, base_url: str) -> list[str]:
    candidates = []
    for img in soup.find_all("img"):
        src = img.get("src", "")
        alt = img.get("alt", "").lower()
        cls = " ".join(img.get("class", [])).lower()
        if any(k in src.lower() or k in alt or k in cls for k in ("logo", "brand", "mark")):
            full = urljoin(base_url, src)
            candidates.append(full)
    # Fallback: largest image in <header>
    if not candidates:
        header = soup.find("header") or soup
        for img in header.find_all("img"):
            src = img.get("src", "")
            if src:
                candidates.append(urljoin(base_url, src))
    return candidates[:5]


def extract_css_urls(soup: BeautifulSoup, base_url: str) -> list[str]:
    urls = []
    for link in soup.find_all("link", rel=lambda r: r and "stylesheet" in r):
        href = link.get("href", "")
        if href:
            urls.append(urljoin(base_url, href))
    return urls[:10]


def extract_inline_styles(soup: BeautifulSoup) -> str:
    parts = []
    for tag in soup.find_all("style"):
        parts.append(tag.get_text())
    return "\n".join(parts)


def extract_css_colors(css_text: str) -> list[str]:
    hex_colors = re.findall(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", css_text)
    seen: set[str] = set()
    result = []
    for c in hex_colors:
        norm = c.lower()
        if norm not in seen and norm not in ("#fff", "#ffffff", "#000", "#000000"):
            seen.add(norm)
            result.append(norm)
    return result[:20]


def extract_font_families(css_text: str) -> list[str]:
    raw = re.findall(r"font-family\s*:\s*([^;}{]+)", css_text, re.IGNORECASE)
    fonts = []
    for entry in raw:
        primary = entry.split(",")[0].strip().strip("'\"")
        if primary and primary not in fonts and "inherit" not in primary.lower():
            fonts.append(primary)
    return fonts[:10]


def extract_text_samples(soup: BeautifulSoup, max_chars: int = 2000) -> str:
    for tag in soup(["script", "style", "noscript", "nav", "footer"]):
        tag.decompose()
    texts = []
    total = 0
    for tag in ("h1", "h2", "p"):
        for el in soup.find_all(tag):
            t = el.get_text(separator=" ", strip=True)
            if len(t) > 30:
                texts.append(t)
                total += len(t)
                if total >= max_chars:
                    break
        if total >= max_chars:
            break
    return " | ".join(texts)


async def fetch_css_text(urls: list[str], timeout: float = 10.0) -> str:
    parts = []
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/css,*/*;q=0.1",
        "Referer": "https://www.google.com/",
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        for url in urls[:5]:
            try:
                r = await client.get(url, headers=headers)
                r.raise_for_status()
                parts.append(r.text[:50_000])
            except Exception:
                pass
    return "\n".join(parts)
