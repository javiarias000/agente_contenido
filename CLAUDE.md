# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend (FastAPI)
```bash
# Start API server
.venv/bin/uvicorn api.main:app --reload --port 8000

# Install dependencies
.venv/bin/pip install -r requirements.txt
```

### Dashboard (Next.js)
```bash
cd dashboard
npm run dev       # dev server on :3000
npm run build
npm run lint
```

### Video assembly (offline, no API)
```bash
# Assemble any run with existing images + voiceover
.venv/bin/python assemble_video.py [RUN_ID]

# Regenerate silent/broken audio via OpenAI TTS + assemble + burn subtitles
.venv/bin/python fix_audio_and_assemble.py [RUN_ID]
```

## Environment setup

Copy `.env.example` to `.env` and fill in keys. Key settings:

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | GPT-4o, DALL-E 3 / gpt-image-1.5, Whisper, TTS fallback |
| `ELEVENLABS_API_KEY` | TTS (free tier cannot use library voices — falls back to OpenAI TTS) |
| `FAL_API_KEY` | Kling image-to-video via fal.ai (UGC photo mode, optional) |
| `SUNO_COOKIE` | Background music generation (optional) |
| `GOOGLE_VEO_API_KEY` | Reserved for future Google Veo integration (not yet active) |
| `OUTPUTS_DIR` | Where generated files are saved (default: `./outputs`) |
| `BRANDS_DIR` | Where brand JSON profiles are stored (default: `./brands`) |

Models can be overridden: `TEXT_MODEL` (default `gpt-4o-mini`), `IMAGE_MODEL` (default `gpt-image-1.5`), `WHISPER_MODEL` (default `whisper-1`).

HyperFrames uses **`gpt-4.1-mini`** hardcoded (not overridable by env vars).

## Architecture

The system is a content generation engine with an agentic pipeline structure. The backend runs a FastAPI server; the frontend is a Next.js dashboard. Everything communicates via REST + Server-Sent Events (SSE) for real-time progress.

### Request flow

```
POST /api/pipelines/run
  → creates PipelineRun in SQLite
  → launches pipeline in BackgroundTask
  → client subscribes to GET /api/pipelines/sse/{run_id}
  → pipeline emits PipelineEvents → EventBus → SSE stream
  → (interactive mode) pipeline pauses, waits for POST /api/pipelines/{run_id}/feedback
```

---

## Pipeline system (`pipelines/`)

Each pipeline inherits `BasePipeline` and implements `build_steps()` returning an ordered list of `StepDefinition`s. Steps are executed sequentially; `BasePipeline.execute()` handles DB persistence, step resumption (skips already-completed steps on retry), and error propagation.

Available pipelines: `ugc`, `hyperframes`, `static_ads`, `avatar_reel`, `carousel`.

**To add a new pipeline:** subclass `BasePipeline`, set `pipeline_type`, implement `build_steps()`, and register it in `api/routers/pipelines.py`.

---

## Pipeline: UGC (`ugc_pipeline.py`)

Two tracks depending on whether a user photo was uploaded:

### Track A — No photo (image generation)
```
brand_load
  → script_generate
  → image_generate (AnimatedImageGenerator)   # DALL-E / gpt-image-1.5 + motion metadata
  → image_enhance (ImageQualityImprover)
  → voice_generate
  → subtitle_generate (AdvancedSubtitleGenerator)
  → video_assemble (ComposedVideoAssembler)
```

### Track B — With photo (`user_photo_path` set)
```
brand_load
  → photo_analyze (PhotoAnalyzer)             # GPT-4o vision analysis of uploaded photo
  → script_generate
  → video_generate (KlingVideoGenerator)      # fal.ai Kling image-to-video; fallback: static zoom
  → voice_generate
  → subtitle_generate (AdvancedSubtitleGenerator)
  → video_assemble (ComposedVideoAssembler)   # accepts video_paths instead of image_paths
```

**Context outputs per step:**

