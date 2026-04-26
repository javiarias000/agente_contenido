from __future__ import annotations

import os
from typing import Any

import httpx
import asyncio

from api.config import settings
from api.events import EventBus
from skills import BaseSkill, SkillResult


class LipSyncSkill(BaseSkill):
    """Lip-sync video using Sync.so or FAL.ai."""
    skill_name = "lip_sync"

    def __init__(self, event_bus: EventBus, run_id: str, step_index: int = 0):
        super().__init__(event_bus, run_id, step_index)

    async def run(self, inputs: dict[str, Any], interactive: bool = False) -> SkillResult:
        image_paths: list[str] = inputs.get("image_paths", [])
        full_voiceover_path: str = inputs.get("full_voiceover_path", "")
        await self.emit("step_start", "Iniciando lip-sync...")

        if not image_paths or not full_voiceover_path:
            await self.emit("log", "Lip-sync omitido: faltan imagen o audio")
            return SkillResult(status="completed", outputs=inputs)

        if settings.sync_so_api_key:
            result_path = await self._sync_so(image_paths[0], full_voiceover_path)
        elif settings.fal_api_key:
            result_path = await self._fal_ai(image_paths[0], full_voiceover_path)
        else:
            await self.emit("log", "Lip-sync omitido: no hay API key configurada (SYNC_SO_API_KEY o FAL_API_KEY)")
            return SkillResult(status="completed", outputs=inputs)

        await self.emit("step_complete", "Lip-sync completado", data={"lipsync_video": result_path})
        return SkillResult(status="completed", outputs={**inputs, "lipsync_video_path": result_path})

    async def _sync_so(self, image_path: str, audio_path: str) -> str:
        """Submit to Sync.so and poll for result."""
        with open(image_path, "rb") as img_f:
            img_data = img_f.read()
        with open(audio_path, "rb") as aud_f:
            aud_data = aud_f.read()

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.sync.so/v2/generate",
                headers={"x-api-key": settings.sync_so_api_key},
                files={"video": ("image.png", img_data, "image/png"), "audio": ("audio.mp3", aud_data, "audio/mpeg")},
            )
            resp.raise_for_status()
            job_id = resp.json()["id"]

        for _ in range(60):
            await asyncio.sleep(10)
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.get(
                    f"https://api.sync.so/v2/generate/{job_id}",
                    headers={"x-api-key": settings.sync_so_api_key},
                )
                data = r.json()
            if data.get("status") == "completed":
                video_url = data["outputUrl"]
                out_path = os.path.join(settings.outputs_dir, "video", f"{self.run_id}_lipsync.mp4")
                async with httpx.AsyncClient(timeout=60.0) as client:
                    video_resp = await client.get(video_url)
                with open(out_path, "wb") as f:
                    f.write(video_resp.content)
                return out_path
        raise TimeoutError("Sync.so job timed out")

    async def _fal_ai(self, image_path: str, audio_path: str) -> str:
        """Submit to FAL.ai lipsync endpoint."""
        import base64
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        with open(audio_path, "rb") as f:
            aud_b64 = base64.b64encode(f.read()).decode()

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://queue.fal.run/fal-ai/lipsync",
                headers={"Authorization": f"Key {settings.fal_api_key}"},
                json={
                    "image_url": f"data:image/png;base64,{img_b64}",
                    "audio_url": f"data:audio/mpeg;base64,{aud_b64}",
                },
            )
            resp.raise_for_status()
            result = resp.json()

        video_url = result.get("video", {}).get("url") or result.get("url")
        if not video_url:
            raise ValueError("FAL.ai did not return a video URL")

        out_path = os.path.join(settings.outputs_dir, "video", f"{self.run_id}_lipsync.mp4")
        async with httpx.AsyncClient(timeout=60.0) as client:
            video_resp = await client.get(video_url)
        with open(out_path, "wb") as f:
            f.write(video_resp.content)
        return out_path
