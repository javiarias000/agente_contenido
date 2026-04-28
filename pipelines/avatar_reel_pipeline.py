from __future__ import annotations

from typing import Any
from sqlmodel.ext.asyncio.session import AsyncSession
from api.events import EventBus
from pipelines.base_pipeline import BasePipeline, StepDefinition


class AvatarReelPipeline(BasePipeline):
    pipeline_type = "avatar_reel"

    def __init__(self, event_bus: EventBus, run_id: str, db_session: AsyncSession | None = None):
        super().__init__(event_bus, run_id, db_session)

    def build_steps(self, inputs: dict[str, Any]) -> list[StepDefinition]:
        from skills.script_generator import ScriptGenerator
        from skills.image_generator import ImageGenerator
        from skills.voice_generator import VoiceGenerator
        from skills.lip_sync import LipSyncSkill
        from skills.assembler import Assembler
        from skills.video_animator import VideoAnimator
        return [
            StepDefinition(name="script_generate", skill_class=ScriptGenerator, skill_kwargs={}),
            StepDefinition(name="avatar_image", skill_class=ImageGenerator, skill_kwargs={}),
            StepDefinition(name="voice_generate", skill_class=VoiceGenerator, skill_kwargs={}),
            StepDefinition(name="lip_sync", skill_class=LipSyncSkill, skill_kwargs={}),
            StepDefinition(name="video_assemble", skill_class=Assembler, skill_kwargs={}),
            StepDefinition(name="video_animate", skill_class=VideoAnimator, skill_kwargs={}),
        ]