| Step | Key outputs |
|---|---|
| `brand_load` | `profile`, `brand_slug` |
| `photo_analyze` | `photo_analysis` |
| `script_generate` | `script` (scenes with `visual_description`, `speaker_text`, `on_screen_text`, `motion_hint`) |
| `image_generate` | `image_paths[]`, `motion_metadata[]` |
| `video_generate` | `video_paths[]`, `motion_metadata[]` |
| `voice_generate` | `audio_paths[]`, `full_voiceover_path` |
| `subtitle_generate` | `srt_path`, `srt_valid`, `words_count` |
| `video_assemble` | `final_video_path`, `srt_path` |

---

## Pipeline: HyperFrames (`hyperframes_pipeline.py`)

**Completely different rendering approach** — no ffmpeg image compositing; uses HTML + GSAP + Puppeteer.

```
brand_load
  → script_generate
  → voice_generate
  → whisper_transcribe (WhisperTranscriber)   # word-level timestamps for karaoke captions
  → hyperframes_compose (HyperFramesComposer) # GPT-4.1-mini generates HTML/GSAP composition
  → hyperframes_render (HyperFramesRenderer)  # npx hyperframes render (Puppeteer → MP4)
```

**Context outputs per step:**

| Step | Key outputs |
|---|---|
| `brand_load` | `profile`, `brand_slug` |
| `script_generate` | `script`, `audio_paths[]` |
| `voice_generate` | `audio_paths[]`, `full_voiceover_path` |
| `whisper_transcribe` | `transcript_words[]` (word + start + end timestamps) |
| `hyperframes_compose` | `composition_path` (HTML file), `total_duration` |
| `hyperframes_render` | `final_video_path` |

### HyperFrames visual system

**Visual styles** (`visual_style` param → `VISUAL_STYLES` in `hyperframes_composer.py`):

| Key | Description |
|---|---|
| `swiss_pulse` | Clinical SaaS/tech — clean grid, Inter font (default) |
| `velvet_standard` | Luxury/premium — dark gold, Cormorant Garamond |
| `maximalist_type` | Loud kinetic — oversized type, Bebas Neue |
| `data_drift` | Futuristic AI/ML — neon on dark, Space Grotesk |
| `soft_signal` | Intimate wellness — warm tones, DM Serif Display |
| `shadow_cut` | Dark cinematic — high contrast, Barlow Condensed |

Brand colors from `profile.colors` override style defaults (accent, bg, primary, secondary).

**Transition styles** (`transition_style` param):

| Key | Behavior |
|---|---|
| `crossfade` | Black overlay fade (default) |
| `flash` | White camera-flash snap |
| `zoom_punch` | Scale-in/out hard cut (no overlay) |
| `wipe_left` | Clip-path horizontal wipe using accent color |
| `glitch` | skewX distortion + accent flash |

**Motion intensity** (`motion_intensity` param):
- `calm` — Ken Burns max 1.04×, sine.inOut eases, 0.8–1.4s durations
- `medium` — Ken Burns max 1.08×, mixed eases, 0.5–0.9s durations
- `energetic` — Ken Burns 1.10–1.15×, fast pan ±40px, elastic/back eases, word-by-word stagger

**Text animation** (`text_animation` param):
- `slide` — enter from y:60–80 with opacity
- `scale` — scale from 0.35–0.5 to 1.0 (logo-reveal feel)
- `split` — individual word spans staggered (luxury editorial)
- `typewriter` — clip-path reveal left-to-right with cursor bar

### HyperFrames composition rules (enforced by `COMPOSER_SYSTEM` prompt)
- GSAP timeline always `{ paused: true }` — `window.__timelines = { "root": tl }` is required
- No `Math.random()`, `Date.now()`, `repeat: -1`, async/await inside timeline
- All elements must animate IN with `tl.from()` — nothing appears fully-formed
- Captions are **NOT** generated by the LLM — they are injected by `_inject_captions()` after LLM response
- `.scene-content` must use flexbox layout, never `position: absolute`
- Three layers minimum per scene: background treatment, foreground content, accent elements

### Karaoke caption injection (`_inject_captions()` in `hyperframes_composer.py`)
- Groups Whisper words into 3–4 word chunks (break on pauses >0.4s, sentence punctuation, or max size)
- Each group fades in as unit; each word lights up with brand accent color at exact Whisper timestamp
- CSS class `.hf-cg` (group container), `.hf-ct` (text), `.hf-cw` (individual word span)
- Positioned `bottom: 300px`, `font-size: 60px`, `font-weight: 800`
- Tweens appended to existing `window.__timelines['root']` — deterministic, independent of LLM

