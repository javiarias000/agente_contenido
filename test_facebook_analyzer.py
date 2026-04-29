#!/usr/bin/env python
"""Test script to analyze a Facebook business page."""

import asyncio
import json
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from api.config import settings
from api.events import EventBus
from skills.brand_analyzer import BrandAnalyzer


class SimpleEventBus(EventBus):
    """Simple event bus for testing."""
    async def emit(self, event_type: str, message: str = "", data: dict = None):
        print(f"[{event_type}] {message}")
        if data:
            print(f"  Data: {json.dumps(data, indent=2, ensure_ascii=False)[:200]}...")


async def test_facebook_analyzer():
    """Test the Facebook brand analyzer."""

    # Page info
    page_id = "1130355880150943"
    url = f"https://www.facebook.com/pg/{page_id}"

    print(f"\n{'='*60}")
    print(f"Testing Facebook Brand Analyzer")
    print(f"Page ID: {page_id}")
    print(f"Token available: {bool(settings.facebook_access_token)}")
    print(f"{'='*60}\n")

    if not settings.facebook_access_token:
        print("❌ Error: FACEBOOK_ACCESS_TOKEN not configured in .env")
        return

    # Create event bus and analyzer
    event_bus = SimpleEventBus()
    analyzer = BrandAnalyzer(
        event_bus=event_bus,
        run_id="test_run_001",
        db_session=None,
    )

    # Run analysis
    try:
        result = await analyzer.run(
            inputs={
                "url": url,
                "name": "Test Facebook Brand",
            },
            interactive=False,
        )

        print(f"\n{'='*60}")
        print("✅ Analysis completed successfully!")
        print(f"{'='*60}\n")

        if result.outputs.get("profile"):
            profile = result.outputs["profile"]
            print("📊 Brand Profile Summary:")
            print(f"  Name: {profile.get('name')}")
            print(f"  Business Type: {profile.get('business_type')}")
            print(f"  Tone: {profile.get('tone_of_voice')}")
            print(f"  Target Audience: {profile.get('target_audience')}")
            print(f"  Brand Values: {profile.get('brand_values')}")
            print(f"  Style Notes: {profile.get('style_notes')[:100]}...")
            print(f"  Content Suggestions: {profile.get('content_suggestions')}")

            # Save full profile
            profile_path = Path("test_profile_output.json")
            with open(profile_path, "w", encoding="utf-8") as f:
                json.dump(profile, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Full profile saved to: {profile_path}")

    except Exception as e:
        print(f"\n❌ Error during analysis:")
        print(f"  {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_facebook_analyzer())
