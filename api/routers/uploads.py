"""Upload endpoints — user photos and studio media files."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

from api.config import settings

router = APIRouter(prefix="/uploads", tags=["uploads"])

ALLOWED_MIMES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
ALLOWED_VIDEO_MIMES = {"video/mp4", "video/quicktime", "video/mov", "video/avi", "video/webm", "video/x-msvideo"}
ALLOWED_MEDIA_MIMES = ALLOWED_MIMES | ALLOWED_VIDEO_MIMES
MAX_SIZE_MB = 10
MAX_MEDIA_SIZE_MB = 100


@router.post("/photo")
async def upload_photo(file: UploadFile = File(...)) -> dict:
    """Upload a product photo for UGC generation.

    Returns:
        {
            "photo_path": "/path/to/file",
            "photo_url": "/outputs/uploads/...",
            "filename": "...",
            "size_bytes": 123456
        }
    """
    # Validate MIME type
    if file.content_type not in ALLOWED_MIMES:
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid file type: {file.content_type}. Allowed: {ALLOWED_MIMES}"}
        )

    # Read and validate size
    contents = await file.read()
    size_bytes = len(contents)
    size_mb = size_bytes / (1024 * 1024)

    if size_mb > MAX_SIZE_MB:
        return JSONResponse(
            status_code=400,
            content={"error": f"File too large: {size_mb:.1f}MB (max {MAX_SIZE_MB}MB)"}
        )

    # Generate filename
    ext = Path(file.filename or "photo.jpg").suffix
    filename = f"{uuid.uuid4().hex}{ext}"

    # Create uploads directory
    uploads_dir = os.path.join(settings.outputs_dir, "uploads")
    os.makedirs(uploads_dir, exist_ok=True)

    # Save file
    photo_path = os.path.join(uploads_dir, filename)
    with open(photo_path, "wb") as f:
        f.write(contents)

    # Return paths
    photo_url = f"/outputs/uploads/{filename}"

    return {
        "photo_path": photo_path,
        "photo_url": photo_url,
        "filename": filename,
        "size_bytes": size_bytes,
    }


@router.post("/media")
async def upload_media(file: UploadFile = File(...)) -> dict:
    """Upload an image or video for Video Studio.

    Accepts JPEG, PNG, WEBP, GIF, MP4, MOV, AVI, WEBM (max 100 MB).

    Returns:
        {
            "path": "/abs/path/to/file",
            "url": "/outputs/uploads/...",
            "filename": "...",
            "media_type": "image" | "video",
            "mime_type": "...",
            "size_bytes": 123456
        }
    """
    mime = file.content_type or ""

    if mime not in ALLOWED_MEDIA_MIMES:
        return JSONResponse(
            status_code=400,
            content={"error": f"Tipo de archivo no soportado: {mime}. Permitidos: imágenes (jpeg, png, webp, gif) y videos (mp4, mov, webm, avi)."},
        )

    contents = await file.read()
    size_bytes = len(contents)
    size_mb = size_bytes / (1024 * 1024)

    limit = MAX_MEDIA_SIZE_MB
    if size_mb > limit:
        return JSONResponse(
            status_code=400,
            content={"error": f"Archivo demasiado grande: {size_mb:.1f} MB (máximo {limit} MB)."},
        )

    ext = Path(file.filename or "media").suffix or (".mp4" if mime in ALLOWED_VIDEO_MIMES else ".jpg")
    filename = f"{uuid.uuid4().hex}{ext}"

    uploads_dir = os.path.join(settings.outputs_dir, "uploads")
    os.makedirs(uploads_dir, exist_ok=True)

    file_path = os.path.join(uploads_dir, filename)
    with open(file_path, "wb") as f:
        f.write(contents)

    media_type = "video" if mime in ALLOWED_VIDEO_MIMES else "image"

    return {
        "path": file_path,
        "url": f"/outputs/uploads/{filename}",
        "filename": filename,
        "media_type": media_type,
        "mime_type": mime,
        "size_bytes": size_bytes,
    }
