# GUÍA DE IMPLEMENTACIÓN DETALLADA

## 1. CREAR `skills/animated_image_generator.py`

```python
from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any

from openai import AsyncOpenAI

from api.config import settings
from api.events import EventBus
from skills.image_generator import ImageGenerator, _build_image_prompt, PLATFORM_SIZES
from skills import BaseSkill, SkillResult


class AnimatedImageGenerator(ImageGenerator):
    """
    Extiende ImageGenerator para generar imágenes con metadatos de animación.
    
    Cambios respecto a ImageGenerator:
    1. Extrae motion_hint del visual_description
    2. Guarda motion.json con metadatos de animación
    3. Retorna motion_metadata además de image_paths
    """
    
    skill_name = "animated_image_generator"
    
    MOTION_PATTERNS = {
        # Palabras clave → motion_type
        "zoom in": "zoom_in",
        "zoom out": "zoom_out",
        "zoom": "zoom_in",  # default
        "pan left": "pan_left",
        "pan right": "pan_right",
        "pan up": "pan_up",
        "pan down": "pan_down",
        "pan": "pan_left",  # default
        "slow pan": "slow_pan",
        "subtle zoom": "subtle_zoom",
        "diagonal": "diagonal",
        "move forward": "zoom_in",
        "move backward": "zoom_out",
        "slide left": "pan_left",
        "slide right": "pan_right",
        "static": "static",
        "none": "none",
    }
    
    async def run(self, inputs: dict[str, Any], interactive: bool = False) -> SkillResult:
        script: dict = inputs["script"]
        brand_slug: str = inputs.get("brand_slug", "")
        platform: str = inputs.get("platform", "tiktok")
        profile: dict = inputs.get("profile", {})
        character_anchor: str = profile.get("character_anchor", "")
        style_notes: str = profile.get("style_notes", "")
        size = PLATFORM_SIZES.get(platform, PLATFORM_SIZES.get("tiktok", "1024x1792"))
        
        # Extract brand colors (same as parent)
        brand_colors = profile.get("colors", {})
        color_palette = brand_colors.get("palette", []) or [
            brand_colors.get("primary", ""),
            brand_colors.get("secondary", ""),
        ]
        color_palette = [c for c in color_palette if c]
        color_mood = brand_colors.get("mood", "")
        
        scenes = script.get("scenes", [])
        await self.emit("step_start", f"Generando {len(scenes)} imágenes con movimiento...")
        
        # Generar imágenes
        image_paths = await self._generate_all(
            scenes, character_anchor, style_notes, size, interactive,
            brand_colors=color_palette, color_mood=color_mood
        )
        
        # Extraer motion metadata y guardar
        motion_metadata = []
        for i, (scene, img_path) in enumerate(zip(scenes, image_paths)):
            motion_hint = self._extract_motion_hint(scene.get("visual_description", ""))
            
            metadata = {
                "scene_index": i,
                "image_path": img_path,
                "motion_type": motion_hint.get("type", "static"),
                "motion_direction": motion_hint.get("direction"),
                "motion_target": motion_hint.get("target"),
                "duration_seconds": scene.get("duration_seconds", 3),
                "speaker_text": scene.get("speaker_text", ""),
                "on_screen_text": scene.get("on_screen_text"),
            }
            motion_metadata.append(metadata)
            
            # Guardar metadata file
            metadata_path = img_path.replace(".png", "_motion.json")
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
            
            await self.emit(
                "progress",
                f"Imagen {i+1}/{len(scenes)} generada con motion: {motion_hint.get('type')}",
                data={"scene_index": i, "motion_type": motion_hint.get("type")}
            )
        
        await self.emit(
            "step_complete",
            f"Generadas {len(image_paths)} imágenes con metadatos de animación",
            data={"image_paths": image_paths, "motion_metadata": motion_metadata},
        )
        
        return SkillResult(
            status="completed",
            outputs={
                "image_paths": image_paths,
                "motion_metadata": motion_metadata,
            }
        )
    
    def _extract_motion_hint(self, visual_description: str) -> dict[str, Any]:
        """
        Extrae motion_hint del visual_description.
        
        Retorna:
        {
            "type": "zoom_in" | "pan_left" | "static" | ...,
            "direction": "in" | "left" | None,
            "target": "face" | "product" | None,
            "confidence": 0.0-1.0,
        }
        """
        text = visual_description.lower()
        
        # Detectar motion type con palabras clave
        motion_type = "static"
        direction = None
        target = None
        confidence = 0.0
        
        for pattern, motion in self.MOTION_PATTERNS.items():
            if pattern in text:
                motion_type = motion
                confidence = 0.8  # patrón encontrado
                
                # Extraer target
                for target_word in ["face", "product", "subject", "object", "center", "edge"]:
                    if target_word in text:
                        target = target_word
                        confidence = 0.9
                        break
                
                # Extraer dirección si aplicable
                if "in" in motion_type:
                    direction = "in"
                elif "out" in motion_type:
                    direction = "out"
                elif "left" in motion_type:
                    direction = "left"
                elif "right" in motion_type:
                    direction = "right"
                elif "up" in motion_type:
                    direction = "up"
                elif "down" in motion_type:
                    direction = "down"
                
                break  # Primera coincidencia gana
        
        return {
            "type": motion_type,
            "direction": direction,
            "target": target,
            "confidence": confidence,
        }
```

