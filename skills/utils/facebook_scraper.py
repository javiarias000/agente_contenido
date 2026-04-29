from __future__ import annotations

import httpx
from typing import Any


async def fetch_facebook_page_data(
    page_id: str,
    access_token: str,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """
    Fetch comprehensive page data from Facebook Graph API.
    Returns: {name, about, category, description, picture_url, posts, photos}
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    async with httpx.AsyncClient(timeout=timeout) as client:
        # Fetch page info
        page_info_url = f"https://graph.instagram.com/v18.0/{page_id}"
        params = {
            "fields": "id,name,about,description,category,website,profile_picture_url,followers_count",
            "access_token": access_token,
        }
        resp = await client.get(page_info_url, params=params)
        resp.raise_for_status()
        page_data = resp.json()

        # Fetch recent posts
        posts_url = f"https://graph.instagram.com/v18.0/{page_id}/media"
        posts_params = {
            "fields": "id,caption,media_type,media_url,timestamp,like_count,comments_count",
            "limit": 12,
            "access_token": access_token,
        }
        posts_resp = await client.get(posts_url, params=posts_params)
        posts_data = posts_resp.json() if posts_resp.status_code == 200 else {"data": []}

        return {
            "page_info": page_data,
            "posts": posts_data.get("data", []),
        }


async def fetch_facebook_page_data_graph_api(
    page_id: str,
    access_token: str,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """
    Fetch comprehensive page data from Facebook Graph API (not Instagram).
    Returns: {name, about, category, description, picture_url, posts, photos}
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    async with httpx.AsyncClient(timeout=timeout) as client:
        # Fetch page info - use only stable fields
        page_info_url = f"https://graph.facebook.com/v18.0/{page_id}"
        params = {
            "fields": "id,name,about,description,category,website,picture,followers_count,fan_count",
            "access_token": access_token,
        }
        resp = await client.get(page_info_url, params=params)
        resp.raise_for_status()
        page_data = resp.json()

        # Fetch recent posts with images
        posts_url = f"https://graph.facebook.com/v18.0/{page_id}/posts"
        posts_params = {
            "fields": "id,message,story,type,created_time,permalink_url,picture,full_picture,likes.summary(true).limit(0),comments.summary(true).limit(0)",
            "limit": 20,
            "access_token": access_token,
        }
        posts_resp = await client.get(posts_url, params=posts_params)
        posts_data = posts_resp.json() if posts_resp.status_code == 200 else {"data": []}

        # Fetch photos
        photos_url = f"https://graph.facebook.com/v18.0/{page_id}/photos"
        photos_params = {
            "fields": "id,source,name,created_time,likes.summary(true).limit(0),comments.summary(true).limit(0)",
            "limit": 10,
            "access_token": access_token,
        }
        photos_resp = await client.get(photos_url, params=photos_params)
        photos_data = photos_resp.json() if photos_resp.status_code == 200 else {"data": []}

        return {
            "page_info": page_data,
            "posts": posts_data.get("data", []),
            "photos": photos_data.get("data", []),
        }


def extract_facebook_business_context(page_data: dict[str, Any]) -> str:
    """
    Extract business context from Facebook page data.
    Returns a text summary of what the business does.
    """
    info = page_data.get("page_info", {})
    parts = []

    if info.get("name"):
        parts.append(f"Nombre: {info['name']}")
    if info.get("category"):
        parts.append(f"Categoría: {info['category']}")
    if info.get("about"):
        parts.append(f"Acerca de: {info['about']}")
    if info.get("description"):
        parts.append(f"Descripción: {info['description']}")

    posts = page_data.get("posts", [])[:5]
    if posts:
        post_texts = []
        for post in posts:
            text = post.get("message") or post.get("story", "")
            if text and len(text) > 20:
                post_texts.append(text[:200])
        if post_texts:
            parts.append(f"Posts recientes: {' | '.join(post_texts)}")

    return "\n".join(parts)
