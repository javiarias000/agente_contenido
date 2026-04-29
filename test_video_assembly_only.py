"""Test video assembly with optimized FFmpeg filters using existing data."""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, "/home/ubuntu/agente_contenido")

from api.config import settings
from api.events import EventBus
from skills.composed_video_assembler import ComposedVideoAssembler


async def test_video_assembly():
    """Test ComposedVideoAssembler with optimized filters and existing data."""
    print("\n" + "="*80)
    print("TESTING OPTIMIZED VIDEO ASSEMBLY")
    print("="*80)

    run_id = "test_video_optimized"
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
        return False

    # Limit to first 2 scenes for faster testing
    image_files = image_files[:2]
    audio_files = audio_files[:2]

    print(f"✓ Using {len(image_files)} scenes")
    print(f"  Images: {[Path(p).name for p in image_files]}")
    print(f"  Audio: {[Path(p).name for p in audio_files]}")

    # Create motion metadata with different types per scene
    motion_metadata = [
        {"motion_type": "zoom_in", "duration_seconds": 3},
        {"motion_type": "pan_left", "duration_seconds": 3},
    ]

    # Create dummy SRT file
    srt_dir = os.path.join(settings.outputs_dir, "video")
    os.makedirs(srt_dir, exist_ok=True)
    srt_path = os.path.join(srt_dir, f"{run_id}.srt")

    with open(srt_path, "w") as f:
        f.write("""1
00:00:00,000 --> 00:00:03,000
First scene subtitle

2
00:00:03,000 --> 00:00:06,000
Second scene subtitle
""")

    print(f"✓ Created test SRT: {Path(srt_path).name}")

    # Subscribe to events
    q = event_bus.subscribe(run_id)

    async def read_events():
        """Read events non-blocking."""
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=0.2)
                    print(f"  [{event.event_type:15}] {event.message}")
                except asyncio.TimeoutError:
                    break
        except Exception:
            pass

    # Run assembler
    print("\n" + "-"*80)
    print("Running ComposedVideoAssembler...")
    print("-"*80 + "\n")

    assembler = ComposedVideoAssembler(event_bus, run_id)

    result = await assembler.run({
        "image_paths": image_files,
        "audio_paths": audio_files,
        "motion_metadata": motion_metadata,
        "srt_path": srt_path,
        "script": {}
    })

    # Read remaining events
    await read_events()
    event_bus.unsubscribe(run_id, q)

    # Show result
    print("\n" + "="*80)
    print("RESULT")
    print("="*80)
    print(f"Status: {result.status}")

    final_video = result.outputs.get("final_video_path", "")
    if final_video:
        print(f"Video path: {final_video}")

    if result.status == "completed" and final_video and os.path.exists(final_video):
        video_size = os.path.getsize(final_video)
        size_mb = video_size / (1024*1024)
        print(f"✓ Video created: {size_mb:.2f} MB")

        if video_size > 100000:  # At least 100KB
            print("✓ Video file size is reasonable")
            print("\n✅ TEST PASSED - Video assembly working with optimized filters!")
            return True
        else:
            print("❌ Video file size too small")
            return False
    else:
        print(f"❌ Video assembly failed")
        if result.outputs.get("error"):
            print(f"Error: {result.outputs['error']}")
        return False


async def main():
    """Run test."""
    try:
        success = await test_video_assembly()
        return 0 if success else 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
