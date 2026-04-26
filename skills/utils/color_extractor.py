from __future__ import annotations

import io
from urllib.parse import urlparse

import httpx
from colorthief import ColorThief
from PIL import Image


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"


def _is_neutral(r: int, g: int, b: int) -> bool:
    """Skip near-white and near-black colors."""
    brightness = (r + g + b) / 3
    return brightness > 230 or brightness < 25


async def extract_colors_from_image_url(url: str) -> list[str]:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        img_bytes = resp.content
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        img.thumbnail((300, 300))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        ct = ColorThief(buf)
        palette = ct.get_palette(color_count=8, quality=1)
        colors = []
        for rgb in palette:
            if not _is_neutral(*rgb):
                colors.append(_rgb_to_hex(*rgb))
        return colors[:5]
    except Exception:
        return []


def merge_color_sources(
    image_colors: list[str],
    css_colors: list[str],
) -> dict[str, str | list[str]]:
    """Combine image palette + CSS colors into a structured palette."""
    all_colors = image_colors + [c for c in css_colors if c not in image_colors]
    palette = all_colors[:6]

    result: dict[str, str | list[str]] = {"palette": palette}
    if palette:
        result["primary"] = palette[0]
    if len(palette) > 1:
        result["secondary"] = palette[1]
    if len(palette) > 2:
        result["accent"] = palette[2]
    result["background"] = "#ffffff"
    result["text"] = "#111111"
    return result
