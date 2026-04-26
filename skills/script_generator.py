from __future__ import annotations

import asyncio
import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from openai import AsyncOpenAI

from api.config import settings
from api.events import EventBus
from skills import BaseSkill, SkillResult
from skills.templates.base_template import BaseTemplate, TemplateContext
from skills.templates.ugc_sales import UGCSalesTemplate
from skills.templates.competitor import CompetitorTemplate
from skills.templates.trending import TrendingTemplate
from skills.templates.educational import EducationalTemplate

TEMPLATES: dict[str, BaseTemplate] = {
    "sales": UGCSalesTemplate(),
    "competitor": CompetitorTemplate(),
    "trending": TrendingTemplate(),
    "educational": EducationalTemplate(),
}

PLATFORM_CONSTRAINTS = {
    "tiktok": {"max_duration": 60, "style": "fast-paced, native, casual"},
    "instagram_reel": {"max_duration": 90, "style": "polished, aesthetic, engaging"},
    "youtube_short": {"max_duration": 60, "style": "informative, punchy, clear value prop"},
}

OUTLINE_SYSTEM = """You are an expert short-form video scriptwriter. Create a video script outline.
Return JSON with:
{
  "title": "string",
  "hook": "string (first 3 seconds, attention-grabbing opening line)",
  "cta": "string (call to action for the end)",
  "hashtags": ["string"],
  "scene_titles": ["string"] (3-6 scene titles only, no content yet)
}
Return ONLY valid JSON."""

SCENE_SYSTEM = """You are an expert short-form video scriptwriter. Expand this scene into full content.
Return JSON with:
{
  "visual_description": "string (detailed visual prompt for AI image generation, include setting, lighting, mood)",
  "speaker_text": "string (exact words to speak in this scene)",
  "on_screen_text": "string or null (text overlay, caption card, or null if none)"
}
Return ONLY valid JSON."""


@dataclass
class Scene:
    index: int
    title: str
    duration_seconds: int
    visual_description: str
    speaker_text: str
    on_screen_text: str | None


@dataclass
class Script:
    run_id: str
    brand_slug: str
    title: str
    hook: str
    scenes: list[Scene]
    cta: str
    total_duration_seconds: int
    target_platform: str
    hashtags: list[str]
    angle_type: str
    created_at: str


