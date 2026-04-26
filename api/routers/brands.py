from __future__ import annotations

import json
import os
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from api.config import settings
from api.database import get_session
from api.models import Brand

router = APIRouter()


class AnalyzeRequest(BaseModel):
    url: str
    name: str = ""
    interactive: bool = False


class BrandUpdateRequest(BaseModel):
    tone_of_voice: str | None = None
    target_audience: str | None = None
    brand_values: list[str] | None = None
    style_notes: str | None = None
    character_anchor: str | None = None
    preferred_voice_id: str | None = None


@router.get("")
async def list_brands(session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.exec(select(Brand).order_by(Brand.created_at.desc()))
    brands = result.all()
    return [
        {
            "id": b.id,
            "name": b.name,
            "slug": b.slug,
            "url": b.url,
            "tone_of_voice": b.tone_of_voice,
            "target_audience": b.target_audience,
            "created_at": b.created_at.isoformat(),
        }
        for b in brands
    ]


@router.post("/analyze")
async def analyze_brand(
    body: AnalyzeRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> dict:
    run_id = str(uuid.uuid4())
    event_bus = request.app.state.event_bus

    async def _run():
        from skills.brand_analyzer import BrandAnalyzer
        from api.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            skill = BrandAnalyzer(event_bus=event_bus, run_id=run_id, db_session=db, step_index=0)
            await skill.run({"url": body.url, "name": body.name}, interactive=body.interactive)

    background_tasks.add_task(_run)
    return {"run_id": run_id, "sse_url": f"/api/pipelines/sse/{run_id}"}


@router.get("/{slug}")
async def get_brand(slug: str, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    result = await session.exec(select(Brand).where(Brand.slug == slug))
    brand = result.first()
    if brand is None:
        # Try reading from JSON file
        path = os.path.join(settings.brands_dir, f"{slug}.json")
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        raise HTTPException(status_code=404, detail="Brand not found")
    return brand.model_dump()


@router.put("/{slug}")
async def update_brand(
    slug: str,
    body: BrandUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.exec(select(Brand).where(Brand.slug == slug))
    brand = result.first()
    if brand is None:
        raise HTTPException(status_code=404, detail="Brand not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(brand, field, value)
    session.add(brand)
    await session.commit()
    # Sync JSON file
    path = os.path.join(settings.brands_dir, f"{slug}.json")
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
        data.update(body.model_dump(exclude_none=True))
        with open(path, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    return {"status": "updated", "slug": slug}


@router.delete("/{slug}")
async def delete_brand(slug: str, session: AsyncSession = Depends(get_session)) -> dict:
    result = await session.exec(select(Brand).where(Brand.slug == slug))
    brand = result.first()
    if brand:
        await session.delete(brand)
        await session.commit()
    return {"status": "deleted", "slug": slug}
