from __future__ import annotations

import json
import os
from typing import Any

from sqlmodel.ext.asyncio.session import AsyncSession

from api.config import settings
from api.events import EventBus
from pipelines.base_pipeline import BasePipeline, StepDefinition
from skills.brand_analyzer import BrandAnalyzer
from skills.script_generator import ScriptGenerator
from skills.image_generator import ImageGenerator
from skills.voice_generator import VoiceGenerator
from skills.assembler import Assembler
from skills.video_animator import VideoAnimator


class _BrandLoadSkill:
    """Thin skill: loads an existing brand profile or runs brand analysis."""
    skill_name = "brand_load"

    def __init__(self, event_bus: EventBus, run_id: str, step_index: int = 0, db_session=None):
        self.event_bus = event_bus
        self.run_id = run_id
        self.step_index = step_index
        self.db = db_session

    async def run(self, inputs: dict[str, Any], interactive: bool = False):
        from skills import SkillResult
        slug = inputs["brand_slug"]
        path = os.path.join(settings.brands_dir, f"{slug}.json")
        if os.path.exists(path):
            with open(path) as f:
                profile = json.load(f)
        else:
            # Auto-analyze if brand JSON doesn't exist but URL was given
            from api.events import PipelineEvent
            from datetime import datetime
            if inputs.get("brand_url"):
                analyzer = BrandAnalyzer(self.event_bus, self.run_id, self.db, self.step_index)
                res = await analyzer.run({"url": inputs["brand_url"], "name": slug}, interactive)
                profile = res.outputs.get("profile", {})
            else:
                profile = {"name": slug, "slug": slug}
        # Inject character_description from inputs if provided
        if inputs.get("character_description"):
            profile["character_anchor"] = inputs["character_description"]
        return SkillResult(status="completed", outputs={"profile": profile, "brand_slug": slug})


class UGCPipeline(BasePipeline):
    pipeline_type = "ugc"

    def __init__(self, event_bus: EventBus, run_id: str, db_session: AsyncSession | None = None):
        super().__init__(event_bus, run_id, db_session)

    def build_steps(self, inputs: dict[str, Any]) -> list[StepDefinition]:
        return [
            StepDefinition(
                name="brand_load",
                skill_class=_BrandLoadSkill,
                skill_kwargs={"db_session": self.db},
            ),
            StepDefinition(
                name="script_generate",
                skill_class=ScriptGenerator,
                skill_kwargs={},
            ),
            StepDefinition(
                name="image_generate",
                skill_class=ImageGenerator,
                skill_kwargs={},
            ),
            StepDefinition(
                name="voice_generate",
                skill_class=VoiceGenerator,
                skill_kwargs={},
            ),
            StepDefinition(
                name="video_assemble",
                skill_class=Assembler,
                skill_kwargs={},
            ),
            StepDefinition(
                name="video_animate",
                skill_class=VideoAnimator,
                skill_kwargs={},
            ),
        ]
