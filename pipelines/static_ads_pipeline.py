from __future__ import annotations

from typing import Any
from sqlmodel.ext.asyncio.session import AsyncSession
from api.events import EventBus
from pipelines.base_pipeline import BasePipeline, StepDefinition


class StaticAdsPipeline(BasePipeline):
    pipeline_type = "static_ads"

    def __init__(self, event_bus: EventBus, run_id: str, db_session: AsyncSession | None = None):
        super().__init__(event_bus, run_id, db_session)

    def build_steps(self, inputs: dict[str, Any]) -> list[StepDefinition]:
        from skills.batch_ads_generator import BatchAdsGenerator
        return [
            StepDefinition(name="generate_ads", skill_class=BatchAdsGenerator, skill_kwargs={}),
        ]
