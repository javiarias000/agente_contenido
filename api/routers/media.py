from __future__ import annotations

import json
import os
import uuid
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel

from api.config import settings

router = APIRouter()


class MediaGenerateRequest(BaseModel):
    run_id: str | None = None
    script_path: str
    brand_slug: str
    platform: Literal["tiktok", "instagram_reel", "youtube_short"] = "tiktok"
    voice_id: str | None = None
    generate_images: bool = True
    generate_audio: bool = True
    interactive: bool = False


@router.post("/generate")
async def generate_media(
    body: MediaGenerateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict:
    if not os.path.exists(body.script_path):
        raise HTTPException(status_code=404, detail="Script file not found")

    with open(body.script_path) as f:
        script = json.load(f)

    run_id = body.run_id or str(uuid.uuid4())
    event_bus = request.app.state.event_bus

    brand_path = os.path.join(settings.brands_dir, f"{body.brand_slug}.json")
    profile = {}
    if os.path.exists(brand_path):
        with open(brand_path) as f:
            profile = json.load(f)

    async def _run():
        results = {}
        if body.generate_images:
            from skills.image_generator import ImageGenerator
            skill = ImageGenerator(event_bus=event_bus, run_id=run_id, step_index=0)
            res = await skill.run(
                {"script": script, "brand_slug": body.brand_slug, "platform": body.platform, "profile": profile},
                interactive=body.interactive,
            )
            results["image_paths"] = res.outputs.get("image_paths", [])
        if body.generate_audio:
            from skills.voice_generator import VoiceGenerator
            skill = VoiceGenerator(event_bus=event_bus, run_id=run_id, step_index=1)
            res = await skill.run(
                {"script": script, "voice_id": body.voice_id, "profile": profile},
                interactive=body.interactive,
            )
            results["audio_paths"] = res.outputs.get("audio_paths", [])
            results["full_voiceover_path"] = res.outputs.get("full_voiceover_path")

    background_tasks.add_task(_run)
    return {"run_id": run_id, "sse_url": f"/api/pipelines/sse/{run_id}"}


@router.get("/voices")
async def list_voices() -> list[dict]:
    from skills.voice_generator import VoiceGenerator
    from api.events import EventBus
    skill = VoiceGenerator(EventBus(), "temp", 0)
    return await skill.list_voices()