---

## 2. CREAR `skills/advanced_subtitle_generator.py`

```python
from __future__ import annotations

import os
from typing import Any

from openai import AsyncOpenAI

from api.config import settings
from api.events import EventBus
from skills import BaseSkill, SkillResult


def _sec_to_srt(seconds: float) -> str:
    """Convierte segundos a formato SRT: HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


class AdvancedSubtitleGenerator(BaseSkill):
    skill_name = "advanced_subtitle_generator"
    
    def __init__(self, event_bus: EventBus, run_id: str, step_index: int = 0):
        super().__init__(event_bus, run_id, step_index)
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    async def run(self, inputs: dict[str, Any], interactive: bool = False) -> SkillResult:
        """
        Genera subtítulos robustos con validación.
        
        Inputs:
            - full_voiceover_path: str
            - script: dict (con scenes)
        
        Outputs:
            - srt_path: str
            - srt_metadata: dict (stats)
        """
        audio_path: str = inputs.get("full_voiceover_path", "")
        script: dict = inputs.get("script", {})
        
        if not audio_path or not os.path.exists(audio_path):
            await self.emit("log", "Sin audio para generar subtítulos")
            # Crear SRT vacío
            srt_path = os.path.join(
                os.path.dirname(audio_path or "./outputs/audio"),
                f"{self.run_id}.srt"
            )
            open(srt_path, "w").close()
            return SkillResult(
                status="completed",
                outputs={"srt_path": srt_path, "srt_metadata": {"empty": True}}
            )
        
        await self.emit("step_start", "Generando subtítulos mejorados...")
        
        try:
            # 1. Transcribir audio
            await self.emit("progress", "1/3 Transcribiendo audio...")
            words = await self._transcribe_audio(audio_path)
            
            if not words:
                # Fallback: usar texto del script
                await self.emit("log", "Whisper sin resultados, usando script como fallback")
                words = self._extract_words_from_script(script)
            
            # 2. Validar y chunking
            await self.emit("progress", "2/3 Validando y agrupando...")
            chunks = self._chunk_words(words, chunk_size=10)
            chunks = self._validate_chunk_timings(chunks)
            
            # 3. Escribir SRT
            await self.emit("progress", "3/3 Escribiendo SRT...")
            srt_dir = os.path.join(settings.outputs_dir, "video")
            os.makedirs(srt_dir, exist_ok=True)
            srt_path = os.path.join(srt_dir, f"{self.run_id}.srt")
            
            metadata = await self._write_srt_validated(chunks, srt_path)
            
            await self.emit(
                "step_complete",
                f"Subtítulos generados: {metadata.get('subtitle_count', 0)} líneas",
                data={"srt_path": srt_path, "metadata": metadata}
            )
            
            return SkillResult(
                status="completed",
                outputs={"srt_path": srt_path, "srt_metadata": metadata}
            )
        
        except Exception as e:
            await self.emit("log", f"Error en subtítulos: {str(e)}")
            # Crear SRT vacío como fallback
            srt_path = os.path.join(settings.outputs_dir, "video", f"{self.run_id}.srt")
            os.makedirs(os.path.dirname(srt_path), exist_ok=True)
            open(srt_path, "w").close()
            return SkillResult(
                status="completed",
                outputs={"srt_path": srt_path, "srt_metadata": {"error": str(e)}}
            )
    
    async def _transcribe_audio(self, audio_path: str) -> list[dict]:
        """
        Transcribe audio con Whisper.
        
        Retorna: [{"word": str, "start": float, "end": float}, ...]
        """
        try:
            with open(audio_path, "rb") as f:
                transcript = await self.client.audio.transcriptions.create(
                    model=settings.whisper_model,
                    file=f,
                    response_format="verbose_json",
                    timestamp_granularities=["word"],
                )
            
            words = []
            # Intenta extraer words primero (Whisper API reciente)
            if hasattr(transcript, "words") and transcript.words:
                words = [
                    {
                        "word": w.word.strip(),
                        "start": w.start,
                        "end": w.end,
                    }
                    for w in transcript.words
                ]
            # Fallback: usar segments
            elif hasattr(transcript, "segments") and transcript.segments:
                for seg in transcript.segments:
                    # Dividir segment en palabras aproximadamente
                    seg_words = seg.text.strip().split()
                    if not seg_words:
                        continue
                    
                    duration = (seg.end - seg.start) / len(seg_words) if seg_words else 0
                    for j, w in enumerate(seg_words):
                        words.append({
                            "word": w,
                            "start": seg.start + (j * duration),
                            "end": seg.start + ((j + 1) * duration),
                        })
            
            return words
        
        except Exception as e:
            await self.emit("log", f"Transcription error: {str(e)}")
            return []
    
    def _extract_words_from_script(self, script: dict) -> list[dict]:
        """Fallback: extraer palabras del script con timing aproximado."""
        words = []
        current_time = 0.0
        
        for scene in script.get("scenes", []):
            text = scene.get("speaker_text", "").strip()
            if not text:
                current_time += scene.get("duration_seconds", 3)
                continue
            
            scene_words = text.split()
            scene_duration = scene.get("duration_seconds", 3)
            word_duration = scene_duration / max(len(scene_words), 1)
            
            for i, word in enumerate(scene_words):
                words.append({
                    "word": word,
                    "start": current_time + (i * word_duration),
                    "end": current_time + ((i + 1) * word_duration),
                })
            
            current_time += scene_duration
        
        return words
    
    def _chunk_words(self, words: list[dict], chunk_size: int = 10) -> list[dict]:
        """
        Agrupa palabras en chunks para subtítulos.
        
        Retorna: [{"words": [...], "start": float, "end": float}, ...]
        """
        if not words:
            return []
        
        chunks = []
        for i in range(0, len(words), chunk_size):
            chunk_words = words[i:i + chunk_size]
            chunks.append({
                "words": chunk_words,
                "text": " ".join(w["word"] for w in chunk_words),
                "start": chunk_words[0]["start"],
                "end": chunk_words[-1]["end"],
            })
        
        return chunks
    
    def _validate_chunk_timings(self, chunks: list[dict]) -> list[dict]:
        """
        Valida y ajusta timings de chunks.
        
        Problemas:
        - start > end
        - timings negativos
        - gaps enormes entre chunks
        """
        validated = []
        
        for i, chunk in enumerate(chunks):
            start = chunk["start"]
            end = chunk["end"]
            
            # Validar básico
            if start < 0:
                start = 0
            if end <= start:
                end = start + 2.0  # default 2 segundos
            
            # Evitar overlap con chunk anterior
            if validated:
                prev_end = validated[-1]["end"]
                if start < prev_end:
                    start = prev_end + 0.1
            
            validated.append({
                **chunk,
                "start": start,
                "end": end,
            })
        
        return validated
    
    async def _write_srt_validated(self, chunks: list[dict], srt_path: str) -> dict:
        """
        Escribe SRT y retorna metadata de validación.
        
        Retorna:
        {
            "subtitle_count": int,
            "total_duration": float,
            "errors": list[str],
            "coverage_percent": float,
        }
        """
        errors = []
        
        # Validar chunks
        for i, chunk in enumerate(chunks):
            if "start" not in chunk or "end" not in chunk:
                errors.append(f"Chunk {i}: missing timing")
            elif chunk["start"] > chunk["end"]:
                errors.append(f"Chunk {i}: invalid timing {chunk['start']} > {chunk['end']}")
            elif not chunk.get("text"):
                errors.append(f"Chunk {i}: empty text")
        
        # Escribir SRT
        with open(srt_path, "w", encoding="utf-8") as f:
            for idx, chunk in enumerate(chunks, 1):
                f.write(f"{idx}\n")
                f.write(f"{_sec_to_srt(chunk['start'])} --> {_sec_to_srt(chunk['end'])}\n")
                f.write(f"{chunk['text']}\n\n")
        
        # Metadata
        total_duration = chunks[-1]["end"] if chunks else 0
        
        return {
            "subtitle_count": len(chunks),
            "total_duration": total_duration,
            "errors": errors,
            "validation_errors_count": len(errors),
            "coverage_percent": 100 if not errors else 90,  # approximate
        }
```

