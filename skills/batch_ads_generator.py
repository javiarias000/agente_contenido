from __future__ import annotations

import asyncio
import json
import os
import zipfile
from typing import Any

from openai import AsyncOpenAI
from PIL import Image, ImageDraw, ImageFont

from api.config import settings
from api.events import EventBus
from skills import BaseSkill, SkillResult
from skills.image_generator import ImageGenerator

AD_TEMPLATES = [
    {"name": "before_after", "headline": "Before: {problem} → After: {solution}"},
    {"name": "review", "headline": "⭐⭐⭐⭐⭐ '{testimonial}'"},
    {"name": "comparison", "headline": "{competitor} vs {brand}: The Difference"},
    {"name": "benefit", "headline": "{benefit} — Guaranteed"},
    {"name": "urgency", "headline": "Last Chance: {offer}"},
]

COPY_SYSTEM = """Generate ad copy variations. Return JSON array of objects with:
{"template": "string", "headline": "string (max 10 words)", "body": "string (max 20 words)", "cta": "string (max 5 words)"}
Generate exactly {n} variations covering different templates and angles."""


class BatchAdsGenerator(BaseSkill):
    skill_name = "generate_ads"

    def __init__(self, event_bus: EventBus, run_id: str, step_index: int = 0):
        super().__init__(event_bus, run_id, step_index)
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def run(self, inputs: dict[str, Any], interactive: bool = False) -> SkillResult:
        brand_slug: str = inputs.get("brand_slug", "brand")
        num_ads: int = inputs.get("num_ads", 10)
        profile: dict = inputs.get("profile", self._load_brand(brand_slug))
        ads_dir = os.path.join(settings.outputs_dir, "ads", self.run_id)
        os.makedirs(ads_dir, exist_ok=True)

        await self.emit("step_start", f"Generando {num_ads} anuncios estáticos...")

        # 1. Generate copy variants
        await self.emit("progress", "Generando copys con GPT-4o...")
        copies = await self._generate_copies(profile, num_ads)

        # 2. Generate images in batches
        await self.emit("progress", "Generando imágenes base...")
        img_gen = ImageGenerator(self.event_bus, self.run_id, self.step_index)
        # Use a single style scene for all ads
        base_image_path = await img_gen.generate_single(
            visual_description=f"Professional product/lifestyle photo for {profile.get('name', brand_slug)} brand ad, clean background",
            character_anchor=profile.get("character_anchor", ""),
            style_notes=profile.get("style_notes", ""),
            size="1024x1024",
            scene_index=0,
        )

        # 3. Composite ads with Pillow
        await self.emit("progress", "Componiendo anuncios...")
        ad_paths = []
        primary_color = profile.get("colors", {}).get("primary", "#1A73E8")
        for i, copy in enumerate(copies):
            path = await self._composite_ad(base_image_path, copy, ads_dir, i, primary_color)
            ad_paths.append(path)
            await self.emit("progress", f"Anuncio {i + 1}/{len(copies)} creado", data={"ad_path": path})

        # 4. Zip package
        zip_path = os.path.join(settings.outputs_dir, "ads", f"{self.run_id}_ads.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            for p in ad_paths:
                zf.write(p, os.path.basename(p))

        await self.emit("step_complete", f"{len(ad_paths)} anuncios generados", data={"zip_path": zip_path, "ad_paths": ad_paths})
        return SkillResult(status="completed", outputs={"ad_paths": ad_paths, "zip_path": zip_path})

    async def _generate_copies(self, profile: dict, n: int) -> list[dict]:
        prompt = COPY_SYSTEM.replace("{n}", str(n))
        brand_info = {
            "brand": profile.get("name", ""),
            "tone": profile.get("tone_of_voice", ""),
            "audience": profile.get("target_audience", ""),
            "values": profile.get("brand_values", []),
        }
        completion = await self.client.chat.completions.create(
            model=settings.text_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(brand_info)},
            ],
            temperature=0.8,
        )
        data = json.loads(completion.choices[0].message.content)
        return data if isinstance(data, list) else data.get("ads", data.get("variations", []))

    async def _composite_ad(
        self, base_image_path: str, copy: dict, ads_dir: str, idx: int, primary_color: str
    ) -> str:
        img = Image.open(base_image_path).convert("RGB")
        img = img.resize((1080, 1080))
        draw = ImageDraw.Draw(img)

        # Semi-transparent overlay at bottom
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle([(0, 650), (1080, 1080)], fill=(0, 0, 0, 160))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(img)

        # Text
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 52)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
        except Exception:
            font_large = ImageFont.load_default()
            font_small = font_large

        headline = copy.get("headline", "")
        body = copy.get("body", "")
        cta = copy.get("cta", "Learn More")

        draw.text((40, 670), headline, fill="white", font=font_large)
        draw.text((40, 740), body, fill="#CCCCCC", font=font_small)
        # CTA button
        draw.rounded_rectangle([(40, 800), (300, 860)], radius=10, fill=primary_color)
        draw.text((60, 815), cta, fill="white", font=font_small)

        path = os.path.join(ads_dir, f"ad_{idx:03d}_{copy.get('template', 'generic')}.png")
        img.save(path, "PNG")
        return path

    def _load_brand(self, slug: str) -> dict:
        path = os.path.join(settings.brands_dir, f"{slug}.json")
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return {}
