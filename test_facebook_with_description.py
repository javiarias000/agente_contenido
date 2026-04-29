#!/usr/bin/env python
"""Test Facebook analyzer with manual business description."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from api.config import settings
from api.events import EventBus
from skills.brand_analyzer import BrandAnalyzer


class SimpleEventBus(EventBus):
    """Simple event bus for testing."""
    async def emit(self, event_type: str, message: str = "", data: dict = None):
        print(f"[{event_type}] {message}")


async def test_with_description():
    """Test the Facebook analyzer with correct business description."""

    page_id = "1130355880150943"
    url = f"https://www.facebook.com/pg/{page_id}"

    business_description = """
    Mi Idea es una empresa especializada en corte láser y diseño de estructuras.
    Trabaja con MDF, acrílico y otros materiales.
    Servicios principales:
    - Corte láser de precisión en MDF, acrílico, madera
    - Diseño y fabricación de cajas de madera y MDF
    - Diseño de estructuras en cartón
    - Productos personalizados según especificaciones del cliente
    - Enfoque en diseño creativo y manufactura de calidad
    """

    print(f"\n{'='*60}")
    print(f"Testing Facebook Brand Analyzer with Business Description")
    print(f"Page ID: {page_id}")
    print(f"Business: {business_description.strip()}")
    print(f"{'='*60}\n")

    event_bus = SimpleEventBus()
    analyzer = BrandAnalyzer(
        event_bus=event_bus,
        run_id="test_run_with_desc",
        db_session=None,
    )

    try:
        result = await analyzer.run(
            inputs={
                "url": url,
                "name": "Mi Idea",
                "business_description": business_description,
            },
            interactive=False,
        )

        print(f"\n{'='*60}")
        print("✅ Analysis completed!")
        print(f"{'='*60}\n")

        if result.outputs.get("profile"):
            profile = result.outputs["profile"]

            print("📊 BRAND ANALYSIS RESULTS:")
            print(f"\n  Business Type: {profile.get('business_type')}")
            print(f"\n  Tone: {profile.get('tone_of_voice')}")
            print(f"\n  Target Audience: {profile.get('target_audience')}")
            print(f"\n  Brand Values:")
            for val in profile.get('brand_values', []):
                print(f"    - {val}")
            print(f"\n  Style Notes: {profile.get('style_notes')}")
            print(f"\n  Content Suggestions:")
            for i, sug in enumerate(profile.get('content_suggestions', []), 1):
                print(f"    {i}. {sug}")
            print(f"\n  Character: {profile.get('character_anchor')}")

            # Save full profile
            profile_path = Path("brands/mi-idea.json")
            profile_path.parent.mkdir(exist_ok=True)
            with open(profile_path, "w", encoding="utf-8") as f:
                json.dump(profile, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Profile saved to: {profile_path}")

    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_with_description())
