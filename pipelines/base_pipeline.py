from __future__ import annotations

import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlmodel.ext.asyncio.session import AsyncSession

from api.database import AsyncSessionLocal
from api.events import EventBus, PipelineEvent
from api.models import PipelineRun, PipelineStep
from sqlmodel import select


@dataclass
class StepDefinition:
    name: str
    skill_class: type
    skill_kwargs: dict[str, Any]


class BasePipeline(ABC):
    pipeline_type: str = "base"

    def __init__(self, event_bus: EventBus, run_id: str, db_session: AsyncSession | None = None):
        self.event_bus = event_bus
        self.run_id = run_id
        self.db = db_session

    @abstractmethod
    def build_steps(self, inputs: dict[str, Any]) -> list[StepDefinition]:
        ...

    async def execute(self, inputs: dict[str, Any], interactive: bool = False) -> dict[str, Any]:
        steps = self.build_steps(inputs)
        total = len(steps)
        context: dict[str, Any] = {**inputs}

        await self._update_run(status="running", steps_total=total, current_step=steps[0].name if steps else None)
        await self._emit("pipeline_start", f"Iniciando pipeline {self.pipeline_type}", steps_total=total)

        for idx, step_def in enumerate(steps):
            step_name = step_def.name

            # Resume: skip if already completed
            if await self._step_completed(step_name):
                cached = await self._get_step_output(step_name)
                if cached:
                    context.update(cached)
                await self._emit("step_complete", f"[cached] {step_name}", step_name=step_name, step_index=idx, steps_total=total)
                continue

            await self._update_run(current_step=step_name, steps_completed=idx)
            await self._update_step(step_name, idx, "running", input_data=context)
            await self._emit("step_start", f"Iniciando: {step_name}", step_name=step_name, step_index=idx, steps_total=total)

            try:
                skill = step_def.skill_class(
                    event_bus=self.event_bus,
                    run_id=self.run_id,
                    step_index=idx,
                    **step_def.skill_kwargs,
                )
                result = await skill.run(context, interactive=interactive)
                context.update(result.outputs)
                await self._update_step(step_name, idx, "completed", output_data=result.outputs)
                await self._emit("step_complete", f"Completado: {step_name}", step_name=step_name, step_index=idx, steps_total=total)
            except Exception as exc:
                tb = traceback.format_exc()
                await self._update_run(status="failed", error_message=str(exc))
                await self._update_step(step_name, idx, "failed")
                await self._emit("pipeline_failed", f"Error en {step_name}: {exc}", step_name=step_name)
                raise

        await self._update_run(status="completed", steps_completed=total)
        await self._emit("pipeline_complete", f"Pipeline {self.pipeline_type} completado", steps_total=total)
        return context

    async def _emit(
        self,
        event_type: str,
        message: str,
        step_name: str | None = None,
        step_index: int | None = None,
        steps_total: int | None = None,
        data: dict | None = None,
    ) -> None:
        event = PipelineEvent(
            run_id=self.run_id,
            event_type=event_type,
            step_name=step_name,
            step_index=step_index,
            steps_total=steps_total,
            message=message,
            data=data or {},
            timestamp=datetime.utcnow(),
        )
        await self.event_bus.emit(event)

    async def _update_run(self, **kwargs) -> None:
        if not self.db:
            return
        result = await self.db.exec(select(PipelineRun).where(PipelineRun.run_id == self.run_id))
        run = result.first()
        if run:
            for k, v in kwargs.items():
                setattr(run, k, v)
            run.updated_at = datetime.utcnow()
            self.db.add(run)
            await self.db.commit()

    async def _update_step(
        self,
        step_name: str,
        step_index: int,
        status: str,
        input_data: dict | None = None,
        output_data: dict | None = None,
    ) -> None:
        if not self.db:
            return
        result = await self.db.exec(
            select(PipelineStep).where(
                PipelineStep.run_id == self.run_id,
                PipelineStep.step_name == step_name,
            )
        )
        step = result.first()
        if step is None:
            step = PipelineStep(run_id=self.run_id, step_name=step_name, step_index=step_index)
        step.status = status
        if input_data is not None:
            step.input_data = {k: v for k, v in input_data.items() if isinstance(v, (str, int, float, bool, list, dict, type(None)))}
        if output_data is not None:
            step.output_data = output_data
        if status == "running":
            step.started_at = datetime.utcnow()
        if status in ("completed", "failed"):
            step.completed_at = datetime.utcnow()
            if step.started_at:
                step.duration_ms = int((step.completed_at - step.started_at).total_seconds() * 1000)
        self.db.add(step)
        await self.db.commit()

    async def _step_completed(self, step_name: str) -> bool:
        if not self.db:
            return False
        result = await self.db.exec(
            select(PipelineStep).where(
                PipelineStep.run_id == self.run_id,
                PipelineStep.step_name == step_name,
                PipelineStep.status == "completed",
            )
        )
        return result.first() is not None

    async def _get_step_output(self, step_name: str) -> dict | None:
        if not self.db:
            return None
        result = await self.db.exec(
            select(PipelineStep).where(
                PipelineStep.run_id == self.run_id,
                PipelineStep.step_name == step_name,
            )
        )
        step = result.first()
        return step.output_data if step else None
