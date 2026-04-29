from __future__ import annotations

import asyncio
import base64
import os
from typing import Any

import httpx
from openai import AsyncOpenAI

from api.config import settings
from api.events import EventBus
from skills import BaseSkill, SkillResult

SIZE_VERTICAL = "1024x1792"   # 9:16 for Reels / TikTok
SIZE_SQUARE = "1024x1024"
SIZE_LANDSCAPE = "1792x1024"

PLATFORM_SIZES = {
    "tiktok": SIZE_VERTICAL,
    "instagram_reel": SIZE_VERTICAL,
    "youtube_short": SIZE_VERTICAL,
    "instagram_post": SIZE_SQUARE,
    "youtube": SIZE_LANDSCAPE,
}


def _build_image_prompt(
    visual_description: str,
    character_anchor: str,
    style_notes: str,
    scene_index: int,
    brand_colors: list[str] | None = None,
    color_mood: str = "",
) -> str:
    parts = []
    if character_anchor:
        parts.append(f"Character: {character_anchor}")
    parts.append(visual_description)
    if style_notes:
        parts.append(f"Visual style: {style_notes}")

    # Add brand colors to prompt
    if brand_colors:
        colors_str = ", ".join(brand_colors)
        parts.append(f"Color palette: {colors_str}. Use these brand colors prominently")
    if color_mood:
        parts.append(f"Color mood: {color_mood}")

    parts.append("Photorealistic, high quality, professional lighting")
    if scene_index == 0:
        parts.append("Eye-catching, strong composition for hook scene")
    return ". ".join(p.strip(". ") for p in parts)


class ImageGenerator(BaseSkill):
    skill_name = "image_generator"

    def __init__(self, event_bus: EventBus, run_id: str, step_index: int = 0):
        super().__init__(event_bus, run_id, step_index)
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._semaphore = asyncio.Semaphore(3)

    async def run(self, inputs: dict[str, Any], interactive: bool = False) -> SkillResult:
        script: dict = inputs["script"]
        brand_slug: str = inputs.get("brand_slug", "")
        platform: str = inputs.get("platform", "tiktok")
        profile: dict = inputs.get("profile", {})
        character_anchor: str = profile.get("character_anchor", "")
        style_notes: str = profile.get("style_notes", "")
        size = PLATFORM_SIZES.get(platform, SIZE_VERTICAL)

        # Extract brand colors
        brand_colors = profile.get("colors", {})
        color_palette = brand_colors.get("palette", []) or [
            brand_colors.get("primary", ""),
            brand_colors.get("secondary", ""),
        ]
        color_palette = [c for c in color_palette if c]
        color_mood = brand_colors.get("mood", "")

        scenes = script.get("scenes", [])
        await self.emit("step_start", f"Generando {len(scenes)} imágenes con {settings.image_model}...")

        image_paths = await self._generate_all(
            scenes, character_anchor, style_notes, size, interactive,
            brand_colors=color_palette, color_mood=color_mood
        )

        await self.emit(
            "step_complete",
            f"Generadas {len(image_paths)} imágenes",
            data={"image_paths": image_paths},
        )
        return SkillResult(status="completed", outputs={"image_paths": image_paths})

    async def generate_single(
        self,
        visual_description: str,
        character_anchor: str = "",
        style_notes: str = "",
        size: str = SIZE_VERTICAL,
        scene_index: int = 0,
        save_path: str | None = None,
        brand_colors: list[str] | None = None,
        color_mood: str = "",
    ) -> str:
        prompt = _build_image_prompt(
            visual_description, character_anchor, style_notes, scene_index,
            brand_colors=brand_colors, color_mood=color_mood
        )
        async with self._semaphore:
            is_gpt_image = settings.image_model.startswith("gpt-image")
            kwargs: dict = {
                "model": settings.image_model,
                "prompt": prompt[:4000],
                "n": 1,
            }
            if is_gpt_image:
                # gpt-image-2: supports 1024x1024, 1536x1024, 1024x1536
                kwargs["size"] = "1024x1536"
                kwargs["quality"] = "high"
            else:
                # dall-e-3
                kwargs["size"] = size  # type: ignore[assignment]
                kwargs["quality"] = "hd"
            response = await self.client.images.generate(**kwargs)

        if save_path is None:
            images_dir = os.path.join(settings.outputs_dir, "images")
            os.makedirs(images_dir, exist_ok=True)
            save_path = os.path.join(images_dir, f"{self.run_id}_scene_{scene_index}.png")

        img_data = response.data[0]
        if getattr(img_data, "b64_json", None):
            import base64
            with open(save_path, "wb") as f:
                f.write(base64.b64decode(img_data.b64_json))
        elif getattr(img_data, "url", None):
            await self._download_image(img_data.url, save_path)
        else:
            raise ValueError("OpenAI image response has neither b64_json nor url")
        return save_path

    async def _generate_all(
        self,
        scenes: list[dict],
        character_anchor: str,
        style_notes: str,
        size: str,
        interactive: bool,
        brand_colors: list[str] | None = None,
        color_mood: str = "",
    ) -> list[str]:
        tasks = [
            self.generate_single(
                visual_description=s.get("visual_description", ""),
                character_anchor=character_anchor,
                style_notes=style_notes,
                size=size,
                scene_index=s.get("index", i),
                brand_colors=brand_colors,
                color_mood=color_mood,
            )
            for i, s in enumerate(scenes)
        ]
        paths: list[str] = []
        for coro, scene in zip(tasks, scenes):
            path = await coro
            paths.append(path)
            preview_data: dict[str, Any] = {"image_path": path, "scene_index": scene.get("index", 0)}
            try:
                with open(path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                preview_data["data_url"] = f"data:image/png;base64,{b64}"
            except Exception:
                pass
            await self.emit(
                "progress",
                f"Imagen escena {scene.get('index', 0) + 1} generada",
                data=preview_data,
            )
            if interactive and scene.get("index", 0) == 0:
                feedback = await self.request_feedback(
                    "¿El personaje/estilo visual es correcto? Aprueba para continuar con las demás escenas.",
                    preview_data,
                    interactive,
                )
                if feedback and feedback.strip().lower() not in ("ok", "aprobado", "approved", ""):
                    character_anchor = f"{character_anchor}. Additional notes: {feedback}"
        return paths

    async def _download_image(self, url: str, save_path: str) -> None:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(resp.content)
