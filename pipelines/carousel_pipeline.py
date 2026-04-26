from __future__ import annotations

from typing import Any
from sqlmodel.ext.asyncio.session import AsyncSession
from api.events import EventBus
from pipelines.base_pipeline import BasePipeline, StepDefinition


class CarouselPipeline(BasePipeline):
    pipeline_type = "carousel"

    def __init__(self, event_bus: EventBus, run_id: str, db_session: AsyncSession | None = None):
        super().__init__(event_bus, run_id, db_session)

    def build_steps(self, inputs: dict[str, Any]) -> list[StepDefinition]:
        from skills.script_generator import ScriptGenerator
        from skills.image_generator import ImageGenerator
        return [
            StepDefinition(name="outline_slides", skill_class=ScriptGenerator, skill_kwargs={}),
            StepDefinition(name="render_slides", skill_class=ImageGenerator, skill_kwargs={}),
        ]
