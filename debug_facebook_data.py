#!/usr/bin/env python
"""Debug script to see raw Facebook data."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from api.config import settings
from skills.utils.facebook_scraper import fetch_facebook_page_data_graph_api, extract_facebook_business_context


async def debug_facebook():
    """Debug: print raw Facebook API data."""

    page_id = "1130355880150943"

    print(f"\n{'='*60}")
    print(f"Debugging Facebook Data Extraction")
    print(f"Page ID: {page_id}")
    print(f"{'='*60}\n")

    if not settings.facebook_access_token:
        print("❌ Error: FACEBOOK_ACCESS_TOKEN not configured")
        return

    try:
        fb_data = await fetch_facebook_page_data_graph_api(
            page_id,
            settings.facebook_access_token,
        )

        print("📋 PAGE INFO:")
        print(json.dumps(fb_data.get("page_info", {}), indent=2, ensure_ascii=False))

        print("\n📸 PHOTOS (first 3):")
        for i, photo in enumerate(fb_data.get("photos", [])[:3]):
            print(f"\n  Photo {i+1}:")
            print(f"    URL: {photo.get('source', 'N/A')[:100]}...")
            print(f"    Name: {photo.get('name', 'N/A')[:100]}")
            print(f"    Likes: {photo.get('likes', {}).get('summary', {}).get('total_count', 0)}")

        print("\n📝 POSTS (first 5):")
        for i, post in enumerate(fb_data.get("posts", [])[:5]):
            print(f"\n  Post {i+1}:")
            print(f"    Message: {post.get('message', post.get('story', 'N/A'))[:150]}...")
            print(f"    Created: {post.get('created_time', 'N/A')}")
            print(f"    Image: {post.get('full_picture', 'N/A')[:80] if post.get('full_picture') else 'No image'}...")
            print(f"    Likes: {post.get('likes', {}).get('summary', {}).get('total_count', 0)}")

        print("\n📄 BUSINESS CONTEXT:")
        context = extract_facebook_business_context(fb_data)
        print(context)

    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_facebook())
