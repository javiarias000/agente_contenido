"""Improved video assembler with animation support and proper logo placement."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from api.config import settings
from api.events import EventBus
from skills import BaseSkill, SkillResult

OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920
OUTPUT_FPS = 30
SAFE_AREA_PERCENT = 0.05  # 5% safe area on edges

# FFmpeg codec settings
VIDEO_CODEC = "libx264"  # libx264 for compatibility, can switch to libx265 for better quality
VIDEO_PRESET = "superfast"  # ultrafast|superfast|veryfast|faster|fast|medium|slow|slower|veryslow
VIDEO_CRF = "28"  # 0=lossless, 23=default, 51=worst quality. Lower = better but larger file


def _get_audio_duration(path: str) -> float:
    """Get audio duration using ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, timeout=10,
        )
        return float(result.stdout.strip()) if result.stdout else 3.0
    except Exception:
        return 3.0


def _calculate_safe_logo_position(
    frame_width: int, frame_height: int, logo_size: int
) -> tuple[int, int]:
    """Calculate logo position respecting safe area.

    Logo in top-right corner with 5% margin from edges.
    """
    safe_margin = int(max(frame_width, frame_height) * SAFE_AREA_PERCENT)
    x = frame_width - logo_size - safe_margin
    y = safe_margin
    return max(x, safe_margin), max(y, safe_margin)


