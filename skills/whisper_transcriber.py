from __future__ import annotations

import os
from typing import Any

from openai import AsyncOpenAI

from api.config import settings
from api.events import EventBus
from skills import BaseSkill, SkillResult


class WhisperTranscriber(BaseSkill):
    """Transcribes full voiceover → word-level timestamps for animated captions."""
    skill_name = "whisper_transcriber"

    def __init__(self, event_bus: EventBus, run_id: str, step_index: int = 0):
        super().__init__(event_bus, run_id, step_index)
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def run(self, inputs: dict[str, Any], interactive: bool = False) -> SkillResult:
        path = inputs.get("full_voiceover_path", "")
        if not path or not os.path.exists(path):
            await self.emit("log", "No voiceover found — skipping transcription")
            return SkillResult(status="completed", outputs={"transcript_words": []})

        await self.emit("step_start", "Transcribiendo audio con Whisper...")

        with open(path, "rb") as f:
            transcript = await self.client.audio.transcriptions.create(
                model=settings.whisper_model,
                file=f,
                response_format="verbose_json",
                timestamp_granularities=["word"],
            )

        words: list[dict] = []
        if hasattr(transcript, "words") and transcript.words:
            words = [
                {"word": w.word.strip(), "start": float(w.start), "end": float(w.end)}
                for w in transcript.words
                if w.word.strip()
            ]
        elif hasattr(transcript, "segments") and transcript.segments:
            for seg in transcript.segments:
                words.append({
                    "word": seg.text.strip(),
                    "start": float(seg.start),
                    "end": float(seg.end),
                })

        await self.emit(
            "step_complete",
            f"Transcripción completa: {len(words)} palabras",
            data={"word_count": len(words)},
        )
        return SkillResult(status="completed", outputs={"transcript_words": words})