### HyperFrames rendering dependencies
- Requires **Node.js** + `npx hyperframes` (downloaded automatically via `--yes`)
- Requires **Chromium or Chrome** installed (Puppeteer; checked in `_CHROMIUM_CANDIDATES` list)
- Docker needs: `PUPPETEER_CHROMIUM_ARGS=--no-sandbox --disable-dev-shm-usage --disable-gpu`
- Render timeout: **15 minutes** — complex compositions can be slow
- Audio mixed into rendered video via ffmpeg after render; falls back to mute if mix fails

---

## Skill system (`skills/`)

Skills are atomic units of work. Each inherits `BaseSkill` and implements `async run(inputs, interactive) -> SkillResult`. The `inputs` dict is a shared context accumulating outputs across all prior steps.

Skills emit progress via `self.emit(event_type, message, data)`. In interactive mode, `self.request_feedback(...)` pauses execution and waits up to 10 minutes for user feedback.

### Key skills

| Skill | File | Description |
|---|---|---|
| `ScriptGenerator` | `script_generator.py` | GPT-4o generates outline then expands 4 scenes in parallel. Output includes `motion_hint` field. |
| `AnimatedImageGenerator` | `animated_image_generator.py` | Extends `ImageGenerator`; extracts motion hints from `visual_description` text patterns; saves `_motion.json` per image. |
| `ImageQualityImprover` | `image_quality_improver.py` | Post-processes images (contrast/sharpness). |
| `PhotoAnalyzer` | `photo_analyzer.py` | GPT-4o vision analysis of user-uploaded photo. |
| `KlingVideoGenerator` | `kling_video_generator.py` | fal.ai Kling v1.6 image-to-video. Polls `queue.fal.run` every 5s, 5-min timeout. Splits video into N scene clips. Falls back to static `zoompan` clips if `FAL_API_KEY` not set. |
| `VoiceGenerator` | `voice_generator.py` | ElevenLabs TTS with automatic fallback to OpenAI TTS (`nova` voice) on 402/401. Output always 44100 Hz stereo. |
| `AdvancedSubtitleGenerator` | `advanced_subtitle_generator.py` | Whisper transcription → validated SRT. Falls back: words → segments → full transcript. Validates min_duration, clamps to audio length. |
| `WhisperTranscriber` | `whisper_transcriber.py` | Whisper → `transcript_words[]` with word-level timestamps. Used exclusively by HyperFrames pipeline for karaoke captions. Falls back to segments if word-level not available. |
| `ComposedVideoAssembler` | `composed_video_assembler.py` | Ken Burns animation via ffmpeg crop+rescale (3 intensity levels), per-clip fade in/out for transitions, concat demuxer, subtitle burn. Accepts either `image_paths` or `video_paths`. |
| `HyperFramesComposer` | `hyperframes_composer.py` | gpt-4.1-mini generates GSAP/HTML composition. Injects karaoke captions deterministically. Saves to `outputs/compositions/{run_id}/index.html`. |
| `HyperFramesRenderer` | `hyperframes_renderer.py` | `npx hyperframes render` → silent MP4, then ffmpeg audio mix. |
| `Assembler` | `assembler.py` | **DEPRECATED** — replaced by `ComposedVideoAssembler`. Still on disk for reference. |
| `VideoAnimator` | `video_animator.py` | **NOT USED** — removed from UGC pipeline. Ken Burns logic now lives in `ComposedVideoAssembler`. |

### Script templates (`skills/templates/`)

`ScriptGenerator` selects a template by `angle_type` (`sales`, `competitor`, `trending`, `educational`). Each subclasses `BaseTemplate` and provides `system_prompt_additions(ctx)`. Add new angles here and register in `ScriptGenerator.TEMPLATES`.

### Motion hint system (`AnimatedImageGenerator`)