class ScriptGenerator(BaseSkill):
    skill_name = "script_generator"

    def __init__(self, event_bus: EventBus, run_id: str, step_index: int = 0):
        super().__init__(event_bus, run_id, step_index)
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def run(self, inputs: dict[str, Any], interactive: bool = False) -> SkillResult:
        brand_slug: str = inputs["brand_slug"]
        angle_type: str = inputs.get("angle_type", "sales")
        platform: str = inputs.get("platform", "tiktok")
        target_duration: int = inputs.get("target_duration", 60)
        custom_hook: str | None = inputs.get("custom_hook")
        competitor_name: str | None = inputs.get("competitor_name")
        profile: dict = inputs.get("profile") or self._load_brand(brand_slug)

        template = TEMPLATES.get(angle_type, TEMPLATES["sales"])
        template.validate_inputs({**inputs, "competitor_name": competitor_name})

        platform_info = PLATFORM_CONSTRAINTS.get(platform, PLATFORM_CONSTRAINTS["tiktok"])
        ctx = TemplateContext(
            brand_name=profile.get("name", brand_slug),
            tone_of_voice=profile.get("tone_of_voice", "friendly and engaging"),
            target_audience=profile.get("target_audience", "general audience"),
            brand_values=profile.get("brand_values", []),
            style_notes=profile.get("style_notes", ""),
            platform=platform,
            target_duration=target_duration,
        )

        await self.emit("step_start", f"Generando guión para {brand_slug} — ángulo: {angle_type}")

        # Step 1: Outline
        await self.emit("progress", "Generando estructura del guión...")
        outline = await self._generate_outline(ctx, template, platform_info, custom_hook, competitor_name)

        # Step 2: Expand scenes in parallel
        await self.emit("progress", f"Expandiendo {len(outline['scene_titles'])} escenas...")
        seconds_per_scene = target_duration // max(len(outline["scene_titles"]), 1)
        scenes = await self._expand_scenes(outline["scene_titles"], ctx, template, seconds_per_scene)

        script = Script(
            run_id=self.run_id,
            brand_slug=brand_slug,
            title=outline["title"],
            hook=outline["hook"],
            scenes=scenes,
            cta=outline["cta"],
            total_duration_seconds=sum(s.duration_seconds for s in scenes),
            target_platform=platform,
            hashtags=outline.get("hashtags", []),
            angle_type=angle_type,
            created_at=datetime.utcnow().isoformat(),
        )

        # Interactive review
        feedback = await self.request_feedback(
            "¿El guión te parece bien? Aprueba o indica qué cambiar.",
            {"script": asdict(script)},
            interactive,
        )

        if feedback and feedback.strip().lower() not in ("ok", "aprobado", "approved", ""):
            await self.emit("progress", "Refinando guión con feedback...")
            script = await self._refine_script(script, feedback, ctx, template, platform_info, seconds_per_scene)

        # Save
        script_path = await self._save_script(script)
        await self.emit(
            "step_complete",
            "Guión generado",
            data={"script_path": script_path, "title": script.title, "scenes": len(scenes)},
        )
        return SkillResult(
            status="completed",
            outputs={"script": asdict(script), "script_path": script_path},
            feedback_used=feedback,
        )

    async def _generate_outline(
        self,
        ctx: TemplateContext,
        template: BaseTemplate,
        platform_info: dict,
        custom_hook: str | None,
        competitor_name: str | None,
    ) -> dict:
        additions = template.system_prompt_additions(ctx)
        user_content = {
            "brand": ctx.brand_name,
            "audience": ctx.target_audience,
            "tone": ctx.tone_of_voice,
            "platform": f"{ctx.platform} ({platform_info['style']})",
            "max_duration_seconds": ctx.target_duration,
            "brand_values": ctx.brand_values,
        }
        if custom_hook:
            user_content["use_this_hook"] = custom_hook
        if competitor_name:
            user_content["competitor"] = competitor_name

        completion = await self.client.chat.completions.create(
            model=settings.text_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": OUTLINE_SYSTEM + "\n\n" + additions},
                {"role": "user", "content": json.dumps(user_content)},
            ],
            temperature=0.7,
        )
        return json.loads(completion.choices[0].message.content)

    async def _expand_scenes(
        self,
        scene_titles: list[str],
        ctx: TemplateContext,
        template: BaseTemplate,
        seconds_per_scene: int,
    ) -> list[Scene]:
        additions = template.system_prompt_additions(ctx)

        async def expand_one(idx: int, title: str) -> Scene:
            user_content = {
                "scene_title": title,
                "scene_index": idx,
                "brand": ctx.brand_name,
                "style_notes": ctx.style_notes,
                "tone": ctx.tone_of_voice,
                "audience": ctx.target_audience,
                "duration_seconds": seconds_per_scene,
            }
            completion = await self.client.chat.completions.create(
                model=settings.text_model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SCENE_SYSTEM + "\n\n" + additions},
                    {"role": "user", "content": json.dumps(user_content)},
                ],
                temperature=0.7,
            )
            data = json.loads(completion.choices[0].message.content)
            return Scene(
                index=idx,
                title=title,
                duration_seconds=seconds_per_scene,
                visual_description=data.get("visual_description", ""),
                speaker_text=data.get("speaker_text", ""),
                on_screen_text=data.get("on_screen_text"),
            )

        semaphore = asyncio.Semaphore(4)

        async def bounded(idx: int, title: str) -> Scene:
            async with semaphore:
                return await expand_one(idx, title)

        return list(await asyncio.gather(*[bounded(i, t) for i, t in enumerate(scene_titles)]))

    async def _refine_script(
        self,
        script: Script,
        feedback: str,
        ctx: TemplateContext,
        template: BaseTemplate,
        platform_info: dict,
        seconds_per_scene: int,
    ) -> Script:
        outline = await self._generate_outline(ctx, template, platform_info, None, None)
        outline["scene_titles"] = [s.title for s in script.scenes]
        scenes = await self._expand_scenes(
            outline["scene_titles"], ctx, template, seconds_per_scene
        )
        script.scenes = scenes
        script.title = outline.get("title", script.title)
        script.hook = outline.get("hook", script.hook)
        script.cta = outline.get("cta", script.cta)
        return script

    def _load_brand(self, slug: str) -> dict:
        path = os.path.join(settings.brands_dir, f"{slug}.json")
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return {}

    async def _save_script(self, script: Script) -> str:
        scripts_dir = os.path.join(settings.outputs_dir, "scripts")
        os.makedirs(scripts_dir, exist_ok=True)
        path = os.path.join(scripts_dir, f"{self.run_id}_script.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(script), f, ensure_ascii=False, indent=2)
        return path
