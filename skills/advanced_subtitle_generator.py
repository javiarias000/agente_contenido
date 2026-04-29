"""Skill to generate robust subtitles with proper validation."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from api.config import settings
from api.events import EventBus
from skills import BaseSkill, SkillResult


def _sec_to_srt(seconds: float) -> str:
    """Convert seconds to SRT format: HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _write_srt_safe(words: list[dict], path: str, min_duration: float = 0.5, max_duration: float = 3600.0) -> bool:
    """Write SRT file with validation.

    Args:
        words: List of {"word": str, "start": float, "end": float}
        path: Output SRT file path
        min_duration: Minimum duration for a subtitle block (seconds)
        max_duration: Maximum allowed duration (clamps SRT to valid range)

    Returns:
        True if successful, False if validation failed
    """
    if not words:
        return False

    try:
        with open(path, "w", encoding="utf-8") as f:
            chunk_size = 8
            chunks = [words[i : i + chunk_size] for i in range(0, len(words), chunk_size)]
            written_count = 0

            for chunk in chunks:
                start = chunk[0].get("start", 0.0)
                end = chunk[-1].get("end", start + min_duration)

                # Ensure minimum duration
                if end - start < min_duration:
                    end = start + min_duration

                # Clamp to max_duration to prevent out-of-range SRT
                if start >= max_duration:
                    break
                if end > max_duration:
                    end = max_duration

                text = " ".join(w.get("word", "") for w in chunk).strip()

                if not text:
                    continue

                written_count += 1
                f.write(f"{written_count}\n")
                f.write(f"{_sec_to_srt(start)} --> {_sec_to_srt(end)}\n")
                f.write(f"{text}\n\n")

        return os.path.getsize(path) > 0

    except Exception as e:
        print(f"Error writing SRT: {e}")
        return False


class AdvancedSubtitleGenerator(BaseSkill):
    """Generate subtitles with robust error handling and validation."""

    skill_name = "advanced_subtitle_generator"

    def __init__(
        self,
        event_bus: EventBus,
        run_id: str,
        step_index: int = 0,
    ):
        super().__init__(event_bus, run_id, step_index)
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def run(self, inputs: dict[str, Any], interactive: bool = False) -> SkillResult:
        """Generate subtitles from audio file.

        Expected inputs:
            - full_voiceover_path: Path to complete audio MP3
            - script: Script dict with scenes[i].speaker_text
        """
        audio_path = inputs.get("full_voiceover_path")
        script = inputs.get("script", {})

        if not audio_path or not os.path.exists(audio_path):
            await self.emit("progress", "⚠️ No audio file, skipping subtitles")
            return SkillResult(
                status="completed",
                outputs={"srt_path": "", "srt_valid": False}
            )

        await self.emit("step_start", "Generando subtítulos...")

        try:
            # Transcribe with Whisper
            await self.emit("progress", "Transcribiendo audio...")
            try:
                with open(audio_path, "rb") as f:
                    transcript = await self.client.audio.transcriptions.create(
                        model=settings.whisper_model,
                        file=f,
                        response_format="verbose_json",
                        timestamp_granularities=["word"],
                    )
            except Exception as e:
                # Handle API key errors gracefully
                if "401" in str(e) or "invalid_api_key" in str(e).lower():
                    await self.emit("progress", "⚠️ API key invalid/missing, skipping transcription")
                    return SkillResult(
                        status="completed",
                        outputs={"srt_path": "", "srt_valid": False, "api_error": True}
                    )
                raise

            # Extract words with timing
            words = []
            if hasattr(transcript, "words") and transcript.words:
                words = [
                    {
                        "word": w.word,
                        "start": w.start,
                        "end": w.end,
                    }
                    for w in transcript.words
                ]
                await self.emit(
                    "progress",
                    f"Extracted {len(words)} words with timing"
                )
            elif hasattr(transcript, "segments") and transcript.segments:
                # Fallback: use segments if words not available
                for seg in transcript.segments:
                    words.append({
                        "word": seg.text.strip(),
                        "start": seg.start,
                        "end": seg.end,
                    })
                await self.emit(
                    "progress",
                    f"Extracted {len(words)} segments (no word-level timing)"
                )
            else:
                # Last resort: use full transcript as single block
                if hasattr(transcript, "text"):
                    words.append({
                        "word": transcript.text,
                        "start": 0.0,
                        "end": 10.0,  # Estimate
                    })
                    await self.emit("progress", "Using full transcript as single block")

            if not words:
                await self.emit("progress", "❌ No transcript extracted")
                return SkillResult(
                    status="completed",
                    outputs={"srt_path": "", "srt_valid": False}
                )

            # Write SRT file with audio duration limit
            import subprocess
            try:
                result = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                     "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
                    capture_output=True, text=True, timeout=10,
                )
                max_audio_duration = float(result.stdout.strip()) if result.stdout else 3600.0
            except Exception:
                max_audio_duration = 3600.0

            srt_dir = os.path.join(settings.outputs_dir, "video")
            os.makedirs(srt_dir, exist_ok=True)
            srt_path = os.path.join(srt_dir, f"{self.run_id}.srt")

            success = _write_srt_safe(words, srt_path, max_duration=max_audio_duration)

            if success:
                size = os.path.getsize(srt_path)
                await self.emit(
                    "step_complete",
                    f"Subtítulos generados ({size} bytes)",
                    data={"srt_path": srt_path, "words_count": len(words)}
                )
                return SkillResult(
                    status="completed",
                    outputs={
                        "srt_path": srt_path,
                        "srt_valid": True,
                        "words_count": len(words),
                    }
                )
            else:
                await self.emit("progress", "❌ SRT validation failed")
                return SkillResult(
                    status="completed",
                    outputs={"srt_path": "", "srt_valid": False}
                )

        except Exception as e:
            await self.emit("progress", f"❌ Error: {e}")
            return SkillResult(
                status="completed",
                outputs={"srt_path": "", "srt_valid": False}
            )
