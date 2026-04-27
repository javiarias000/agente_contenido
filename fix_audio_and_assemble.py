#!/usr/bin/env python3
"""
Regenera audio con OpenAI TTS + genera SRT desde el guión + ensambla video final.
Sin ElevenLabs, sin Whisper API. Solo OpenAI TTS + ffmpeg.

Uso: python fix_audio_and_assemble.py [RUN_ID]
"""

import asyncio
import glob
import json
import os
import subprocess
import sys
import tempfile

from openai import AsyncOpenAI

OUTPUTS = "./outputs"
W, H, FPS = 1080, 1920, 30
TTS_VOICE = "nova"   # alloy | echo | fable | nova | onyx | shimmer
TTS_MODEL = "tts-1"


# ─── Audio ───────────────────────────────────────────────────────────────────

async def synthesize(client: AsyncOpenAI, text: str, path: str) -> float:
    resp = await client.audio.speech.create(
        model=TTS_MODEL,
        voice=TTS_VOICE,
        input=text[:4096],
        response_format="mp3",
    )
    with open(path, "wb") as f:
        f.write(resp.content)
    return ffprobe_duration(path)


async def regenerate_audio(run_id: str, scenes: list[dict]) -> tuple[list[str], str]:
    from api.config import settings
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    audio_dir = f"{OUTPUTS}/audio"
    os.makedirs(audio_dir, exist_ok=True)

    audio_paths: list[str] = []
    full_text = ""

    for scene in scenes:
        text = scene.get("speaker_text", "").strip()
        idx = scene.get("index", len(audio_paths))
        path = f"{audio_dir}/{run_id}_scene_{idx}.mp3"

        if not text:
            audio_paths.append("")
            continue

        existing = path if os.path.exists(path) else None
        if existing:
            vol = get_max_volume(existing)
            if vol > -80:
                print(f"    Escena {idx}: audio OK existente, omitiendo TTS")
                audio_paths.append(path)
                full_text += f" {text}"
                continue

        print(f"    Escena {idx}: generando TTS ({len(text)} chars)...", end=" ", flush=True)
        dur = await synthesize(client, text, path)
        audio_paths.append(path)
        full_text += f" {text}"
        print(f"✓ ({dur:.1f}s)")

    full_path = f"{audio_dir}/{run_id}_full_voiceover.mp3"
    existing_full = full_path if os.path.exists(full_path) else None
    if existing_full and get_max_volume(existing_full) > -80:
        print(f"    Voiceover completo: OK existente")
    else:
        print(f"    Voiceover completo: generando TTS ({len(full_text)} chars)...", end=" ", flush=True)
        await synthesize(client, full_text.strip(), full_path)
        print("✓")

    return audio_paths, full_path


# ─── Subtítulos desde script (sin API) ───────────────────────────────────────

def generate_srt_from_script(scenes: list[dict], audio_paths: list[str], srt_path: str) -> None:
    """Crea SRT usando el texto del guión y la duración real de cada audio."""
    entries = []
    cursor = 0.0

    for scene in scenes:
        text = scene.get("speaker_text", "").strip()
        idx = scene.get("index", 0)
        if not text:
            cursor += scene.get("duration_seconds", 3.0)
            continue

        path = audio_paths[idx] if idx < len(audio_paths) else ""
        if path and os.path.exists(path):
            duration = ffprobe_duration(path)
        else:
            duration = scene.get("duration_seconds", 3.0)

        # Divide el texto en líneas de máx 60 chars para que se vea bien
        words = text.split()
        lines, line = [], []
        for w in words:
            line.append(w)
            if len(" ".join(line)) > 55:
                lines.append(" ".join(line))
                line = []
        if line:
            lines.append(" ".join(line))

        # Distribuir tiempo entre líneas
        if lines:
            time_per_line = duration / len(lines)
            for i, ln in enumerate(lines):
                start = cursor + i * time_per_line
                end = start + time_per_line - 0.05
                entries.append((start, end, ln))

        cursor += duration

    with open(srt_path, "w", encoding="utf-8") as f:
        for i, (start, end, text) in enumerate(entries, 1):
            f.write(f"{i}\n")
            f.write(f"{_srt_ts(start)} --> {_srt_ts(end)}\n")
            f.write(f"{text}\n\n")

    print(f"    SRT generado: {len(entries)} líneas")


def _srt_ts(s: float) -> str:
    h, rem = divmod(int(s), 3600)
    m, sec = divmod(rem, 60)
    ms = int((s - int(s)) * 1000)
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"


# ─── ffmpeg helpers ───────────────────────────────────────────────────────────

def ffprobe_duration(path: str) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, timeout=10,
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def get_max_volume(path: str) -> float:
    r = subprocess.run(
        ["ffmpeg", "-i", path, "-af", "volumedetect", "-f", "null", "/dev/null"],
        capture_output=True, text=True, timeout=15,
    )
    for line in r.stderr.splitlines():
        if "max_volume" in line:
            try:
                return float(line.split("max_volume:")[1].split("dB")[0].strip())
            except Exception:
                pass
    return -100.0


def build_clip(image: str, duration: float, out: str) -> bool:
    vf = (
        f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
        f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black"
    )
    r = subprocess.run([
        "ffmpeg", "-y", "-loop", "1", "-i", image,
        "-t", f"{duration:.3f}",
        "-vf", vf, "-r", str(FPS), "-pix_fmt", "yuv420p",
        "-c:v", "libx264", "-preset", "fast", "-an", out,
    ], capture_output=True, timeout=120)
    return r.returncode == 0 and os.path.exists(out)


