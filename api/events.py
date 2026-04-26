from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class PipelineEvent:
    run_id: str
    event_type: str  # step_start|step_complete|step_error|step_paused|progress|log|pipeline_complete|pipeline_failed
    step_name: str | None
    step_index: int | None
    steps_total: int | None
    message: str
    data: dict[str, Any]
    timestamp: datetime

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "event_type": self.event_type,
            "step_name": self.step_name,
            "step_index": self.step_index,
            "steps_total": self.steps_total,
            "message": self.message,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }


class EventBus:
    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue]] = {}
        self._feedback_queues: dict[str, asyncio.Queue] = {}

    def subscribe(self, run_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._queues.setdefault(run_id, []).append(q)
        return q

    def unsubscribe(self, run_id: str, q: asyncio.Queue) -> None:
        if run_id in self._queues:
            self._queues[run_id].discard(q) if hasattr(self._queues[run_id], "discard") else None
            try:
                self._queues[run_id].remove(q)
            except ValueError:
                pass

    async def emit(self, event: PipelineEvent) -> None:
        for q in list(self._queues.get(event.run_id, [])):
            await q.put(event)

    async def wait_for_feedback(self, run_id: str) -> str | None:
        q: asyncio.Queue = asyncio.Queue()
        self._feedback_queues[run_id] = q
        try:
            feedback = await asyncio.wait_for(q.get(), timeout=600)
            return feedback
        except asyncio.TimeoutError:
            return None
        finally:
            self._feedback_queues.pop(run_id, None)

    async def submit_feedback(self, run_id: str, feedback: str) -> bool:
        q = self._feedback_queues.get(run_id)
        if q is None:
            return False
        await q.put(feedback)
        return True

    def cleanup(self, run_id: str) -> None:
        self._queues.pop(run_id, None)
        self._feedback_queues.pop(run_id, None)