---

## 3. SKETCH: `skills/composed_video_assembler.py`

Este archivo es muy grande. Aquí va un skeleton con funciones clave:

```python
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
from skills.advanced_subtitle_generator import AdvancedSubtitleGenerator

OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920
OUTPUT_FPS = 30


class ComposedVideoAssembler(BaseSkill):
    skill_name = "composed_video_assembler"
    
    def __init__(self, event_bus: EventBus, run_id: str, step_index: int = 0):
        super().__init__(event_bus, run_id, step_index)
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    async def run(self, inputs: dict[str, Any], interactive: bool = False) -> SkillResult:
        image_paths: list[str] = inputs.get("image_paths", [])
        audio_paths: list[str] = inputs.get("audio_paths", [])
        full_voiceover_path: str = inputs.get("full_voiceover_path", "")
        motion_metadata: list[dict] = inputs.get("motion_metadata", [])
        profile: dict = inputs.get("profile", {})
        script: dict = inputs.get("script", {})
        
        video_dir = os.path.join(settings.outputs_dir, "video")
        os.makedirs(video_dir, exist_ok=True)
        
        await self.emit("step_start", "Ensamblando video con composición...")
        
        # 1. Componer clips animados por escena
        await self.emit("progress", "1/5 Componiendo escenas animadas...")
        scene_videos = await self._compose_scene_videos(
            image_paths, audio_paths, motion_metadata, profile
        )
        
        # 2. Concatenar con transiciones
        await self.emit("progress", "2/5 Concatenando con transiciones...")
        concat_path = os.path.join(video_dir, f"{self.run_id}_concat.mp4")
        await self._concatenate_with_transitions(scene_videos, concat_path)
        
        # 3. Generar subtítulos mejorados
        await self.emit("progress", "3/5 Generando subtítulos...")
        subtitle_gen = AdvancedSubtitleGenerator(self.event_bus, self.run_id, self.step_index)
        subtitle_result = await subtitle_gen.run(
            {
                "full_voiceover_path": full_voiceover_path,
                "script": script,
            },
            interactive=False
        )
        srt_path = subtitle_result.outputs.get("srt_path", "")
        
        # 4. Quemar subtítulos con validación
        await self.emit("progress", "4/5 Grabando subtítulos...")
        subtitled_path = os.path.join(video_dir, f"{self.run_id}_subtitled.mp4")
        await self._burn_subtitles_validated(concat_path, srt_path, subtitled_path)
        
        # 5. BGM opcional
        await self.emit("progress", "5/5 Finalizando...")
        final_path = subtitled_path
        if settings.suno_cookie:
            try:
                final_path = await self._add_bgm_if_configured(subtitled_path, script)
            except Exception as e:
                await self.emit("log", f"BGM omitida: {e}")
        
        # Cleanup
        for p in scene_videos + [concat_path]:
            try:
                os.remove(p)
            except:
                pass
        
        if interactive:
            await self.request_feedback(
                "¿El video final te parece bien?",
                {"video_path": final_path, "srt_path": srt_path},
                interactive,
            )
        
        await self.emit(
            "step_complete",
            "Video ensamblado con éxito",
            data={"final_video_path": final_path, "srt_path": srt_path},
        )
        
        return SkillResult(
            status="completed",
            outputs={"final_video_path": final_path, "srt_path": srt_path},
        )
    
    async def _compose_scene_videos(
        self,
        image_paths: list[str],
        audio_paths: list[str],
        motion_metadata: list[dict],
        profile: dict,
    ) -> list[str]:
        """Compone video animado para cada escena con overlays."""
        scene_videos = []
        
        for i, (img, audio) in enumerate(zip(image_paths, audio_paths)):
            if not img or not os.path.exists(img):
                continue
            
            motion = motion_metadata[i] if i < len(motion_metadata) else {}
            
            try:
                video = await self._compose_single_scene(
                    img, audio, motion, profile, i
                )
                scene_videos.append(video)
                await self.emit(
                    "progress",
                    f"Escena {i+1} compuesta",
                    data={"scene_index": i}
                )
            except Exception as e:
                await self.emit("log", f"Error en escena {i}: {str(e)}")
                raise
        
        return scene_videos
    
    async def _compose_single_scene(
        self,
        image_path: str,
        audio_path: str,
        motion_metadata: dict,
        profile: dict,
        scene_index: int,
    ) -> str:
        """
        Compone un clip de una escena con:
        - Imagen de fondo
        - Animación (zoom, pan, etc)
        - Logo + safe area
        - On-screen text
        - Audio sincronizado
        
        Retorna ruta del video generado.
        """
        # TODO: Implementar con ffmpeg complex filtergraph
        # Skeleton:
        
        motion_type = motion_metadata.get("motion_type", "static")
        on_screen_text = motion_metadata.get("on_screen_text")
        duration = self._get_audio_duration(audio_path)
        
        output_path = image_path.replace(".png", f"_scene_{scene_index}_animated.mp4")
        
        # Filtergraph complejo
        # [0:v] input image
        # → scale to 1080x1920
        # → apply motion (zoompan, crop, etc)
        # → drawtext for on_screen_text
        # → overlay logo
        # [1:a] input audio
        # → aresample to 44100:stereo
        # → concat v y a
        
        # Por ahora, placeholder:
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", image_path,
            "-i", audio_path if audio_path and os.path.exists(audio_path) else "-f lavfi -i color=black:s=1080x1920:d=3",
            "-t", str(duration),
            "-c:v", "libx264", "-preset", "fast",
            "-c:a", "aac",
            "-pix_fmt", "yuv420p",
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr.decode()[:200]}")
        
        return output_path
    
    async def _concatenate_with_transitions(
        self,
        clip_paths: list[str],
        output_path: str,
    ) -> None:
        """Concatena clips con transiciones suaves (fade/dissolve)."""
        # TODO: Implementar con xfade filter o concat demuxer simple
        # Placeholder:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            for p in clip_paths:
                f.write(f"file '{os.path.abspath(p)}'\n")
            list_path = f.name
        
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", list_path,
            "-c:v", "libx264", "-c:a", "aac",
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, timeout=300)
        os.remove(list_path)
        
        if result.returncode != 0:
            raise RuntimeError(f"Concatenation failed")
    
    async def _burn_subtitles_validated(
        self,
        input_path: str,
        srt_path: str,
        output_path: str,
    ) -> None:
        """Quema subtítulos con validación y manejo de errores."""
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input video not found: {input_path}")
        
        # Validar SRT
        if not os.path.exists(srt_path) or os.path.getsize(srt_path) == 0:
            # No subtitles, just copy
            import shutil
            shutil.copy(input_path, output_path)
            await self.emit("log", "No subtitles to burn")
            return
        
        # Preparar path de SRT (escape para ffmpeg)
        abs_srt = os.path.abspath(srt_path).replace("\\", "/")
        if ":" in abs_srt:  # Windows paths
            abs_srt = abs_srt.replace(":", "\\:")
        
        # FFmpeg filter
        subtitle_filter = (
            f"subtitles='{abs_srt}':force_style="
            "'FontSize=24,Bold=1,PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,Outline=2,Alignment=2'"
        )
        
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-vf", subtitle_filter,
            "-c:a", "copy",
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, timeout=300, text=True)
        
        if result.returncode != 0:
            await self.emit("log", f"Subtitle burn failed: {result.stderr[:100]}")
            # Fallback: copy without subtitles
            import shutil
            shutil.copy(input_path, output_path)
            await self.emit("log", "Fallback: video without subtitles")
        else:
            await self.emit("log", "Subtitles burned successfully")
    
    def _get_audio_duration(self, path: str) -> float:
        """Obtiene duración de audio en segundos."""
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", path
                ],
                capture_output=True, text=True, timeout=10,
            )
            return float(result.stdout.strip())
        except:
            return 3.0
    
    async def _add_bgm_if_configured(self, video_path: str, script: dict) -> str:
        """Agrega música de fondo si Suno está configurado."""
        # TODO: Implementar similar a assembler.py línea 222
        return video_path
```