def concat_clips(clip_paths: list[str], out: str) -> bool:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        list_file = f.name
        for p in clip_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")
    r = subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
        "-c:v", "libx264", "-preset", "fast", "-an", out,
    ], capture_output=True, timeout=300)
    os.remove(list_file)
    return r.returncode == 0


def mux_audio(video: str, audio: str, out: str) -> bool:
    r = subprocess.run([
        "ffmpeg", "-y", "-i", video, "-i", audio,
        "-c:v", "copy",
        "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "128k",
        "-shortest", out,
    ], capture_output=True, timeout=300)
    return r.returncode == 0


def burn_subtitles(video: str, srt: str, out: str) -> bool:
    if not os.path.exists(srt) or os.path.getsize(srt) == 0:
        return False
    abs_srt = os.path.abspath(srt).replace("\\", "/")
    style = (
        "FontName=Arial,FontSize=20,Bold=1,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
        "Outline=2,Shadow=1,Alignment=2,MarginV=60"
    )
    r = subprocess.run([
        "ffmpeg", "-y", "-i", video,
        "-vf", f"subtitles='{abs_srt}':force_style='{style}'",
        "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "128k", out,
    ], capture_output=True, timeout=300)
    return r.returncode == 0 and os.path.exists(out)


# ─── Pipeline principal ───────────────────────────────────────────────────────

async def process_run(run_id: str) -> str | None:
    print(f"\n▶ Run: {run_id}")

    # Cargar script
    script_path = f"{OUTPUTS}/scripts/{run_id}_script.json"
    if not os.path.exists(script_path):
        print("  ✗ No se encontró el script JSON")
        return None

    with open(script_path) as f:
        script = json.load(f)

    scenes = script.get("scenes", [])
    images = sorted(glob.glob(f"{OUTPUTS}/images/{run_id}_scene_*.png"))

    if not images:
        print("  ✗ No hay imágenes")
        return None

    print(f"  → {len(images)} imágenes, {len(scenes)} escenas en guión")

    # 1. Regenerar audio (solo si el existente está en silencio)
    print("  [1/4] Verificando/regenerando audio...")
    audio_paths, full_voiceover = await regenerate_audio(run_id, scenes)

    # 2. Construir clips de video por escena
    print("  [2/4] Construyendo clips de video...")
    video_dir = f"{OUTPUTS}/video"
    os.makedirs(video_dir, exist_ok=True)
    tmp_clips = []

    for i, img in enumerate(images):
        path = audio_paths[i] if i < len(audio_paths) else ""
        dur = ffprobe_duration(path) if path and os.path.exists(path) else 3.0
        if dur < 0.1:
            dur = 3.0
        clip_out = f"{video_dir}/{run_id}_clip_{i}.mp4"
        print(f"    Clip {i}: {dur:.1f}s ...", end=" ", flush=True)
        if build_clip(img, dur, clip_out):
            tmp_clips.append(clip_out)
            print("✓")
        else:
            print("✗")

    if not tmp_clips:
        print("  ✗ Sin clips")
        return None

    # 3. Concatenar + audio
    print("  [3/4] Concatenando y agregando audio...")
    concat_out = f"{video_dir}/{run_id}_concat.mp4"
    if not concat_clips(tmp_clips, concat_out):
        print("  ✗ Error concatenando")
        return None

    with_audio = f"{video_dir}/{run_id}_with_audio.mp4"
    if os.path.exists(full_voiceover) and get_max_volume(full_voiceover) > -80:
        if not mux_audio(concat_out, full_voiceover, with_audio):
            with_audio = concat_out
    else:
        with_audio = concat_out

    # 4. Subtítulos desde script JSON
    print("  [4/4] Generando subtítulos y video final...")
    srt_path = f"{video_dir}/{run_id}.srt"
    generate_srt_from_script(scenes, audio_paths, srt_path)

    final_out = f"{video_dir}/{run_id}_final.mp4"
    if not burn_subtitles(with_audio, srt_path, final_out):
        print("    ⚠ Subtítulos fallaron, copiando sin ellos")
        import shutil
        shutil.copy(with_audio, final_out)

    # Limpiar temporales
    for p in tmp_clips + [concat_out, with_audio]:
        if p != final_out:
            try:
                os.remove(p)
            except Exception:
                pass

    size_mb = os.path.getsize(final_out) / 1024 / 1024
    dur_total = ffprobe_duration(final_out)
    print(f"\n  ✅ Video final: {final_out}  ({size_mb:.1f} MB, {dur_total:.1f}s)")
    return final_out


async def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    if len(sys.argv) > 1:
        run_ids = sys.argv[1:]
    else:
        # Auto-detectar runs con script + imágenes
        run_ids = []
        for p in sorted(glob.glob(f"{OUTPUTS}/scripts/*_script.json")):
            run_id = os.path.basename(p).replace("_script.json", "")
            images = glob.glob(f"{OUTPUTS}/images/{run_id}_scene_*.png")
            if images:
                run_ids.append(run_id)

    if not run_ids:
        print("✗ No se encontraron runs con script + imágenes")
        sys.exit(1)

    print(f"Runs a procesar: {len(run_ids)}")
    results = []
    for run_id in run_ids:
        path = await process_run(run_id)
        if path:
            results.append(path)

    print(f"\n{'='*60}")
    print(f"Videos generados: {len(results)}/{len(run_ids)}")
    for p in results:
        print(f"  → {p}")


if __name__ == "__main__":
    asyncio.run(main())
