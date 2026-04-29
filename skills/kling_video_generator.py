"""Skill to generate video from image using fal.ai Kling API."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import httpx

from api.config import settings
from api.events import EventBus
from skills import BaseSkill, SkillResult

# Kling video generation API endpoint
KLING_API_URL = "https://queue.fal.run/fal-ai/kling-video/v1.6/standard/image-to-video"
KLING_STATUS_URL = "https://queue.fal.run/requests"
MAX_WAIT_SECONDS = 300  # 5 minutes timeout


class KlingVideoGenerator(BaseSkill):
    """Generate video from image using fal.ai Kling."""

    skill_name = "kling_video_generator"

    def __init__(
        self,
        event_bus: EventBus,
        run_id: str,
        step_index: int = 0,
    ):
        super().__init__(event_bus, run_id, step_index)

    async def run(self, inputs: dict[str, Any], interactive: bool = False) -> SkillResult:
        """Generate video from image.

        Expected inputs:
            - image_path: Path to input image
            - script: Script dict with scenes (to determine number of clips)
            - duration_seconds: Duration per clip (default 6)
        """
        image_path = inputs.get("image_path", "")
        script = inputs.get("script", {})
        duration_seconds = inputs.get("duration_seconds", 6)

        if not image_path or not os.path.exists(image_path):
            return SkillResult(
                status="failed",
                outputs={"error": f"Image not found: {image_path}"}
            )

        if not settings.fal_api_key:
            await self.emit("progress", "⚠️  fal_api_key not configured, skipping Kling generation")
            return SkillResult(
                status="failed",
                outputs={"error": "fal_api_key not configured"}
            )

        await self.emit("step_start", "Generando video con Kling...")

        try:
            scenes = script.get("scenes", [])
            num_scenes = len(scenes)
            await self.emit(
                "progress",
                f"Generando video Kling a partir de imagen ({num_scenes} escenas de {duration_seconds}s c/u)..."
            )

            # Generate video using Kling
            kling_video_path = await self._generate_kling_video(image_path, duration_seconds)

            if not kling_video_path or not os.path.exists(kling_video_path):
                return SkillResult(
                    status="failed",
                    outputs={"error": "Failed to generate Kling video"}
                )

            # Split the generated video into N equal clips for each scene
            video_dir = os.path.join(settings.outputs_dir, "video")
            os.makedirs(video_dir, exist_ok=True)

            await self.emit("progress", f"Dividiendo video en {num_scenes} clips...")
            scene_clips = await self._split_video_into_scenes(
                kling_video_path, num_scenes, video_dir
            )

            if not scene_clips:
                return SkillResult(
                    status="failed",
                    outputs={"error": "Failed to split video into scenes"}
                )

            # Create motion metadata
            motion_metadata = []
            for i, scene_path in enumerate(scene_clips):
                motion_metadata.append({
                    "scene_index": i,
                    "image_path": image_path,
                    "motion_type": "kling_generated",
                    "motion_direction": None,
                    "duration_seconds": duration_seconds,
                    "video_path": scene_path,
                })

            await self.emit(
                "step_complete",
                f"Video Kling generado y dividido en {len(scene_clips)} clips",
                data={"video_paths": scene_clips},
            )

            return SkillResult(
                status="completed",
                outputs={
                    "video_paths": scene_clips,
                    "motion_metadata": motion_metadata,
                }
            )

        except Exception as e:
            await self.emit("progress", f"❌ Error: {e}")
            return SkillResult(
                status="failed",
                outputs={"error": str(e)}
            )

    async def _generate_kling_video(self, image_path: str, duration: int) -> str | None:
        """Generate video using fal.ai Kling API via async queue."""
        # Read image
        with open(image_path, "rb") as f:
            image_data = f.read()

        # Upload image and submit job
        async with httpx.AsyncClient() as client:
            # Submit job
            await self.emit("progress", "Enviando imagen a Kling...")
            files = {
                "image": ("image.jpg", image_data, "image/jpeg"),
            }
            data = {
                "duration": min(duration, 10),  # Kling max 10s
                "prompt": "Professional product video with smooth cinematic motion",
                "negative_prompt": "",
            }

            headers = {
                "Authorization": f"Key {settings.fal_api_key}",
            }

            try:
                submit_response = await client.post(
                    KLING_API_URL,
                    files=files,
                    data=data,
                    headers=headers,
                    timeout=60.0,
                )
                submit_response.raise_for_status()
            except httpx.HTTPError as e:
                await self.emit("progress", f"❌ Failed to submit to Kling: {e}")
                return None

            result = submit_response.json()
            request_id = result.get("request_id")

            if not request_id:
                await self.emit("progress", f"❌ No request_id from Kling API")
                return None

            await self.emit("progress", f"Job ID: {request_id}, esperando respuesta...")

            # Poll for completion
            start_time = time.time()
            while time.time() - start_time < MAX_WAIT_SECONDS:
                await asyncio.sleep(5)  # Check every 5 seconds

                try:
                    status_response = await client.get(
                        f"{KLING_STATUS_URL}/{request_id}",
                        headers=headers,
                        timeout=30.0,
                    )
                    status_response.raise_for_status()
                except httpx.HTTPError:
                    continue

                status_result = status_response.json()
                status = status_result.get("status")

                if status == "completed":
                    await self.emit("progress", "✅ Video Kling generado")
                    video_url = status_result.get("data", {}).get("video", {}).get("url")
                    if video_url:
                        # Download video
                        return await self._download_video(video_url)
                    else:
                        await self.emit("progress", "❌ No video URL in response")
                        return None

                elif status == "failed":
                    await self.emit("progress", f"❌ Kling generation failed: {status_result}")
                    return None

                else:
                    await self.emit("progress", f"⏳ Status: {status}...")

            await self.emit("progress", f"❌ Kling generation timeout ({MAX_WAIT_SECONDS}s)")
            return None

    async def _download_video(self, url: str) -> str | None:
        """Download video from URL."""
        video_dir = os.path.join(settings.outputs_dir, "video")
        os.makedirs(video_dir, exist_ok=True)
        video_path = os.path.join(video_dir, f"{self.run_id}_kling_generated.mp4")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=60.0)
                response.raise_for_status()

            with open(video_path, "wb") as f:
                f.write(response.content)

            return video_path
        except Exception as e:
            await self.emit("progress", f"❌ Failed to download video: {e}")
            return None

    async def _split_video_into_scenes(
        self, video_path: str, num_scenes: int, output_dir: str
    ) -> list[str]:
        """Split video into N equal-duration clips."""
        if num_scenes <= 0:
            return []

        # Get video duration
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", video_path
                ],
                capture_output=True, text=True, timeout=10
            )
            total_duration = float(result.stdout.strip())
        except Exception:
            return []

        scene_duration = total_duration / num_scenes
        scene_clips = []

        for i in range(num_scenes):
            start_time = i * scene_duration
            output_path = os.path.join(output_dir, f"{self.run_id}_kling_scene_{i}.mp4")

            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-ss", str(start_time),
                "-t", str(scene_duration),
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
                "-c:a", "aac",
                output_path
            ]

            try:
                subprocess.run(cmd, capture_output=True, timeout=120)
                if os.path.exists(output_path):
                    scene_clips.append(output_path)
                    await self.emit("progress", f"✅ Clip {i+1}/{num_scenes} extraído")
            except Exception as e:
                await self.emit("progress", f"⚠️  Failed to extract clip {i+1}: {e}")

        return scene_clips
