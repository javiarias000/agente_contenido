#!/usr/bin/env python3
"""Test the refactored UGC pipeline with new components."""

import asyncio
import json
from pathlib import Path

async def test_pipeline():
    from pipelines.ugc_pipeline import UGCPipeline
    from api.events import EventBus
    from api.config import settings
    
    print("\n" + "="*60)
    print("Testing Refactored UGC Pipeline")
    print("="*60 + "\n")
    
    # Create event bus
    event_bus = EventBus()
    
    # Create pipeline
    pipeline = UGCPipeline(
        event_bus=event_bus,
        run_id="test_refactored_001",
        db_session=None
    )
    
    # Test inputs
    inputs = {
        "brand_slug": "mi-idea",
        "platform": "tiktok",
        "angle_type": "sales",
    }
    
    print(f"🚀 Testing pipeline with inputs:")
    print(f"   Brand: {inputs['brand_slug']}")
    print(f"   Platform: {inputs['platform']}")
    print(f"   Angle: {inputs['angle_type']}\n")
    
    try:
        result = await pipeline.execute(inputs, interactive=False)
        
        print(f"\n✅ Pipeline completed!")
        print(f"   Script: {result.get('script', {}).get('run_id')}")
        print(f"   Images: {len(result.get('image_paths', []))} images")
        print(f"   Video: {result.get('final_video_path', 'N/A')}")
        print(f"   Subtitles: {result.get('srt_path', 'N/A')}")
        
        # Check if files exist
        video_path = result.get('final_video_path')
        if video_path and Path(video_path).exists():
            size_mb = Path(video_path).stat().st_size / (1024*1024)
            print(f"\n📊 Video generated: {size_mb:.1f} MB")
        
    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_pipeline())
