from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from api.events import EventBus, PipelineEvent


@dataclass
class SkillResult:
    status: str  # "completed" | "paused" | "failed"
    outputs: dict[str, Any] = field(default_factory=dict)
    feedback_used: str | None = None


class BaseSkill(ABC):
    skill_name: str = "base"

    def __init__(self, event_bus: EventBus, run_id: str, step_index: int = 0):
        self.event_bus = event_bus
        self.run_id = run_id
        self.step_index = step_index

    async def emit(
        self,
        event_type: str,
        message: str,
        data: dict[str, Any] | None = None,
        step_name: str | None = None,
    ) -> None:
        event = PipelineEvent(
            run_id=self.run_id,
            event_type=event_type,
            step_name=step_name or self.skill_name,
            step_index=self.step_index,
            steps_total=None,
            message=message,
            data=data or {},
            timestamp=datetime.utcnow(),
        )
        await self.event_bus.emit(event)

    async def request_feedback(
        self,
        prompt: str,
        preview_data: dict[str, Any],
        interactive: bool,
    ) -> str | None:
        if not interactive:
            return None

        await self.emit(
            "step_paused",
            prompt,
            data={"preview": preview_data, "prompt": prompt},
        )
        feedback = await self.event_bus.wait_for_feedback(self.run_id)
        return feedback

    @abstractmethod
    async def run(self, inputs: dict[str, Any], interactive: bool = False) -> SkillResult:
        ...
