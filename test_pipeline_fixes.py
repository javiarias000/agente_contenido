"""Test the fixed pipeline with existing data from test_ugc_with_voice_001."""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, "/home/ubuntu/agente_contenido")

from api.config import settings
from api.events import EventBus, PipelineEvent
from skills.advanced_subtitle_generator import AdvancedSubtitleGenerator
from skills.composed_video_assembler import ComposedVideoAssembler


async def test_subtitles():
    """Test AdvancedSubtitleGenerator with existing full voiceover."""
    print("\n" + "="*80)
    print("TEST 1: AdvancedSubtitleGenerator")
    print("="*80)

    # Setup
    run_id = "test_fixes_subtitles"
    event_bus = EventBus()
    audio_path = "/home/ubuntu/agente_contenido/outputs/audio/test_ugc_with_voice_001_full_voiceover.mp3"

    if not os.path.exists(audio_path):
        print(f"❌ Audio file not found: {audio_path}")
        return False

    print(f"✓ Found audio: {os.path.getsize(audio_path)} bytes")

    # Run subtitle generator
    generator = AdvancedSubtitleGenerator(event_bus, run_id)

    # Subscribe to events
    q = event_bus.subscribe(run_id)

    # Capture events in background
    async def read_events():
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=0.5)
                print(f"  [{event.event_type}] {event.message}")
            except asyncio.TimeoutError:
                break
            except Exception:
                break

    result = await generator.run({
        "full_voiceover_path": audio_path,
        "script": {"scenes": []}
    })

    # Read remaining events
    await read_events()
    event_bus.unsubscribe(run_id, q)

    print(f"\nResult status: {result.status}")
    print(f"Result outputs: {result.outputs}")

    # Validate output
    srt_path = result.outputs.get("srt_path", "")
    srt_valid = result.outputs.get("srt_valid", False)

    if srt_valid and os.path.exists(srt_path):
        srt_size = os.path.getsize(srt_path)
        print(f"✓ SRT file created: {srt_path} ({srt_size} bytes)")

        # Show first few lines of SRT
        with open(srt_path, "r") as f:
            lines = f.readlines()[:15]
            print("\nSRT content sample:")
            for line in lines:
                print(f"  {line.rstrip()}")

        return True
    else:
        print(f"❌ SRT validation failed or file not created")
        return False


async def test_video_assembly():
    """Test ComposedVideoAssembler with existing images and audio."""
    print("\n" + "="*80)
    print("TEST 2: ComposedVideoAssembler")
    print("="*80)

    run_id = "test_fixes_video"
    event_bus = EventBus()

    # Gather existing images and audio
    images_dir = "/home/ubuntu/agente_contenido/outputs/images"
    audio_dir = "/home/ubuntu/agente_contenido/outputs/audio"

    # Find images matching test_ugc_with_voice_001
    image_files = sorted([
        os.path.join(images_dir, f)
        for f in os.listdir(images_dir)
        if f.startswith("test_ugc_with_voice_001_scene_") and f.endswith(".png")
    ])

    # Find audio files matching test_ugc_with_voice_001
    audio_files = sorted([
        os.path.join(audio_dir, f)
        for f in os.listdir(audio_dir)
        if f.startswith("test_ugc_with_voice_001_scene_") and f.endswith(".mp3")
    ])

    if not image_files or not audio_files:
        print(f"❌ Missing image or audio files")
        print(f"   Images found: {len(image_files)}")
        print(f"   Audio files found: {len(audio_files)}")
        return False

    print(f"✓ Found {len(image_files)} images")
    print(f"✓ Found {len(audio_files)} audio files")

    # Create motion metadata
    motion_metadata = [
        {"motion_type": "zoom_in", "duration_seconds": 3},
        {"motion_type": "pan_left", "duration_seconds": 3},
        {"motion_type": "static", "duration_seconds": 3},
        {"motion_type": "pan_right", "duration_seconds": 3},
        {"motion_type": "zoom_out", "duration_seconds": 3},
    ]

    # Create dummy SRT file with valid subtitles
    srt_dir = os.path.join(settings.outputs_dir, "video")
    os.makedirs(srt_dir, exist_ok=True)
    srt_path = os.path.join(srt_dir, f"{run_id}.srt")

    with open(srt_path, "w") as f:
        f.write("""1
00:00:00,000 --> 00:00:03,000
This is a test subtitle for scene one

2
00:00:03,000 --> 00:00:06,000
Another subtitle for scene two

3
00:00:06,000 --> 00:00:09,000
Third subtitle for scene three

4
00:00:09,000 --> 00:00:12,000
Fourth subtitle for scene four

5
00:00:12,000 --> 00:00:15,000
Fifth subtitle for scene five
""")

    print(f"✓ Created test SRT: {srt_path}")

    # Run assembler
    assembler = ComposedVideoAssembler(event_bus, run_id)

    # Subscribe to events
    q = event_bus.subscribe(run_id)

    # Capture events in background
    async def read_events():
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=0.5)
                print(f"  [{event.event_type}] {event.message}")
            except asyncio.TimeoutError:
                break
            except Exception:
                break

    result = await assembler.run({
        "image_paths": image_files[:len(audio_files)],  # Match audio count
        "audio_paths": audio_files,
        "motion_metadata": motion_metadata,
        "srt_path": srt_path,
        "script": {}
    })

    # Read remaining events
    await read_events()
    event_bus.unsubscribe(run_id, q)

    print(f"\nResult status: {result.status}")
    print(f"Result outputs: {result.outputs}")

    # Validate output
    final_video = result.outputs.get("final_video_path", "")

    if result.status == "completed" and final_video and os.path.exists(final_video):
        video_size = os.path.getsize(final_video)
        print(f"✓ Final video created: {final_video}")
        print(f"  Size: {video_size / (1024*1024):.2f} MB")

        if video_size > 100000:  # At least 100KB
            print("✓ Video file size looks reasonable")
            return True
        else:
            print("❌ Video file size too small")
            return False
    else:
        print(f"❌ Video assembly failed or output not found")
        return False


async def main():
    """Run all tests."""
    print("\n" + "#"*80)
    print("# PIPELINE FIX VERIFICATION TESTS")
    print("#"*80)

    try:
        # Test 1: Subtitles
        subtitle_ok = await test_subtitles()

        # Test 2: Video assembly with animation
        video_ok = await test_video_assembly()

        print("\n" + "="*80)
        print("TEST RESULTS")
        print("="*80)
        print(f"Subtitle generation: {'✓ PASS' if subtitle_ok else '❌ FAIL'}")
        print(f"Video assembly:      {'✓ PASS' if video_ok else '❌ FAIL'}")

        if subtitle_ok and video_ok:
            print("\n✓ All tests passed! Pipeline fixes are working.")
            return 0
        else:
            print("\n❌ Some tests failed. Review output above.")
            return 1

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
