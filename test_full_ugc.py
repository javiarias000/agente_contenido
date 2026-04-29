#!/usr/bin/env python3
"""Test full UGC pipeline end-to-end."""

import asyncio
import json
from pathlib import Path
from api.models import PipelineRun
from pipelines.ugc_pipeline import UGCPipeline
from api.config import settings
from api.database import get_db

async def test_full_ugc_pipeline():
    """Run full UGC pipeline with Mi Idea brand."""
    
    print(f"\n{'='*60}")
    print(f"Testing Full UGC Pipeline for Mi Idea")
    print(f"{'='*60}\n")
    
    # Create pipeline run
    pipeline_run = PipelineRun(
        run_id="test_ugc_full_001",
        pipeline_type="ugc",
        brand_slug="mi-idea",
        status="running",
        input_config={
            "angle_type": "sales",
            "platform": "tiktok",
            "duration_seconds": 30,
        }
    )
    
    # Get database session
    async for db in get_db():
        # Save run to DB
        db.add(pipeline_run)
        await db.commit()
        
        # Create and execute pipeline
        pipeline = UGCPipeline(
            run_id=pipeline_run.run_id,
            db=db,
            event_bus=None  # Will be created by pipeline
        )
        
        result = await pipeline.execute(
            input_config=pipeline_run.input_config,
            interactive=False
        )
        
        print(f"\n✅ Pipeline Result:")
        print(f"  Status: {result.get('status')}")
        if result.get('error'):
            print(f"  Error: {result.get('error')}")
        
        # List outputs
        outputs_dir = Path(settings.outputs_dir)
        for output_type in ['scripts', 'images', 'audio', 'video']:
            pattern = f"test_ugc_full_001*"
            files = list((outputs_dir / output_type).glob(pattern)) if (outputs_dir / output_type).exists() else []
            if files:
                print(f"\n  {output_type.upper()}:")
                for f in sorted(files)[:5]:
                    print(f"    - {f.name}")
        
        break

if __name__ == "__main__":
    asyncio.run(test_full_ugc_pipeline())
