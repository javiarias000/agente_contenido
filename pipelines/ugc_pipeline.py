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
from skills.animated_image_generator import AnimatedImageGenerator
from skills.voice_generator import VoiceGenerator
from skills.advanced_subtitle_generator import AdvancedSubtitleGenerator
from skills.composed_video_assembler import ComposedVideoAssembler
from skills.image_quality_improver import ImageQualityImprover


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
        from api.events import PipelineEvent
        from datetime import datetime

        slug = inputs["brand_slug"]
        path = os.path.join(settings.brands_dir, f"{slug}.json")

        if os.path.exists(path):
            with open(path) as f:
                profile = json.load(f)
        else:
            # Auto-analyze if brand JSON doesn't exist but URL was given
            if inputs.get("brand_url"):
                analyzer = BrandAnalyzer(self.event_bus, self.run_id, self.db, self.step_index)
                res = await analyzer.run({"url": inputs["brand_url"], "name": slug}, interactive)
                profile = res.outputs.get("profile", {})
            else:
                profile = {"name": slug, "slug": slug}

        # Load brand assets analysis if available
        asset_dir = os.path.join(settings.brands_dir.replace("brands", "brand_assets"), slug)
        if os.path.exists(asset_dir):
            # Load logo analysis
            logo_analysis_path = os.path.join(asset_dir, "logo_analysis.json")
            if os.path.exists(logo_analysis_path):
                with open(logo_analysis_path) as f:
                    logo_analysis = json.load(f)
                    profile["logo_colors"] = logo_analysis.get("all_colors", [])
                    profile["logo_analysis"] = logo_analysis.get("detailed_analyses", {})

            # Load posts analysis
            posts_analysis_path = os.path.join(asset_dir, "posts_analysis.json")
            if os.path.exists(posts_analysis_path):
                with open(posts_analysis_path) as f:
                    posts_analysis = json.load(f)
                    profile["posts_insights"] = posts_analysis

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
                skill_class=AnimatedImageGenerator,
                skill_kwargs={},
            ),
            StepDefinition(
                name="image_enhance",
                skill_class=ImageQualityImprover,
                skill_kwargs={},
            ),
            StepDefinition(
                name="voice_generate",
                skill_class=VoiceGenerator,
                skill_kwargs={},
            ),
            StepDefinition(
                name="subtitle_generate",
                skill_class=AdvancedSubtitleGenerator,
                skill_kwargs={},
            ),
            StepDefinition(
                name="video_assemble",
                skill_class=ComposedVideoAssembler,
                skill_kwargs={},
            ),
        ]
