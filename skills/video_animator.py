from __future__ import annotations

import base64
import os
import re
import subprocess
from typing import Any

import requests

from api.config import settings
from api.events import EventBus
from skills import BaseSkill, SkillResult


class VideoAnimator(BaseSkill):
    """Anima videos usando Google Gemini + ffmpeg.

    Gemini analiza la imagen y recomienda movimiento.
    ffmpeg aplica el movimiento al video (zoom, pan, etc).
    """

    skill_name = "video_animator"
    GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

    def __init__(self, event_bus: EventBus, run_id: str, step_index: int = 0):
        super().__init__(event_bus, run_id, step_index)

    async def run(self, inputs: dict[str, Any], interactive: bool = False) -> SkillResult:
        final_video_path: str = inputs.get("final_video_path", "")
        image_paths: list[str] = inputs.get("image_paths", [])

        if not final_video_path or not os.path.exists(final_video_path):
            await self.emit("log", "Sin video final para animar")
            return SkillResult(status="skipped")

        if not settings.google_veo_api_key:
            await self.emit("log", "GOOGLE_VEO_API_KEY no configurada")
            return SkillResult(status="skipped")

        await self.emit("step_start", "Animando video con Gemini + ffmpeg...")

        try:
            reference_image = next(
                (p for p in image_paths if p and os.path.exists(p)), None
            )

            if not reference_image:
                await self.emit("log", "Sin imagen para analizar")
                return SkillResult(status="skipped")

            await self.emit("progress", "1/3 Analizando imagen con Gemini...")
            motion_type = await self._analyze_image_for_motion(reference_image)

            if not motion_type:
                await self.emit("log", "No se pudo analizar imagen")
                return SkillResult(status="skipped")

            await self.emit("progress", f"2/3 Movimiento detectado: {motion_type[:50]}...")

            video_dir = os.path.join(settings.outputs_dir, "video")
            output_path = os.path.join(video_dir, f"{self.run_id}_animated.mp4")

            await self.emit("progress", "3/3 Aplicando movimiento con ffmpeg...")
            success = await self._apply_motion_with_ffmpeg(
                final_video_path, output_path, motion_type
            )

            if success and os.path.exists(output_path):
                size_mb = os.path.getsize(output_path) / (1024 * 1024)
                await self.emit(
                    "step_complete",
                    f"Video animado ({size_mb:.1f} MB)",
                    data={"animated_video_path": output_path},
                )
                return SkillResult(
                    status="completed",
                    outputs={"animated_video_path": output_path},
                )
            else:
                await self.emit("log", "ffmpeg falló, retornando original")
                return SkillResult(
                    status="completed",
                    outputs={"final_video_path": final_video_path},
                )

        except Exception as e:
            await self.emit("log", f"Error: {str(e)[:100]}")
            return SkillResult(status="failed")

    async def _analyze_image_for_motion(self, image_path: str) -> str | None:
        """Analiza imagen con Gemini para determinar tipo de movimiento."""
        try:
            with open(image_path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode()

            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "inlineData": {
                                    "mimeType": "image/png",
                                    "data": image_base64
                                }
                            },
                            {
                                "text": """Analiza esta imagen y recomienda UN SOLO tipo de movimiento de cámara para animarla.

RESPONDE SOLO con UNA de estas opciones (sin explicación):
- zoom_in: acercamiento lento a la imagen
- zoom_out: alejamiento lento de la imagen
- pan_left: movimiento horizontal a la izquierda
- pan_right: movimiento horizontal a la derecha
- pan_up: movimiento vertical hacia arriba
- pan_down: movimiento vertical hacia abajo
- diagonal: zoom in + pan simultáneo

Elige la que sea MÁS apropiada para esta imagen."""
                            }
                        ]
                    }
                ]
            }

            url = f"{self.GEMINI_API_URL}?key={settings.google_veo_api_key}"
            resp = requests.post(url, json=payload, timeout=120)

            if resp.status_code != 200:
                await self.emit("log", f"Gemini error: {resp.status_code}")
                return None

            data = resp.json()
            candidates = data.get("candidates", [])

            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    text = parts[0].get("text", "").strip().lower()
                    # Validar que sea un tipo de movimiento válido
                    valid_motions = ["zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "pan_down", "diagonal"]
                    for motion in valid_motions:
                        if motion in text:
                            return motion
                    # Si Gemini retorna algo que no reconocemos, usa zoom_in por defecto
                    return "zoom_in"

            return None

        except Exception as e:
            await self.emit("log", f"Analysis error: {str(e)[:100]}")
            return None

    async def _apply_motion_with_ffmpeg(
        self, input_video: str, output_video: str, motion_type: str
    ) -> bool:
        """Aplica efecto de movimiento al video usando ffmpeg."""
        try:
            # Define los filtros de ffmpeg según el tipo de movimiento
            ffmpeg_filters = {
                "zoom_in": "scale=iw*1.2:ih*1.2,crop=iw:ih",
                "zoom_out": "scale=iw*0.8:ih*0.8,pad=iw:ih:(ow-iw)/2:(oh-ih)/2:black",
                "pan_left": "crop=iw*0.9:ih:0:0",
                "pan_right": "crop=iw*0.9:ih:iw*0.1:0",
                "pan_up": "crop=iw:ih*0.9:0:0",
                "pan_down": "crop=iw:ih*0.9:0:ih*0.1",
                "diagonal": "scale=iw*1.1:ih*1.1,crop=iw:ih"
            }

            filter_str = ffmpeg_filters.get(motion_type, ffmpeg_filters["zoom_in"])

            await self.emit("log", f"Movimiento: {motion_type}")

            cmd = [
                "ffmpeg",
                "-y",
                "-i", input_video,
                "-vf", f"format=yuv420p,{filter_str}",
                "-c:v", "libx264",
                "-preset", "fast",
                "-c:a", "aac",
                output_video
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=300, text=True)

            if result.returncode == 0 and os.path.exists(output_video):
                await self.emit("log", f"✓ Animación completada: {motion_type}")
                return True
            else:
                await self.emit("log", f"ffmpeg error: {result.stderr[:100]}")
                return False

        except Exception as e:
            await self.emit("log", f"ffmpeg exception: {str(e)[:100]}")
            return False
