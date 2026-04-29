"""Quick pipeline test with minimal processing."""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, "/home/ubuntu/agente_contenido")

from api.config import settings
from api.events import EventBus
from skills.composed_video_assembler import ComposedVideoAssembler


async def test_quick():
    """Quick test with 1 scene."""
    print("\n" + "="*80)
    print("QUICK VIDEO ASSEMBLY TEST (1 Scene)")
    print("="*80 + "\n")

    run_id = "test_quick_001"
    event_bus = EventBus()

    # Find first image and audio pair
    images_dir = "/home/ubuntu/agente_contenido/outputs/images"
    audio_dir = "/home/ubuntu/agente_contenido/outputs/audio"

    image = os.path.join(images_dir, "test_ugc_with_voice_001_scene_0.png")
    audio = os.path.join(audio_dir, "test_ugc_with_voice_001_scene_0.mp3")

    if not os.path.exists(image) or not os.path.exists(audio):
        print(f"❌ Missing test files")
        return False

    print(f"Image: {Path(image).name} ({os.path.getsize(image)} bytes)")
    print(f"Audio: {Path(audio).name} ({os.path.getsize(audio)} bytes)")

    # Run assembler
    assembler = ComposedVideoAssembler(event_bus, run_id)
    q = event_bus.subscribe(run_id)

    async def read_events():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=0.2)
                    print(f"  {event.message}")
                except asyncio.TimeoutError:
                    break
        except Exception:
            pass

    print("\nAssembling video...")
    result = await assembler.run({
        "image_paths": [image],
        "audio_paths": [audio],
        "motion_metadata": [{"motion_type": "static"}],
        "srt_path": "",
        "script": {}
    })

    await read_events()
    event_bus.unsubscribe(run_id, q)

    # Check result
    print("\n" + "="*80)
    final_video = result.outputs.get("final_video_path", "")

    print(f"Result outputs: {result.outputs}")
    print(f"Final video: {final_video}")
    print(f"Exists: {os.path.exists(final_video) if final_video else 'N/A'}")

    if result.status == "completed" and final_video and os.path.exists(final_video):
        size = os.path.getsize(final_video)
        size_mb = size / (1024*1024)
        print(f"✅ SUCCESS - Video: {Path(final_video).name} ({size_mb:.2f} MB)")
        return True
    else:
        print(f"❌ FAILED - Status: {result.status}")
        if result.outputs.get("error"):
            print(f"Error: {result.outputs['error']}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_quick())
    sys.exit(0 if success else 1)
