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
| `OPENAI_API_KEY` | GPT-4o, DALL-E 3, Whisper, TTS fallback |
| `ELEVENLABS_API_KEY` | TTS (free tier cannot use library voices — falls back to OpenAI TTS) |
| `SUNO_COOKIE` | Background music generation (optional) |
| `OUTPUTS_DIR` | Where generated files are saved (default: `./outputs`) |
| `BRANDS_DIR` | Where brand JSON profiles are stored (default: `./brands`) |

Models can be overridden: `TEXT_MODEL`, `IMAGE_MODEL`, `WHISPER_MODEL`.

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

### Pipeline system (`pipelines/`)

Each pipeline inherits `BasePipeline` and implements `build_steps()` returning an ordered list of `StepDefinition`s. Steps are executed sequentially; `BasePipeline.execute()` handles DB persistence, step resumption (skips already-completed steps on retry), and error propagation.

Available pipelines: `ugc`, `static_ads`, `avatar_reel`, `carousel`.

**To add a new pipeline:** subclass `BasePipeline`, set `pipeline_type`, implement `build_steps()`, and register it in `api/routers/pipelines.py`.

### Skill system (`skills/`)

Skills are the atomic units of work. Each inherits `BaseSkill` and implements `async run(inputs, interactive) -> SkillResult`. The `inputs` dict is a shared context that accumulates outputs across the pipeline — each step receives all prior outputs merged in.

Skills emit progress via `self.emit(event_type, message, data)`. In interactive mode, `self.request_feedback(prompt, preview_data, interactive)` pauses execution and waits up to 10 minutes for user feedback via the SSE/feedback endpoint.

Key skills:
- `ScriptGenerator` — GPT-4o generates outline then expands scenes in parallel (4 concurrent). Uses `skills/templates/` to inject angle-specific prompts.
- `ImageGenerator` — DALL-E 3 or gpt-image-* per scene; semaphore limits concurrency. Detects model via `settings.image_model.startswith("gpt-image")`.
- `VoiceGenerator` — ElevenLabs with automatic fallback to OpenAI TTS (`nova` voice). Falls back silently on 402/401 errors (free plan limitations).
- `Assembler` — pure ffmpeg: builds per-scene clips, concatenates, transcribes with Whisper, burns subtitles, optionally adds Suno BGM.

**Audio output must be 44100 Hz stereo.** OpenAI TTS generates 24 kHz mono by default; always resample with `-ar 44100 -ac 2` when muxing.

### Script templates (`skills/templates/`)

`ScriptGenerator` selects a template by `angle_type` (`sales`, `competitor`, `trending`, `educational`). Each template subclasses `BaseTemplate` and provides `system_prompt_additions(ctx)` — additional system prompt text that shapes the LLM output for that angle. Add new angles by creating a new template and registering it in `ScriptGenerator.TEMPLATES`.

### Data model (`api/models.py`)

Three SQLModel tables: `Brand` (persisted brand profiles with tone/audience/colors), `PipelineRun` (run lifecycle + input config), `PipelineStep` (per-step status, inputs, outputs, timing). All JSON columns use SQLModel's `Column(JSON)`. DB is SQLite via aiosqlite, auto-created on startup.

Brand profiles are also persisted as JSON files in `brands/` for offline access by skills (avoids DB dependency inside skill code).

### Output structure

```
outputs/
  scripts/  {run_id}_script.json
  images/   {run_id}_scene_{i}.png
  audio/    {run_id}_scene_{i}.mp3 + {run_id}_full_voiceover.mp3
  video/    {run_id}_final.mp4 + {run_id}.srt
```

`/outputs` is served as static files by FastAPI.

### Dashboard (`dashboard/src/`)

- `lib/api.ts` — typed wrappers for all backend REST calls
- `lib/sse.ts` — SSE client that maps event types to UI state
- `lib/types.ts` — shared TypeScript types mirroring the backend models
- Pages under `app/`: `pipelines/` (run + monitor), `brands/` (CRUD), `outputs/` (gallery)

State management uses Zustand. Data fetching uses SWR for polling + native EventSource for SSE. The dashboard URL must match `DASHBOARD_URL` in `.env` for CORS to work.
