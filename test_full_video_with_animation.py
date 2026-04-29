"""Test full video assembly with multiple scenes and animations."""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, "/home/ubuntu/agente_contenido")

from api.config import settings
from api.events import EventBus
from skills.composed_video_assembler import ComposedVideoAssembler


async def test_with_animation():
    """Test with 3 scenes and different motion types."""
    print("\n" + "="*80)
    print("FULL VIDEO ASSEMBLY TEST (3 Scenes + Animation)")
    print("="*80 + "\n")

    run_id = "test_animation_003"
    event_bus = EventBus()

    # Find images and audio
    images_dir = "/home/ubuntu/agente_contenido/outputs/images"
    audio_dir = "/home/ubuntu/agente_contenido/outputs/audio"

    images = [
        os.path.join(images_dir, "test_ugc_with_voice_001_scene_0.png"),
        os.path.join(images_dir, "test_ugc_with_voice_001_scene_1.png"),
        os.path.join(images_dir, "test_ugc_with_voice_001_scene_2.png"),
    ]

    audio = [
        os.path.join(audio_dir, "test_ugc_with_voice_001_scene_0.mp3"),
        os.path.join(audio_dir, "test_ugc_with_voice_001_scene_1.mp3"),
        os.path.join(audio_dir, "test_ugc_with_voice_001_scene_2.mp3"),
    ]

    # Verify files exist
    missing = [p for p in images + audio if not os.path.exists(p)]
    if missing:
        print(f"❌ Missing files: {[Path(p).name for p in missing]}")
        return False

    print(f"✓ Using {len(images)} scenes")
    for i, (img, aud) in enumerate(zip(images, audio)):
        img_size = os.path.getsize(img) / (1024)
        aud_size = os.path.getsize(aud) / (1024)
        print(f"  Scene {i+1}: {img_size:.0f} KB + {aud_size:.0f} KB audio")

    # Create motion metadata with different animation types
    motion_metadata = [
        {"motion_type": "zoom_in", "duration_seconds": 3},
        {"motion_type": "pan_left", "duration_seconds": 3},
        {"motion_type": "pan_right", "duration_seconds": 3},
    ]

    # Run assembler
    assembler = ComposedVideoAssembler(event_bus, run_id)
    q = event_bus.subscribe(run_id)

    async def read_events():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=0.2)
                    if "error" in event.event_type.lower() or "fail" in event.message.lower():
                        print(f"  ⚠️  {event.message}")
                    elif "generado" in event.message.lower() or "generated" in event.message.lower():
                        print(f"  ✓ {event.message}")
                    else:
                        print(f"  → {event.message}")
                except asyncio.TimeoutError:
                    break
        except Exception:
            pass

    print("\nAssembling video with animations...")
    result = await assembler.run({
        "image_paths": images,
        "audio_paths": audio,
        "motion_metadata": motion_metadata,
        "srt_path": "",
        "script": {}
    })

    await read_events()
    event_bus.unsubscribe(run_id, q)

    # Check result
    print("\n" + "="*80)
    final_video = result.outputs.get("final_video_path", "")

    if result.status == "completed" and final_video and os.path.exists(final_video):
        size = os.path.getsize(final_video)
        size_mb = size / (1024*1024)
        print(f"✅ SUCCESS - Video created: {Path(final_video).name}")
        print(f"   Size: {size_mb:.2f} MB ({size:,} bytes)")
        print(f"   Path: {final_video}")

        # Verify it's a valid video file
        if size > 100000:  # At least 100KB
            print(f"   ✓ File size is reasonable for a video")

        return True
    else:
        print(f"❌ FAILED - Status: {result.status}")
        if result.outputs.get("error"):
            error_msg = result.outputs['error']
            if len(error_msg) > 200:
                error_msg = error_msg[:200] + "..."
            print(f"   Error: {error_msg}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_with_animation())
    sys.exit(0 if success else 1)