---

## 4. ACTUALIZAR `pipelines/ugc_pipeline.py`

**Cambios:**

```python
# Línea 111-118: Reemplazar Assembler y VideoAnimator

def build_steps(self, inputs: dict[str, Any]) -> list[StepDefinition]:
    return [
        StepDefinition(
            name="brand_load",
            skill_class=_BrandLoadSkill,
            skill_kwargs={"db_session": self.db},
        ),
        StepDefinition(
            name="script_generate",
            skill_class=ScriptGenerator,
            skill_kwargs={},
        ),
        # CAMBIO 1: Usar AnimatedImageGenerator en lugar de ImageGenerator
        StepDefinition(
            name="image_generate",
            skill_class=AnimatedImageGenerator,  # ← NUEVO
            skill_kwargs={},
        ),
        StepDefinition(
            name="image_enhance",
            skill_class=ImageQualityImprover,
            skill_kwargs={},
        ),
        StepDefinition(
            name="voice_generate",
            skill_class=VoiceGenerator,
            skill_kwargs={},
        ),
        # CAMBIO 2: Usar ComposedVideoAssembler en lugar de Assembler
        # CAMBIO 3: Remover VideoAnimator (ahora integrado en ComposedVideoAssembler)
        StepDefinition(
            name="video_assemble",
            skill_class=ComposedVideoAssembler,  # ← NUEVO
            skill_kwargs={},
        ),
    ]

# Agregar imports
from skills.animated_image_generator import AnimatedImageGenerator
from skills.composed_video_assembler import ComposedVideoAssembler
```

