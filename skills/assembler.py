from __future__ import annotations

import json
import os
import subprocess
import tempfile
from typing import Any

from openai import AsyncOpenAI

from api.config import settings
from api.events import EventBus
from skills import BaseSkill, SkillResult

OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920
OUTPUT_FPS = 30


def _get_audio_duration(path: str) -> float:
    """Use ffprobe to get audio duration in seconds."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, timeout=10,
        )
        return float(result.stdout.strip())
    except Exception:
        return 3.0


def _write_srt(words: list[dict], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        chunk_size = 8
        chunks = [words[i:i + chunk_size] for i in range(0, len(words), chunk_size)]
        for idx, chunk in enumerate(chunks, 1):
            start = chunk[0]["start"]
            end = chunk[-1]["end"]
            text = " ".join(w["word"] for w in chunk)
            f.write(f"{idx}\n")
            f.write(f"{_sec_to_srt(start)} --> {_sec_to_srt(end)}\n")
            f.write(f"{text}\n\n")


def _sec_to_srt(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


class Assembler(BaseSkill):
    skill_name = "assembler"

    def __init__(self, event_bus: EventBus, run_id: str, step_index: int = 0):
        super().__init__(event_bus, run_id, step_index)
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def run(self, inputs: dict[str, Any], interactive: bool = False) -> SkillResult:
        image_paths: list[str] = inputs["image_paths"]
        audio_paths: list[str] = inputs["audio_paths"]
        full_voiceover_path: str = inputs["full_voiceover_path"]
        script: dict = inputs.get("script", {})

        video_dir = os.path.join(settings.outputs_dir, "video")
        os.makedirs(video_dir, exist_ok=True)

        await self.emit("step_start", "Ensamblando video final...")

        # 1. Build per-scene clips via ffmpeg
        await self.emit("progress", "Construyendo clips por escena...")
        scene_clips = await self._build_scene_clips(image_paths, audio_paths)

        # 2. Concatenate
        await self.emit("progress", "Concatenando escenas...")
        concat_path = os.path.join(video_dir, f"{self.run_id}_concat.mp4")
        self._concatenate_clips(scene_clips, concat_path)

        # 3. Generate subtitles
        await self.emit("progress", "Generando subtítulos con Whisper...")
        srt_path = os.path.join(video_dir, f"{self.run_id}.srt")
        await self._generate_subtitles(full_voiceover_path, srt_path)

        # 4. Burn subtitles
        await self.emit("progress", "Grabando subtítulos en video...")
        subtitled_path = os.path.join(video_dir, f"{self.run_id}_subtitled.mp4")
        self._burn_subtitles(concat_path, srt_path, subtitled_path)

        # 5. Add background music if Suno configured
        final_path = subtitled_path
        if settings.suno_cookie:
            await self.emit("progress", "Agregando música de fondo...")
            try:
                bgm_path = await self._generate_bgm(script)
                if bgm_path:
                    with_music_path = os.path.join(video_dir, f"{self.run_id}_final.mp4")
                    self._mix_audio(subtitled_path, bgm_path, with_music_path)
                    final_path = with_music_path
            except Exception as e:
                await self.emit("log", f"BGM omitida: {e}")

        # Cleanup temp files
        for p in scene_clips + [concat_path]:
            try:
                os.remove(p)
            except Exception:
                pass

        if interactive:
            await self.request_feedback(
                "¿El video final te parece bien? Aprueba o indica cambios.",
                {"video_path": final_path, "srt_path": srt_path},
                interactive,
            )

        await self.emit(
            "step_complete",
            "Video ensamblado",
            data={"final_video_path": final_path, "srt_path": srt_path},
        )
        return SkillResult(
            status="completed",
            outputs={"final_video_path": final_path, "srt_path": srt_path},
        )

    async def _build_scene_clips(
        self, image_paths: list[str], audio_paths: list[str]
    ) -> list[str]:
        clips = []
        for i, (img, audio) in enumerate(zip(image_paths, audio_paths)):
            if not img or not os.path.exists(img):
                continue
            duration = _get_audio_duration(audio) if audio and os.path.exists(audio) else 3.0
            out_path = img.replace(".png", f"_clip_{i}.mp4")
            vf = (
                f"scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:force_original_aspect_ratio=decrease,"
                f"pad={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:(ow-iw)/2:(oh-ih)/2"
            )
            cmd = [
                "ffmpeg", "-y", "-loop", "1", "-i", img,
            ]
            if audio and os.path.exists(audio):
                cmd += ["-i", audio]
            cmd += [
                "-t", str(duration),
                "-vf", vf,
                "-r", str(OUTPUT_FPS),
                "-pix_fmt", "yuv420p",
                "-c:v", "libx264", "-preset", "fast",
            ]
            if audio and os.path.exists(audio):
                cmd += ["-c:a", "aac", "-shortest"]
            cmd.append(out_path)
            result = subprocess.run(cmd, capture_output=True, timeout=120)
            if result.returncode == 0 and os.path.exists(out_path):
                clips.append(out_path)
        return clips

    def _concatenate_clips(self, clip_paths: list[str], output_path: str) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            list_path = f.name
            for p in clip_paths:
                f.write(f"file '{os.path.abspath(p)}'\n")
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path,
             "-c:v", "libx264", "-c:a", "aac", output_path],
            capture_output=True, timeout=300,
        )
        os.remove(list_path)

    async def _generate_subtitles(self, audio_path: str, srt_path: str) -> None:
        if not audio_path or not os.path.exists(audio_path):
            open(srt_path, "w").close()
            return
        with open(audio_path, "rb") as f:
            transcript = await self.client.audio.transcriptions.create(
                model=settings.whisper_model,
                file=f,
                response_format="verbose_json",
                timestamp_granularities=["word"],
            )
        words = []
        if hasattr(transcript, "words") and transcript.words:
            words = [{"word": w.word, "start": w.start, "end": w.end} for w in transcript.words]
        elif hasattr(transcript, "segments") and transcript.segments:
            for seg in transcript.segments:
                words.append({"word": seg.text.strip(), "start": seg.start, "end": seg.end})
        _write_srt(words, srt_path)

    def _burn_subtitles(self, input_path: str, srt_path: str, output_path: str) -> None:
        import shutil
        if not os.path.exists(input_path):
            return
        if not os.path.exists(srt_path) or os.path.getsize(srt_path) == 0:
            shutil.copy(input_path, output_path)
            return
        abs_srt = os.path.abspath(srt_path).replace("\\", "/").replace(":", "\\:")
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", input_path,
             "-vf", f"subtitles='{abs_srt}':force_style='FontSize=24,Bold=1,"
                   "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,"
                   "Alignment=2'",
             "-c:a", "copy", output_path],
            capture_output=True, timeout=300,
        )
        if result.returncode != 0 or not os.path.exists(output_path):
            # Fallback: copy without subtitles
            shutil.copy(input_path, output_path)

    def _mix_audio(self, video_path: str, bgm_path: str, output_path: str) -> None:
        subprocess.run(
            ["ffmpeg", "-y", "-i", video_path, "-i", bgm_path,
             "-filter_complex",
             "[0:a][1:a]amix=inputs=2:duration=first:weights=1 0.15[aout]",
             "-map", "0:v", "-map", "[aout]",
             "-c:v", "copy", "-c:a", "aac", output_path],
            capture_output=True, timeout=300,
        )

    async def _generate_bgm(self, script: dict) -> str | None:
        """Generate background music via Suno API (unofficial)."""
        import httpx
        prompt = f"Upbeat background music for a {script.get('target_platform', 'social media')} video about {script.get('title', 'product')}, no lyrics, 60 seconds"
        headers = {"Authorization": f"Bearer {settings.suno_cookie}"}
        payload = {
            "prompt": prompt,
            "mv": "chirp-v3-5",
            "title": "BGM",
            "tags": "background instrumental upbeat",
            "make_instrumental": True,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://studio-api.suno.ai/api/generate/v2/",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        song_id = data.get("clips", [{}])[0].get("id")
        if not song_id:
            return None

        # Poll for completion
        import asyncio
        for _ in range(30):
            await asyncio.sleep(10)
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.get(
                    f"https://studio-api.suno.ai/api/feed/?ids={song_id}",
                    headers=headers,
                )
                clips = r.json()
            if clips and clips[0].get("status") == "complete":
                audio_url = clips[0]["audio_url"]
                bgm_path = os.path.join(settings.outputs_dir, "audio", f"{self.run_id}_bgm.mp3")
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.get(audio_url)
                with open(bgm_path, "wb") as f:
                    f.write(resp.content)
                return bgm_path
        return None