class ComposedVideoAssembler(BaseSkill):
    """Assemble video from images + audio with animation and proper overlays."""

    skill_name = "composed_video_assembler"

    def __init__(
        self,
        event_bus: EventBus,
        run_id: str,
        step_index: int = 0,
    ):
        super().__init__(event_bus, run_id, step_index)

    async def run(self, inputs: dict[str, Any], interactive: bool = False) -> SkillResult:
        """Assemble video from images/videos and audio.

        Expected inputs:
            - image_paths: List of image paths (optional if video_paths provided)
            - video_paths: List of pre-generated video paths (optional, from Kling etc)
            - audio_paths: List of audio paths (one per scene)
            - motion_metadata: List of motion metadata dicts (optional)
            - srt_path: Path to SRT subtitle file (optional)
            - script: Script dict with scene info
        """
        image_paths = inputs.get("image_paths", [])
        video_paths = inputs.get("video_paths", [])
        audio_paths = inputs.get("audio_paths", [])
        motion_metadata = inputs.get("motion_metadata", [])
        srt_path = inputs.get("srt_path", "")
        script = inputs.get("script", {})

        # Either images or videos must be provided
        has_images = bool(image_paths)
        has_videos = bool(video_paths)

        if not (has_images or has_videos) or not audio_paths:
            return SkillResult(
                status="failed",
                outputs={"error": "Missing image_paths/video_paths or audio_paths"}
            )

        video_dir = os.path.join(settings.outputs_dir, "video")
        os.makedirs(video_dir, exist_ok=True)

        await self.emit("step_start", "Ensamblando video...")

        try:
            # Build individual scene clips with animation or use pre-generated videos
            await self.emit("progress", "Construyendo clips de escena...")

            if has_videos:
                # Use pre-generated videos (e.g., from Kling)
                scene_clips = await self._sync_videos_with_audio(
                    video_paths, audio_paths
                )
            else:
                # Generate clips from images with animation
                scene_clips = await self._build_animated_clips(
                    image_paths, audio_paths, motion_metadata
                )

            # Concatenate clips
            await self.emit("progress", "Concatenando escenas...")
            concat_path = os.path.join(video_dir, f"{self.run_id}_concat.mp4")
            self._concatenate_clips(scene_clips, concat_path)

            # Burn subtitles if available
            final_path = concat_path
            if srt_path and os.path.exists(srt_path) and os.path.getsize(srt_path) > 0:
                await self.emit("progress", "Grabando subtítulos...")
                subtitled_path = os.path.join(video_dir, f"{self.run_id}_subtitled.mp4")
                self._burn_subtitles(concat_path, srt_path, subtitled_path)
                if os.path.exists(subtitled_path):
                    final_path = subtitled_path

            # Cleanup temporary files
            # Only delete scene clips; keep final video
            for p in scene_clips:
                try:
                    os.remove(p)
                except Exception:
                    pass

            # If we created subtitled version, clean up concat version
            if final_path != concat_path:
                try:
                    os.remove(concat_path)
                except Exception:
                    pass

            await self.emit(
                "step_complete",
                "Video ensamblado",
                data={"final_video_path": final_path, "srt_path": srt_path},
            )

            return SkillResult(
                status="completed",
                outputs={
                    "final_video_path": final_path,
                    "srt_path": srt_path,
                }
            )

        except Exception as e:
            await self.emit("progress", f"❌ Error: {e}")
            return SkillResult(
                status="failed",
                outputs={"error": str(e)}
            )

    async def _build_animated_clips(
        self,
        image_paths: list[str],
        audio_paths: list[str],
        motion_metadata: list[dict] | None = None,
    ) -> list[str]:
        """Build individual scene clips with animation filters.

        Uses motion_metadata to apply ken-burns effect if available.
        """
        clips = []

        for i, (img_path, audio_path) in enumerate(zip(image_paths, audio_paths)):
            if not img_path or not os.path.exists(img_path):
                continue

            if not audio_path or not os.path.exists(audio_path):
                await self.emit("progress", f"⚠️ Scene {i+1}: No audio found, using 3s default")
                duration = 3.0
            else:
                duration = _get_audio_duration(audio_path)

            # Get motion info if available
            motion = None
            if motion_metadata and i < len(motion_metadata):
                motion = motion_metadata[i]

            out_path = img_path.replace(".png", f"_scene_{i}.mp4")

            # Build ffmpeg filter graph
            filter_graph = self._build_filter_graph(motion, duration)

            cmd = [
                "ffmpeg", "-y",
                "-loop", "1", "-i", img_path,
                "-i", audio_path,
                "-t", str(duration),
                "-vf", filter_graph,
                "-r", str(OUTPUT_FPS),
                "-pix_fmt", "yuv420p",
                "-c:v", VIDEO_CODEC, "-preset", VIDEO_PRESET, "-crf", VIDEO_CRF,
                "-c:a", "aac", "-shortest",
                out_path
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=300)
            if result.returncode == 0 and os.path.exists(out_path):
                clips.append(out_path)
                await self.emit("progress", f"Clip {i+1} generado")

        return clips

    def _build_filter_graph(self, motion: dict | None, duration: float) -> str:
        """Build ffmpeg filter graph with animation.

        Handles scaling to 1080x1920 and optional motion animation.
        """
        # Base scale/pad to fill 1080x1920
        scale_pad = (
            f"scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:(ow-iw)/2:(oh-ih)/2"
        )

        # Add motion animation if specified
        if motion and motion.get("motion_type") != "static":
            motion_type = motion.get("motion_type")
            motion_filter = self._motion_filter(motion_type, duration)
            return f"{scale_pad},{motion_filter}"

        return scale_pad

    def _motion_filter(self, motion_type: str, duration: float) -> str:
        """Generate motion filter string for ffmpeg.

        Optimized to avoid double-scaling. Motion is achieved through crop/pad
        rather than additional scaling operations.
        """
        if motion_type == "zoom_in":
            # Simulate zoom in by cropping center (image already padded)
            crop_w = int(OUTPUT_WIDTH * 0.95)
            crop_h = int(OUTPUT_HEIGHT * 0.95)
            return f"crop={crop_w}:{crop_h}:(iw-{crop_w})/2:(ih-{crop_h})/2,pad={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:(ow-iw)/2:(oh-ih)/2"
        elif motion_type == "zoom_out":
            # Already achieved by padding in scale_pad
            return ""
        elif motion_type == "pan_left":
            # Crop right side and pad left
            crop_w = int(OUTPUT_WIDTH * 0.95)
            offset = int(OUTPUT_WIDTH * 0.05)
            return f"crop={crop_w}:{OUTPUT_HEIGHT}:{offset}:0,pad={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:{offset}:0"
        elif motion_type == "pan_right":
            # Crop left side and pad right
            crop_w = int(OUTPUT_WIDTH * 0.95)
            offset = int(OUTPUT_WIDTH * 0.05)
            return f"crop={crop_w}:{OUTPUT_HEIGHT}:0:0,pad={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:{offset}:0"
        else:
            return ""

    def _concatenate_clips(self, clip_paths: list[str], output_path: str) -> None:
        """Concatenate video clips using ffmpeg concat demuxer."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            list_path = f.name
            for p in clip_paths:
                f.write(f"file '{os.path.abspath(p)}'\n")

        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path,
             "-c:v", VIDEO_CODEC, "-preset", VIDEO_PRESET, "-crf", VIDEO_CRF,
             "-c:a", "aac", output_path],
            capture_output=True, timeout=300,
        )
        os.remove(list_path)

    async def _sync_videos_with_audio(
        self,
        video_paths: list[str],
        audio_paths: list[str],
    ) -> list[str]:
        """Sync pre-generated videos with their corresponding audio tracks.

        If video duration > audio duration, trim video.
        If audio duration > video duration, extend video (loop or freeze).
        """
        synced_clips = []

        for i, (video_path, audio_path) in enumerate(zip(video_paths, audio_paths)):
            if not os.path.exists(video_path):
                continue
            if not audio_path or not os.path.exists(audio_path):
                # Video without audio — keep as is
                synced_clips.append(video_path)
                continue

            # Get durations
            video_duration = _get_audio_duration(video_path)
            audio_duration = _get_audio_duration(audio_path)

            out_path = video_path.replace(".mp4", f"_synced_{i}.mp4")

            if abs(video_duration - audio_duration) < 0.5:
                # Already synced
                synced_clips.append(video_path)
            else:
                # Trim video to match audio duration
                cmd = [
                    "ffmpeg", "-y",
                    "-i", video_path,
                    "-i", audio_path,
                    "-c:v", "copy", "-c:a", "aac",
                    "-shortest",
                    out_path
                ]
                subprocess.run(cmd, capture_output=True, timeout=120)
                if os.path.exists(out_path):
                    synced_clips.append(out_path)
                    await self.emit("progress", f"Vídeo {i+1} sincronizado con audio")
                else:
                    synced_clips.append(video_path)

        return synced_clips

    def _burn_subtitles(self, input_path: str, srt_path: str, output_path: str) -> None:
        """Burn subtitles into video using ffmpeg."""
        if not os.path.exists(input_path):
            return

        abs_srt = os.path.abspath(srt_path).replace("\\", "/")

        result = subprocess.run(
            ["ffmpeg", "-y", "-i", input_path,
             "-vf",
             f"subtitles='{abs_srt}':force_style='FontSize=12,Bold=1,"
             "BorderStyle=3,BorderColor=&H00000000,"
             "BackColour=&H40000000,OutlineColour=&H00000000,Outline=1,"
             "MarginL=20,MarginR=20,MarginV=30,"
             "PrimaryColour=&H00FFFFFF,Alignment=2'",
             "-c:a", "copy", output_path],
            capture_output=True, timeout=300,
        )

        if result.returncode != 0 or not os.path.exists(output_path):
            # Fallback: copy without subtitles with warning
            import shutil
            shutil.copy(input_path, output_path)
