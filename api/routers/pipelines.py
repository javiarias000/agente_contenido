from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from api.database import get_session
from api.models import PipelineRun

router = APIRouter()


class PipelineRunRequest(BaseModel):
    pipeline_type: Literal["ugc", "avatar_reel", "static_ads", "carousel"] = "ugc"
    brand_slug: str
    mode: Literal["interactive", "headless"] = "interactive"
    platform: Literal["tiktok", "instagram_reel", "youtube_short"] = "tiktok"
    angle_type: Literal["sales", "competitor", "trending", "educational"] = "sales"
    character_description: str | None = None
    voice_id: str | None = None
    target_duration: int = 60
    competitor_name: str | None = None
    custom_hook: str | None = None
    # UGC with user photo
    user_photo_path: str | None = None
    # Avatar reel
    news_url: str | None = None
    # Static ads
    num_ads: int = 10
    # Carousel
    topic: str | None = None
    num_slides: int = 6
    render_method: Literal["html", "image"] = "image"


class FeedbackRequest(BaseModel):
    approved: bool = True
    instructions: str = ""


@router.post("/run")
async def run_pipeline(
    body: PipelineRunRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> dict:
    run_id = str(uuid.uuid4())
    event_bus = request.app.state.event_bus
    interactive = body.mode == "interactive"

    db_run = PipelineRun(
        run_id=run_id,
        pipeline_type=body.pipeline_type,
        status="pending",
        mode=body.mode,
        input_config=body.model_dump(),
    )
    session.add(db_run)
    await session.commit()

    async def _run():
        from api.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            if body.pipeline_type == "ugc":
                from pipelines.ugc_pipeline import UGCPipeline
                pipeline = UGCPipeline(event_bus=event_bus, run_id=run_id, db_session=db)
            elif body.pipeline_type == "static_ads":
                from pipelines.static_ads_pipeline import StaticAdsPipeline
                pipeline = StaticAdsPipeline(event_bus=event_bus, run_id=run_id, db_session=db)
            elif body.pipeline_type == "avatar_reel":
                from pipelines.avatar_reel_pipeline import AvatarReelPipeline
                pipeline = AvatarReelPipeline(event_bus=event_bus, run_id=run_id, db_session=db)
            elif body.pipeline_type == "carousel":
                from pipelines.carousel_pipeline import CarouselPipeline
                pipeline = CarouselPipeline(event_bus=event_bus, run_id=run_id, db_session=db)
            else:
                return
            await pipeline.execute(body.model_dump(), interactive=interactive)

    background_tasks.add_task(_run)
    return {"run_id": run_id, "sse_url": f"/api/pipelines/sse/{run_id}"}


@router.get("/sse/{run_id}")
async def pipeline_sse(run_id: str, request: Request):
    event_bus = request.app.state.event_bus
    queue = event_bus.subscribe(run_id)

    async def generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield {"data": json.dumps(event.to_dict())}
                    if event.event_type in ("pipeline_complete", "pipeline_failed"):
                        break
                except asyncio.TimeoutError:
                    # Send heartbeat
                    yield {"data": json.dumps({"event_type": "heartbeat", "run_id": run_id})}
        finally:
            event_bus.unsubscribe(run_id, queue)

    return EventSourceResponse(generator())


@router.post("/{run_id}/feedback")
async def submit_feedback(run_id: str, body: FeedbackRequest, request: Request) -> dict:
    event_bus = request.app.state.event_bus
    feedback_text = "approved" if body.approved else body.instructions
    submitted = await event_bus.submit_feedback(run_id, feedback_text)
    if not submitted:
        raise HTTPException(status_code=404, detail="No pipeline waiting for feedback on this run_id")
    return {"status": "feedback_received", "run_id": run_id}


@router.get("")
async def list_runs(session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.exec(
        select(PipelineRun).order_by(PipelineRun.created_at.desc()).limit(50)
    )
    runs = result.all()
    return [
        {
            "run_id": r.run_id,
            "pipeline_type": r.pipeline_type,
            "status": r.status,
            "mode": r.mode,
            "current_step": r.current_step,
            "steps_completed": r.steps_completed,
            "steps_total": r.steps_total,
            "created_at": r.created_at.isoformat(),
        }
        for r in runs
    ]


@router.get("/{run_id}")
async def get_run(run_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    result = await session.exec(select(PipelineRun).where(PipelineRun.run_id == run_id))
    run = result.first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run.model_dump()
