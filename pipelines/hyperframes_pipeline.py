from __future__ import annotations

import json
import os
from typing import Any

from sqlmodel.ext.asyncio.session import AsyncSession

from api.config import settings
from api.events import EventBus
from pipelines.base_pipeline import BasePipeline, StepDefinition
from skills.script_generator import ScriptGenerator
from skills.voice_generator import VoiceGenerator
from skills.whisper_transcriber import WhisperTranscriber
from skills.hyperframes_composer import HyperFramesComposer
from skills.hyperframes_renderer import HyperFramesRenderer


class _BrandLoadSkill:
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
        profile = {}
        if os.path.exists(path):
            with open(path) as f:
                profile = json.load(f)
        else:
            profile = {"name": slug, "slug": slug}

        if inputs.get("character_description"):
            profile["character_anchor"] = inputs["character_description"]

        return SkillResult(status="completed", outputs={"profile": profile, "brand_slug": slug})


class HyperFramesPipeline(BasePipeline):
    """
    Full HyperFrames video pipeline.
    Flow: brand_load → script_generate → voice_generate →
          whisper_transcribe → hyperframes_compose → hyperframes_render
    """
    pipeline_type = "hyperframes"

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
                name="voice_generate",
                skill_class=VoiceGenerator,
                skill_kwargs={},
            ),
            StepDefinition(
                name="whisper_transcribe",
                skill_class=WhisperTranscriber,
                skill_kwargs={},
            ),
            StepDefinition(
                name="hyperframes_compose",
                skill_class=HyperFramesComposer,
                skill_kwargs={},
            ),
            StepDefinition(
                name="hyperframes_render",
                skill_class=HyperFramesRenderer,
                skill_kwargs={},
            ),
        ]
