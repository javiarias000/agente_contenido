from __future__ import annotations

import json
import os
import uuid
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel

from api.config import settings

router = APIRouter()


class ScriptGenerateRequest(BaseModel):
    brand_slug: str
    angle_type: Literal["sales", "competitor", "trending", "educational"] = "sales"
    platform: Literal["tiktok", "instagram_reel", "youtube_short"] = "tiktok"
    target_duration: int = 60
    custom_hook: str | None = None
    competitor_name: str | None = None
    interactive: bool = False


@router.post("/generate")
async def generate_script(
    body: ScriptGenerateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict:
    run_id = str(uuid.uuid4())
    event_bus = request.app.state.event_bus

    async def _run():
        from skills.script_generator import ScriptGenerator
        skill = ScriptGenerator(event_bus=event_bus, run_id=run_id, step_index=0)
        await skill.run(body.model_dump(), interactive=body.interactive)

    background_tasks.add_task(_run)
    return {"run_id": run_id, "sse_url": f"/api/pipelines/sse/{run_id}"}


@router.get("/{run_id}")
async def get_script(run_id: str) -> dict:
    scripts_dir = os.path.join(settings.outputs_dir, "scripts")
    path = os.path.join(scripts_dir, f"{run_id}_script.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Script not found")
    with open(path) as f:
        return json.load(f)
