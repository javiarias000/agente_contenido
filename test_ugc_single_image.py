#!/usr/bin/env python
"""Test UGC pipeline generating a single image with Mi Idea brand."""

import asyncio
import json
from pathlib import Path
from sqlmodel.ext.asyncio.session import AsyncSession

from api.config import settings
from api.events import EventBus
from pipelines.ugc_pipeline import UGCPipeline


class SimpleEventBus(EventBus):
    """Simple event bus for testing."""

    async def emit(self, event_type: str, message: str = "", data: dict = None):
        if event_type in ("progress", "step_complete", "step_start"):
            print(f"[{event_type.upper()}] {message}")
            if data and "image_path" in data:
                print(f"  📸 Image: {Path(data['image_path']).name}")


async def test_ugc_pipeline():
    """Test UGC pipeline with Mi Idea brand."""

    print(f"\n{'='*60}")
    print(f"Testing UGC Pipeline - Mi Idea Brand")
    print(f"{'='*60}\n")

    # Pipeline inputs
    inputs = {
        "brand_slug": "mi-idea",
        "angle_type": "sales",  # Try sales angle with updated prompt
        "platform": "tiktok",
        "target_duration": 30,  # Short test video
    }

    event_bus = SimpleEventBus()
    pipeline = UGCPipeline(event_bus=event_bus, run_id="test_ugc_001", db_session=None)

    try:
        print("🚀 Iniciando pipeline UGC...\n")

        # Execute pipeline
        result = await pipeline.execute(inputs=inputs, interactive=False)

        print(f"\n{'='*60}")
        print(f"✅ Pipeline Completed!")
        print(f"{'='*60}\n")

        # Check results
        if result.get("status") == "completed":
            # Find the script
            script = result.get("outputs", {}).get("script", {})
            image_paths = result.get("outputs", {}).get("image_paths", [])

            if script:
                print("📝 SCRIPT GENERATED:")
                print(f"  Title: {script.get('title')}")
                print(f"  Hook: {script.get('hook')[:100]}...")
                print(f"  Scenes: {len(script.get('scenes', []))}")
                print(f"  CTA: {script.get('cta')}")
                print(f"  Angle: {script.get('angle_type')}")
                print(f"  Colors detected: {json.dumps(script.get('brand_colors', []), indent=2)}")

            if image_paths:
                print(f"\n🖼️  IMAGES GENERATED: {len(image_paths)}")
                for i, path in enumerate(image_paths, 1):
                    exists = Path(path).exists()
                    size = Path(path).stat().st_size if exists else 0
                    print(f"  {i}. {Path(path).name} ({size:,} bytes) {'✅' if exists else '❌'}")

                # Show first image info
                if image_paths:
                    first_image = image_paths[0]
                    print(f"\n📸 First Scene Visual Description:")
                    first_scene = script.get('scenes', [{}])[0]
                    print(f"  {first_scene.get('visual_description', 'N/A')[:200]}...")

        else:
            print(f"❌ Pipeline failed: {result.get('error_message', 'Unknown error')}")

    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_ugc_pipeline())
