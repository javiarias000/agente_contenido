from __future__ import annotations

import os
from typing import Any

from elevenlabs.client import AsyncElevenLabs
from openai import AsyncOpenAI

from api.config import settings
from api.events import EventBus
from skills import BaseSkill, SkillResult

DEFAULT_ELEVEN_MODEL = "eleven_multilingual_v2"
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel
OPENAI_TTS_VOICE = "nova"                   # nova | alloy | echo | fable | onyx | shimmer


class VoiceGenerator(BaseSkill):
    skill_name = "voice_generator"

    def __init__(self, event_bus: EventBus, run_id: str, step_index: int = 0):
        super().__init__(event_bus, run_id, step_index)
        self.eleven = AsyncElevenLabs(api_key=settings.elevenlabs_api_key)
        self.openai = AsyncOpenAI(api_key=settings.openai_api_key)

    async def run(self, inputs: dict[str, Any], interactive: bool = False) -> SkillResult:
        script: dict = inputs["script"]
        voice_id: str = inputs.get("voice_id") or DEFAULT_VOICE_ID
        profile: dict = inputs.get("profile", {})
        if profile.get("preferred_voice_id"):
            voice_id = profile["preferred_voice_id"]

        scenes = script.get("scenes", [])
        await self.emit("step_start", f"Generando audio para {len(scenes)} escenas...")

        audio_dir = os.path.join(settings.outputs_dir, "audio")
        os.makedirs(audio_dir, exist_ok=True)

        audio_paths: list[str] = []
        full_text = ""

        for scene in scenes:
            text = scene.get("speaker_text", "")
            if not text.strip():
                audio_paths.append("")
                continue
            idx = scene.get("index", len(audio_paths))
            path = os.path.join(audio_dir, f"{self.run_id}_scene_{idx}.mp3")
            await self._synthesize(text, voice_id, path)
            audio_paths.append(path)
            full_text += f" {text}"
            await self.emit(
                "progress",
                f"Audio escena {idx + 1} generado",
                data={"audio_path": path, "scene_index": idx},
            )

        full_path = os.path.join(audio_dir, f"{self.run_id}_full_voiceover.mp3")
        if full_text.strip():
            await self._synthesize(full_text.strip(), voice_id, full_path)

        if interactive:
            await self.request_feedback(
                "¿La voz y el tono te parecen correctos?",
                {"audio_paths": audio_paths, "full_voiceover": full_path},
                interactive,
            )

        await self.emit(
            "step_complete",
            "Audio generado",
            data={"audio_paths": audio_paths, "full_voiceover_path": full_path},
        )
        return SkillResult(
            status="completed",
            outputs={"audio_paths": audio_paths, "full_voiceover_path": full_path},
        )

    async def _synthesize(self, text: str, voice_id: str, output_path: str) -> None:
        """Try ElevenLabs first; fall back to OpenAI TTS on any error."""
        try:
            await self._synthesize_elevenlabs(text, voice_id, output_path)
        except Exception as e:
            await self.emit("log", f"ElevenLabs falló ({e}), usando OpenAI TTS...")
            await self._synthesize_openai(text, output_path)

    async def _synthesize_elevenlabs(self, text: str, voice_id: str, output_path: str) -> None:
        with open(output_path, "wb") as f:
            async for chunk in self.eleven.text_to_speech.convert(
                voice_id=voice_id,
                text=text,
                model_id=DEFAULT_ELEVEN_MODEL,
                output_format="mp3_44100_128",
            ):
                if chunk:
                    f.write(chunk)

    async def _synthesize_openai(self, text: str, output_path: str) -> None:
        response = await self.openai.audio.speech.create(
            model="tts-1",
            voice=OPENAI_TTS_VOICE,
            input=text[:4096],
            response_format="mp3",
        )
        with open(output_path, "wb") as f:
            f.write(response.content)

    async def list_voices(self) -> list[dict]:
        try:
            result = await self.eleven.voices.get_all()
            return [{"id": v.voice_id, "name": v.name, "provider": "elevenlabs"} for v in result.voices]
        except Exception:
            return [
                {"id": v, "name": v.capitalize(), "provider": "openai"}
                for v in ["alloy", "echo", "fable", "nova", "onyx", "shimmer"]
            ]
