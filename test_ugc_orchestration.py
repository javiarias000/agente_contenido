"""
Orchestration test: Run full UGC pipeline for Mi Idea and validate output.
Claude Code as orchestrator validates quality at each step.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, ".")

from api.config import settings
from api.events import EventBus, PipelineEvent
from pipelines.ugc_pipeline import UGCPipeline
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession as SQLAsyncSession
from sqlmodel import SQLModel
import uuid

class SimpleEventBus(EventBus):
    """Simple event bus for testing."""
    def __init__(self):
        self.events = []

    async def emit(self, event: PipelineEvent):
        self.events.append(event.to_dict())
        print(f"[{event.event_type}] {event.message}")
        if event.data:
            print(f"       Data: {json.dumps(event.data, indent=2)[:200]}...")


async def main():
    print("=" * 80)
    print("🎬 UGC PIPELINE ORCHESTRATION TEST - Mi Idea (Corte Láser)")
    print("=" * 80)
    print()

    # Create event bus and run ID
    event_bus = SimpleEventBus()
    run_id = f"test_ugc_{uuid.uuid4().hex[:8]}"

    print(f"📋 Run ID: {run_id}")
    print(f"🎯 Brand: mi-idea (corte láser y diseño)")
    print(f"📱 Platform: TikTok (60s max)")
    print()

    # Pipeline inputs
    inputs = {
        "brand_slug": "mi-idea",
        "angle_type": "sales",  # Sales-focused UGC
        "platform": "tiktok",
        "target_duration": 60,
        "custom_hook": "Un proyecto láser personalizado que transformó mi espacio",
        "character_description": "Diseñador creativo, 30-40 años, mostrando un proyecto de corte láser personalizado",
    }

    print(f"🎬 Pipeline Configuration:")
    print(f"   - Angle: {inputs['angle_type']}")
    print(f"   - Platform: {inputs['platform']}")
    print(f"   - Duration: {inputs['target_duration']}s")
    print(f"   - Character: {inputs.get('character_description', 'Default')}")
    print()

    try:
        # Build and execute pipeline (no DB needed for test)
        pipeline = UGCPipeline(event_bus, run_id, db_session=None)
        result = await pipeline.execute(inputs)

        print()
        print("=" * 80)
        print("📊 PIPELINE RESULTS")
        print("=" * 80)

        if result.get("status") == "completed":
            print("✅ PIPELINE COMPLETED SUCCESSFULLY")
            print()

            # Check outputs
            outputs = result.get("outputs", {})

            # 1. Script validation
            script = outputs.get("script", {})
            if script:
                print("📝 Script Generated:")
                print(f"   - Title: {script.get('title', 'N/A')}")
                print(f"   - Scenes: {len(script.get('scenes', []))}")
                print(f"   - Total duration: {script.get('total_duration_seconds', 0)}s")
                print(f"   - Hook: {script.get('hook', '')[:60]}...")
                print()

            # 2. Image validation
            image_paths = outputs.get("image_paths", [])
            if image_paths:
                print(f"🖼️  Images Generated: {len(image_paths)}")
                for i, img_path in enumerate(image_paths):
                    if os.path.exists(img_path):
                        size_mb = os.path.getsize(img_path) / (1024 * 1024)
                        print(f"   - Scene {i+1}: {Path(img_path).name} ({size_mb:.1f}MB) ✅")
                    else:
                        print(f"   - Scene {i+1}: {img_path} ❌ NOT FOUND")
                print()

            # 3. Audio validation
            audio_paths = outputs.get("audio_paths", [])
            full_voiceover = outputs.get("full_voiceover_path", "")
            if audio_paths:
                print(f"🔊 Audio Generated: {len(audio_paths)} scene audios")
                for i, audio_path in enumerate(audio_paths):
                    if audio_path and os.path.exists(audio_path):
                        size_mb = os.path.getsize(audio_path) / (1024 * 1024)
                        print(f"   - Scene {i+1}: {size_mb:.1f}MB ✅")
                    elif audio_path:
                        print(f"   - Scene {i+1}: ❌ NOT FOUND")
                    else:
                        print(f"   - Scene {i+1}: ⏭️  SKIPPED (no text)")

                if full_voiceover and os.path.exists(full_voiceover):
                    size_mb = os.path.getsize(full_voiceover) / (1024 * 1024)
                    print(f"   - Full voiceover: {size_mb:.1f}MB ✅")
                print()

            # 4. Video validation
            final_video = outputs.get("final_video_path", "")
            if final_video and os.path.exists(final_video):
                size_mb = os.path.getsize(final_video) / (1024 * 1024)
                print(f"🎥 Final Video: {Path(final_video).name}")
                print(f"   - Size: {size_mb:.1f}MB ✅")
                print(f"   - Path: {final_video}")
                print()
            elif final_video:
                print(f"❌ Final video not found: {final_video}")

            # 5. Subtitle validation
            srt_path = outputs.get("srt_path", "")
            if srt_path and os.path.exists(srt_path):
                with open(srt_path) as f:
                    srt_content = f.read()
                    lines = srt_content.strip().split('\n')
                    subtitle_count = len([l for l in lines if l.isdigit()])
                print(f"📝 Subtitles: {subtitle_count} entries ✅")
                print()

        else:
            print(f"❌ PIPELINE FAILED")
            print(f"Status: {result.get('status')}")
            print(f"Error: {result.get('error')}")

    except Exception as e:
        print(f"❌ ORCHESTRATION ERROR: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"Events emitted: {len(event_bus.events)}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