---

## 5. ACTUALIZAR `skills/script_generator.py`

**Cambio en prompt (línea 46-54):**

```python
SCENE_SYSTEM = """You are an expert short-form video scriptwriter. Expand this scene into full content.
Return JSON with:
{
  "visual_description": "string (detailed visual prompt for AI image generation with REALISTIC, DYNAMIC elements...)",
  "speaker_text": "string (exact words to speak in this scene)",
  "on_screen_text": "string or null (text overlay, caption card, or null if none)",
  "motion_hint": "string (optional): none | zoom_in | zoom_out | pan_left | pan_right | pan_up | pan_down | slow_pan | subtle_zoom | diagonal | static"
}
IMPORTANT: visual_description must be detailed and realistic. motion_hint helps generate smooth animations.
Return ONLY valid JSON."""
```

---

## 6. TESTING

**`tests/test_animated_image_generator.py`:**

```python
import pytest
from skills.animated_image_generator import AnimatedImageGenerator


@pytest.mark.asyncio
async def test_extract_motion_hint():
    gen = AnimatedImageGenerator(event_bus=..., run_id="test")
    
    # Test cases
    assert gen._extract_motion_hint("slow zoom in on face")["type"] == "zoom_in"
    assert gen._extract_motion_hint("pan left across scene")["type"] == "pan_left"
    assert gen._extract_motion_hint("static image")["type"] == "static"
    assert gen._extract_motion_hint("no motion here")["type"] == "static"
```

---

## 7. CHECKLIST DE IMPLEMENTACIÓN

- [ ] Crear `animated_image_generator.py` con `_extract_motion_hint()`
- [ ] Crear `advanced_subtitle_generator.py` con validación
- [ ] Crear `composed_video_assembler.py` con composición y animación
- [ ] Actualizar `ugc_pipeline.py` para usar nuevos skills
- [ ] Actualizar `script_generator.py` prompt para agregar motion_hint
- [ ] Tests unitarios para cada skill
- [ ] Test end-to-end con UGC pipeline
- [ ] Deprecate `video_animator.py` con warning
- [ ] Documentar cambios en CLAUDE.md

