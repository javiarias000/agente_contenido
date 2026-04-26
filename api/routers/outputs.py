from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from api.config import settings
from api.database import get_session
from api.models import OutputAsset

router = APIRouter()


@router.get("")
async def list_outputs(
    asset_type: str | None = None,
    brand_id: int | None = None,
    run_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    query = select(OutputAsset).where(OutputAsset.deleted == False)
    if asset_type:
        query = query.where(OutputAsset.asset_type == asset_type)
    if brand_id:
        query = query.where(OutputAsset.brand_id == brand_id)
    if run_id:
        query = query.where(OutputAsset.run_id == run_id)
    query = query.order_by(OutputAsset.created_at.desc()).offset(offset).limit(limit)
    result = await session.exec(query)
    assets = result.all()
    return [
        {
            "id": a.id,
            "run_id": a.run_id,
            "asset_type": a.asset_type,
            "file_path": a.file_path,
            "file_size": a.file_size,
            "mime_type": a.mime_type,
            "brand_id": a.brand_id,
            "created_at": a.created_at.isoformat(),
        }
        for a in assets
    ]


@router.get("/{asset_id}/file")
async def download_asset(
    asset_id: int,
    session: AsyncSession = Depends(get_session),
) -> FileResponse:
    result = await session.exec(select(OutputAsset).where(OutputAsset.id == asset_id))
    asset = result.first()
    if not asset or asset.deleted:
        raise HTTPException(status_code=404, detail="Asset not found")
    full_path = os.path.join(settings.outputs_dir, asset.file_path) if not os.path.isabs(asset.file_path) else asset.file_path
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    return FileResponse(full_path, media_type=asset.mime_type or "application/octet-stream")


@router.delete("/{asset_id}")
async def delete_asset(
    asset_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.exec(select(OutputAsset).where(OutputAsset.id == asset_id))
    asset = result.first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    asset.deleted = True
    session.add(asset)
    await session.commit()
    return {"status": "deleted", "id": asset_id}


@router.get("/runs/{run_id}")
async def get_run_outputs(run_id: str, session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.exec(
        select(OutputAsset)
        .where(OutputAsset.run_id == run_id, OutputAsset.deleted == False)
        .order_by(OutputAsset.created_at)
    )
    assets = result.all()
    return [
        {
            "id": a.id,
            "asset_type": a.asset_type,
            "file_path": a.file_path,
            "mime_type": a.mime_type,
            "created_at": a.created_at.isoformat(),
        }
        for a in assets
    ]
