from __future__ import annotations

import asyncio
import os
import shutil
from typing import Any

from api.config import settings
from api.events import EventBus
from skills import BaseSkill, SkillResult

# Chromium paths to try in order
_CHROMIUM_CANDIDATES = [
    "/usr/bin/chromium-browser",
    "/usr/bin/chromium",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
]


def _find_chromium() -> str | None:
    for p in _CHROMIUM_CANDIDATES:
        if os.path.exists(p):
            return p
    return shutil.which("chromium-browser") or shutil.which("chromium")


class HyperFramesRenderer(BaseSkill):
    """Renders a HyperFrames HTML composition to MP4 via `npx hyperframes render`."""
    skill_name = "hyperframes_renderer"

    def __init__(self, event_bus: EventBus, run_id: str, step_index: int = 0):
        super().__init__(event_bus, run_id, step_index)

    async def run(self, inputs: dict[str, Any], interactive: bool = False) -> SkillResult:
        composition_path: str = inputs["composition_path"]
        full_voiceover_path: str = inputs.get("full_voiceover_path", "")
        total_duration: float = float(inputs.get("total_duration", 0))

        if not os.path.exists(composition_path):
            raise FileNotFoundError(f"Composition not found: {composition_path}")

        comp_dir = os.path.dirname(composition_path)
        video_dir = os.path.join(settings.outputs_dir, "video")
        os.makedirs(video_dir, exist_ok=True)

        silent_path = os.path.join(video_dir, f"{self.run_id}_hf_silent.mp4")
        final_path = os.path.join(video_dir, f"{self.run_id}_final.mp4")

        await self.emit("step_start", "Renderizando composición con HyperFrames...")

        env = {**os.environ}
        chrome = _find_chromium()
        if chrome:
            env["PUPPETEER_EXECUTABLE_PATH"] = chrome
        # Needed in Docker / headless Linux
        env.setdefault("PUPPETEER_CHROMIUM_ARGS", "--no-sandbox --disable-dev-shm-usage --disable-gpu")

        render_cmd = [
            "npx", "--yes", "hyperframes", "render",
            "--output", silent_path,
        ]
        if total_duration > 0:
            render_cmd += ["--duration", str(total_duration)]

        await self.emit("progress", "Ejecutando npx hyperframes render (esto puede tardar unos minutos)...")

        proc = await asyncio.create_subprocess_exec(
            *render_cmd,
            cwd=comp_dir,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=900)
        except asyncio.TimeoutError:
            proc.kill()
            raise RuntimeError("HyperFrames render excedió el tiempo límite de 15 minutos")

        if proc.returncode != 0 or not os.path.exists(silent_path):
            stderr = stderr_bytes.decode(errors="replace")[-2000:] if stderr_bytes else "(sin output)"
            raise RuntimeError(f"HyperFrames render falló (exit {proc.returncode}):\n{stderr}")

        await self.emit("progress", "Video renderizado — mezclando audio...")

        # Mix voiceover into the rendered video
        has_audio = full_voiceover_path and os.path.exists(full_voiceover_path)
        if has_audio:
            mix_proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-y",
                "-i", silent_path,
                "-i", full_voiceover_path,
                "-c:v", "copy",
                "-c:a", "aac",
                "-ar", "44100", "-ac", "2",
                "-shortest",
                final_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                _, mix_stderr = await asyncio.wait_for(mix_proc.communicate(), timeout=300)
            except asyncio.TimeoutError:
                mix_proc.kill()
                mix_proc.returncode = -1
                mix_stderr = b""

            if mix_proc.returncode != 0 or not os.path.exists(final_path):
                shutil.copy(silent_path, final_path)
                await self.emit("log", f"Audio mix falló, usando video mudo: {mix_stderr.decode(errors='replace')[-500:]}")
            else:
                os.remove(silent_path)
        else:
            shutil.move(silent_path, final_path)

        await self.emit(
            "step_complete",
            "Video HyperFrames listo",
            data={"final_video_path": final_path},
        )
        return SkillResult(
            status="completed",
            outputs={"final_video_path": final_path},
        )
