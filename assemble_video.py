#!/usr/bin/env python3
"""
Ensamblador de video sin API — solo ffmpeg.
Uso: python assemble_video.py [RUN_ID]
Si no se pasa RUN_ID, busca el run con más assets completos.
"""

import glob
import os
import subprocess
import sys
import tempfile

OUTPUTS = "./outputs"
W, H, FPS = 1080, 1920, 30


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


def find_best_run() -> str | None:
    image_runs = set()
    for p in glob.glob(f"{OUTPUTS}/images/*_scene_0.png"):
        run_id = os.path.basename(p).replace("_scene_0.png", "")
        image_runs.add(run_id)

    best, best_score = None, 0
    for run_id in image_runs:
        imgs = glob.glob(f"{OUTPUTS}/images/{run_id}_scene_*.png")
        audio = glob.glob(f"{OUTPUTS}/audio/{run_id}_scene_*.mp3")
        voiceover = f"{OUTPUTS}/audio/{run_id}_full_voiceover.mp3"
        has_vo = os.path.exists(voiceover) and os.path.getsize(voiceover) > 0
        score = len(imgs) * 2 + len(audio) + (10 if has_vo else 0)
        if score > best_score:
            best, best_score = run_id, score
    return best


def build_clip(image: str, duration: float, out: str) -> bool:
    vf = (
        f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
        f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black"
    )
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image,
        "-t", f"{duration:.3f}",
        "-vf", vf,
        "-r", str(FPS),
        "-pix_fmt", "yuv420p",
        "-c:v", "libx264", "-preset", "fast",
        "-an",
        out,
    ]
    r = subprocess.run(cmd, capture_output=True, timeout=120)
    return r.returncode == 0 and os.path.exists(out)


def concat_clips(clip_paths: list[str], out: str) -> bool:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        list_file = f.name
        for p in clip_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")
    r = subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
         "-c:v", "libx264", "-preset", "fast", "-an", out],
        capture_output=True, timeout=300,
    )
    os.remove(list_file)
    return r.returncode == 0


def mux_audio(video: str, audio: str, out: str) -> bool:
    r = subprocess.run(
        ["ffmpeg", "-y",
         "-i", video,
         "-i", audio,
         "-c:v", "copy",
         "-c:a", "aac", "-b:a", "192k",
         "-shortest",
         out],
        capture_output=True, timeout=300,
    )
    return r.returncode == 0


def assemble(run_id: str) -> str | None:
    print(f"\n▶ Ensamblando run: {run_id}")

    # Recopilar imágenes ordenadas
    images = sorted(glob.glob(f"{OUTPUTS}/images/{run_id}_scene_*.png"))
    if not images:
        print("  ✗ No se encontraron imágenes")
        return None
    print(f"  → {len(images)} imágenes encontradas")

    # Calcular duración de cada escena
    voiceover = f"{OUTPUTS}/audio/{run_id}_full_voiceover.mp3"
    has_voiceover = os.path.exists(voiceover) and os.path.getsize(voiceover) > 0
    total_duration = ffprobe_duration(voiceover) if has_voiceover else 0.0

    scene_durations = []
    for i in range(len(images)):
        scene_audio = f"{OUTPUTS}/audio/{run_id}_scene_{i}.mp3"
        if os.path.exists(scene_audio) and os.path.getsize(scene_audio) > 0:
            d = ffprobe_duration(scene_audio)
            scene_durations.append(d if d > 0 else 3.0)
        else:
            scene_durations.append(3.0)

    # Si hay voiceover, redistribuir duración para que cubra todo el video
    if has_voiceover and total_duration > 0:
        sum_scenes = sum(scene_durations)
        if sum_scenes < total_duration:
            # Distribuir el tiempo restante en la primera escena
            scene_durations[0] += total_duration - sum_scenes
        print(f"  → Voiceover: {total_duration:.1f}s — Duración escenas: {[f'{d:.1f}' for d in scene_durations]}")
    else:
        print(f"  → Sin voiceover, usando {sum(scene_durations):.1f}s total")

    video_dir = f"{OUTPUTS}/video"
    os.makedirs(video_dir, exist_ok=True)
    tmp_clips = []

    # Construir clip por escena
    for i, (img, dur) in enumerate(zip(images, scene_durations)):
        clip_out = os.path.join(video_dir, f"{run_id}_clip_{i}.mp4")
        print(f"  → Escena {i}: {dur:.1f}s ...", end=" ", flush=True)
        if build_clip(img, dur, clip_out):
            tmp_clips.append(clip_out)
            print("✓")
        else:
            print("✗ error")

    if not tmp_clips:
        print("  ✗ No se pudo crear ningún clip")
        return None

    # Concatenar clips (video sin audio)
    concat_out = os.path.join(video_dir, f"{run_id}_concat.mp4")
    print(f"  → Concatenando {len(tmp_clips)} clips...", end=" ", flush=True)
    if not concat_clips(tmp_clips, concat_out):
        print("✗")
        return None
    print("✓")

    # Muxear audio
    final_out = os.path.join(video_dir, f"{run_id}_final.mp4")
    if has_voiceover:
        print(f"  → Agregando voiceover...", end=" ", flush=True)
        if mux_audio(concat_out, voiceover, final_out):
            print("✓")
        else:
            print("✗ — usando video sin audio")
            os.rename(concat_out, final_out)
    else:
        os.rename(concat_out, final_out)
        print("  → Sin audio (no hay voiceover)")

    # Limpiar temporales
    for p in tmp_clips:
        try:
            os.remove(p)
        except Exception:
            pass
    if os.path.exists(concat_out):
        try:
            os.remove(concat_out)
        except Exception:
            pass

    size_mb = os.path.getsize(final_out) / 1024 / 1024
    print(f"\n  ✅ Video final: {final_out}  ({size_mb:.1f} MB)")
    return final_out


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    if len(sys.argv) > 1:
        run_ids = sys.argv[1:]
    else:
        # Encontrar todos los runs con imágenes + voiceover
        run_ids = []
        for p in sorted(glob.glob(f"{OUTPUTS}/images/*_scene_0.png")):
            run_id = os.path.basename(p).replace("_scene_0.png", "")
            voiceover = f"{OUTPUTS}/audio/{run_id}_full_voiceover.mp3"
            if os.path.exists(voiceover) and os.path.getsize(voiceover) > 0:
                run_ids.append(run_id)

        if not run_ids:
            # Fallback: cualquier run con imágenes
            best = find_best_run()
            run_ids = [best] if best else []

    if not run_ids:
        print("✗ No se encontraron runs con assets completos.")
        sys.exit(1)

    results = []
    for run_id in run_ids:
        path = assemble(run_id)
        if path:
            results.append(path)

    print(f"\n{'='*50}")
    print(f"Videos generados: {len(results)}")
    for p in results:
        print(f"  → {p}")


if __name__ == "__main__":
    main()
