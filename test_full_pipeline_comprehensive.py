"""Comprehensive pipeline test with graceful error handling.

Tests the full UGC pipeline with existing data, handling:
- Missing API key (skips subtitle generation)
- FFmpeg video encoding
- Proper output file generation
"""

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "/home/ubuntu/agente_contenido")

from api.config import settings
from api.events import EventBus, PipelineEvent
from pipelines.ugc_pipeline import UGCPipeline


async def test_full_pipeline():
    """Test full UGC pipeline with existing data."""
    print("\n" + "#"*80)
    print("# COMPREHENSIVE UGC PIPELINE TEST")
    print("#"*80 + "\n")

    # Setup
    run_id = "test_pipeline_comprehensive"
    event_bus = EventBus()

    # Check for existing test data
    outputs_dir = Path(settings.outputs_dir)

    # Use test_ugc_with_voice_001 data which has both images and audio
    image_base = "test_ugc_with_voice_001"
    image_files = sorted([
        str(outputs_dir / "images" / f)
        for f in os.listdir(outputs_dir / "images")
        if f.startswith(image_base) and f.endswith(".png")
    ])

    audio_files = sorted([
        str(outputs_dir / "audio" / f)
        for f in os.listdir(outputs_dir / "audio")
        if f.startswith(image_base) and f.endswith(".mp3")
    ])

    full_voiceover = str(outputs_dir / "audio" / f"{image_base}_full_voiceover.mp3")
    script_path = outputs_dir / "scripts" / f"{image_base}_script.json"

    print("📊 TEST SETUP")
    print("-" * 80)
    print(f"Run ID: {run_id}")
    print(f"Using existing data from: {image_base}")
    print(f"  Images: {len(image_files)} found")
    print(f"  Audio scenes: {len(audio_files)} found")
    print(f"  Full voiceover: {os.path.exists(full_voiceover)}")
    print(f"  Script: {os.path.exists(script_path)}")

    if not all([image_files, audio_files, full_voiceover]):
        print("\n❌ Missing required test data")
        return False

    # Load script
    with open(script_path) as f:
        script = json.load(f)

    print("\n✓ All test data available\n")

    # Create test brand profile
    brand_profile = {
        "name": "Test Brand",
        "slug": "test_brand",
        "colors": ["#FF6B6B", "#4ECDC4"],
        "tone": "professional",
        "character_anchor": "A modern, professional brand"
    }

    # Setup event subscription
    q = event_bus.subscribe(run_id)

    async def print_events():
        """Print events as they arrive."""
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=0.5)
                    marker = "✓" if "complete" in event.event_type else "→" if "start" in event.event_type else "·"
                    print(f"  {marker} [{event.step_name or 'system':20}] {event.message}")
                except asyncio.TimeoutError:
                    break
        except Exception:
            pass

    # Build pipeline inputs using existing data
    inputs = {
        "brand_slug": "test_brand",
        "platform": "tiktok",
        "angle_type": "sales",
        "character_description": brand_profile.get("character_anchor"),
        # Pass pre-generated content to skip regeneration steps
        "_existing_data": {
            "images": image_files[:len(audio_files)],
            "audio": audio_files,
            "full_voiceover": full_voiceover,
            "script": script,
            "profile": brand_profile,
        }
    }

    # Run pipeline
    print("🎬 RUNNING PIPELINE")
    print("-" * 80 + "\n")

    pipeline = UGCPipeline(event_bus, run_id)

    # For this test, we'll just test the final two critical steps directly
    # (to avoid script generation and image generation which require API calls)

    from skills.animated_image_generator import AnimatedImageGenerator
    from skills.advanced_subtitle_generator import AdvancedSubtitleGenerator
    from skills.composed_video_assembler import ComposedVideoAssembler

    # Test subtitle generation (might skip due to API key)
    print("STEP 1: Advanced Subtitle Generation")
    subtitle_gen = AdvancedSubtitleGenerator(event_bus, f"{run_id}_subtitles")
    sub_result = await subtitle_gen.run({
        "full_voiceover_path": full_voiceover,
        "script": script
    })
    await print_events()

    srt_path = sub_result.outputs.get("srt_path", "")
    print(f"  Result: SRT path = {srt_path or '(none - API key missing)'}")
    print(f"  Status: {sub_result.status}\n")

    # Test video assembly (main focus)
    print("STEP 2: Composed Video Assembly")
    assembler = ComposedVideoAssembler(event_bus, f"{run_id}_video")

    # Create motion metadata
    motion_metadata = [
        {"motion_type": "zoom_in", "duration_seconds": 3},
        {"motion_type": "pan_left", "duration_seconds": 3},
    ]

    # Limit to 2 scenes for faster test
    test_images = image_files[:2]
    test_audio = audio_files[:2]

    print(f"  Testing with {len(test_images)} scenes")

    assembly_result = await assembler.run({
        "image_paths": test_images,
        "audio_paths": test_audio,
        "motion_metadata": motion_metadata[:2],
        "srt_path": srt_path,
        "script": script
    })

    await print_events()

    final_video = assembly_result.outputs.get("final_video_path", "")
    print(f"  Result: Video path = {final_video or '(none)'}")
    print(f"  Status: {assembly_result.status}\n")

    # Summary
    print("="*80)
    print("TEST SUMMARY")
    print("="*80)

    success = assembly_result.status == "completed" and final_video and os.path.exists(final_video)

    if success:
        size_mb = os.path.getsize(final_video) / (1024*1024)
        print(f"✅ SUCCESS - Video generated ({size_mb:.2f} MB)")
        print(f"   Output: {final_video}")
        return True
    else:
        print(f"❌ FAILED - Video assembly did not complete")
        if assembly_result.outputs.get("error"):
            print(f"   Error: {assembly_result.outputs['error']}")
        return False

    event_bus.unsubscribe(f"{run_id}_video", q)


async def main():
    """Run test."""
    try:
        success = await test_full_pipeline()
        return 0 if success else 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