Keywords detected in `visual_description` → `motion_type`:
```
"zoom in"/"move forward" → zoom_in
"zoom out"/"move backward" → zoom_out
"pan left"/"slide left" → pan_left
"pan right"/"slide right" → pan_right
"pan up" → pan_up    "pan down" → pan_down
"slow pan" → slow_pan    "subtle zoom" → subtle_zoom
"diagonal" → diagonal    "static"/"none" → static
```
Each image gets a `_motion.json` sidecar with `motion_type`, `direction`, `target`, `duration_seconds`, `speaker_text`, `on_screen_text`.

### Ken Burns implementation (`ComposedVideoAssembler`)

Uses static ffmpeg crop (not progressive `zoompan`) — frame is already at max zoom, not animated:
```python
_MOTION_CROP = {"calm": 0.03, "medium": 0.08, "energetic": 0.16}
# zoom_in: crop center {crop_w}x{crop_h} → rescale to 1080x1920
```
Per-clip fade in/out durations vary by transition style (`_FADE_DURATION`). Flash transition uses white fade (`:white=1`), all others black.

**Audio output must be 44100 Hz stereo.** OpenAI TTS generates 24 kHz mono — always resample with `-ar 44100 -ac 2`.

---

## Data model (`api/models.py`)

Three SQLModel tables: `Brand`, `PipelineRun`, `PipelineStep`. All JSON columns use `Column(JSON)`. DB is SQLite via aiosqlite, auto-created on startup.

Brand profiles are also persisted as JSON files in `brands/` for offline access by skills.

---

## Output structure

```
outputs/
  scripts/        {run_id}_script.json
  images/         {run_id}_scene_{i}.png  +  {run_id}_scene_{i}_motion.json
  audio/          {run_id}_scene_{i}.mp3  +  {run_id}_full_voiceover.mp3
  video/          {run_id}_final.mp4  +  {run_id}.srt
  compositions/   {run_id}/index.html      ← HyperFrames only
```

`/outputs` is served as static files by FastAPI.

---

## API Gateway — `api/routers/pipelines.py`

`PipelineRunRequest` shared params (all pipelines):
- `pipeline_type`: `ugc | hyperframes | static_ads | avatar_reel | carousel`
- `brand_slug`, `mode` (interactive/headless), `platform`, `angle_type`, `target_duration`
- `voice_id`, `custom_hook`, `character_description`

UGC-only params: `user_photo_path`, `competitor_name`

HyperFrames-only params: `visual_style`, `transition_style`, `motion_intensity`, `text_animation`, `creative_brief`

Both UGC and HyperFrames accept `transition_style`, `motion_intensity`, and `creative_brief` — UGC uses them in ffmpeg; HyperFrames passes them to the GSAP system prompt.

---

## Dashboard (`dashboard/src/`)

- `lib/api.ts` — typed wrappers for all backend REST calls
- `lib/sse.ts` — SSE client that maps event types to UI state
- `lib/types.ts` — shared TypeScript types mirroring backend models
- Pages under `app/`: `pipelines/` (run + monitor), `brands/` (CRUD), `outputs/` (gallery)

State: Zustand. Data fetching: SWR for polling + native EventSource for SSE.

`dashboard/CLAUDE.md` → `@AGENTS.md` which warns that this Next.js version has breaking changes; read `node_modules/next/dist/docs/` before writing frontend code.

---

## Known limitations and technical debt

| Issue | Location | Status |
|---|---|---|
| Ken Burns is static crop, not progressive keyframe animation | `composed_video_assembler.py:_motion_filter()` | Open — `zoompan` filter proposed but not implemented |
| Silent subtitle fallback (no warning on ffmpeg failure) | `composed_video_assembler.py:_burn_subtitles()` | Partial fix (logs warning, still copies without subs) |
| `VideoAnimator` (`video_animator.py`) — GOOGLE_VEO_API_KEY is verified but never called | `video_animator.py:37` | Dead code — not in any active pipeline |
| `Assembler` (`assembler.py`) still on disk | `skills/assembler.py` | Deprecated; can be deleted |
| HyperFrames renderer requires Chromium + Node.js | `hyperframes_renderer.py` | Must be pre-installed in environment |
| `ComposedVideoAssembler._burn_subtitles` path escaping uses `/` not `\\:` | `composed_video_assembler.py:353` | May fail on Windows with paths containing colons |
