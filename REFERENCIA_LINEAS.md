# REFERENCIA RÁPIDA: Líneas Clave del Código

## Estructura de Archivos Clave

```
/home/ubuntu/agente_contenido/
├── api/
│   ├── models.py           (datos: Brand, PipelineRun, PipelineStep)
│   ├── config.py           (settings)
│   ├── events.py           (EventBus, PipelineEvent)
│   └── routers/
│       └── pipelines.py    (endpoint POST /api/pipelines/run)
├── pipelines/
│   ├── base_pipeline.py    (orquestación)
│   ├── ugc_pipeline.py     (flujo UGC)
│   └── avatar_reel_pipeline.py
├── skills/
│   ├── __init__.py         (BaseSkill, SkillResult)
│   ├── assembler.py        (PROBLEMAS aquí)
│   ├── video_animator.py   (superficial)
│   ├── script_generator.py (generación de scripts)
│   ├── image_generator.py
│   ├── voice_generator.py
│   └── templates/
│       └── base_template.py
└── dashboard/              (Next.js frontend)
```

---

## PROBLEMA 1: Logo fuera del frame

### Ubicación: `skills/assembler.py`

| Línea | Código | Problema |
|-------|--------|----------|
| 15-16 | `OUTPUT_WIDTH = 1080` | Dimensión fija sin customización |
| 15-16 | `OUTPUT_HEIGHT = 1920` | Dimensión fija sin customización |
| 137-140 | `vf = f"scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:force_original_aspect_ratio=decrease,pad=..."` | **PROBLEMA**: Logo puede caer en padding |
| 128-159 | `_build_scene_clips()` | Genera clips sin overlay de logo |

### Contexto de ejecución

```
ugc_pipeline.py:111-112
  ↓ Assembler step
  ↓ assembler.py:61 run()
    ├─ línea 74: _build_scene_clips()
    │  ├─ línea 137-140: escala + padding
    │  └─ línea 142-155: ffmpeg -loop -i image
    └─ línea 79: _concatenate_clips()
```

### Impacto en componentes

- **ScriptGenerator** (script_generator.py): No sabe dónde está logo
- **ImageGenerator** (image_generator.py): Genera imagen sin metadata de logo
- **Assembler** (assembler.py): Aplica escala sin considerar logo

### Solución requerida

```python
# skills/composed_video_assembler.py (NEW)
class ComposedVideoAssembler:
    async def _compose_scene_videos(self, ...):
        # - Detectar logo en imagen (corner detection)
        # - Aplicar safe area (5% margin)
        # - Reposicionar logo si fuera de safe area
        # - Reescalar imagen sin afectar logo
```

---

## PROBLEMA 2: Subtítulos desaparecen

### Ubicación: `skills/assembler.py`

| Línea | Función | Problema |
|-------|---------|----------|
| 33-43 | `_write_srt(words)` | **NO VALIDA**: words vacío, timings negativos |
| 173-190 | `_generate_subtitles()` | Si `transcript.words` vacío → cae a segments |
| 184-189 | Extracción de palabras | **FALLBACK**: segment-level timings (3-5 seg chunks) |
| 192-210 | `_burn_subtitles()` | **SILENT FALLBACK**: Si ffmpeg error → copia sin subtítulos (línea 210) |
| 199 | `abs_srt.replace(":", "\\:")` | Escape de path incorrecto en Windows |
| 205 | `-c:a copy` | No resampling de audio si Whisper falló |

### Cascada de fallos

```
Whisper (línea 178)
  ↓ response_format="verbose_json", timestamp_granularities=["word"]
  ↓ Si audio corto: transcript.words = None
  ↓ línea 185: hasattr(transcript, "words") = False
  ↓ línea 187: cae a transcript.segments
  ↓ línea 189: words con timing de SEGMENTO (no palabra)
  ↓ línea 190: _write_srt(words) → SRT con pocas líneas gigantes
  ↓ línea 200-207: ffmpeg intenta grabar subtítulos
  ↓ línea 208-210: Si error → COPIA SIN SUBTÍTULOS (SIN AVISAR)
```

### Variables críticas

```python
# assembler.py
settings.whisper_model  # (api/config.py:43)
OUTPUT_WIDTH = 1080     # (línea 15)
OUTPUT_HEIGHT = 1920    # (línea 16)
```

### Solución requerida

```python
# skills/advanced_subtitle_generator.py (NEW)
class AdvancedSubtitleGenerator:
    async def _transcribe_audio(self, audio_path):
        # - Validar response (words vs segments)
        # - Fallback a script si Whisper falla
        # - Logging detallado
    
    def _validate_chunk_timings(self, chunks):
        # - Validar start < end
        # - Validar no hay gaps enormes
        # - Validar no hay overlaps
    
    async def _write_srt_validated(self, chunks, srt_path):
        # - Retornar metadata de validación
        # - NO silent failures
```

---

## PROBLEMA 3: Sin transiciones entre escenas

### Ubicación: `skills/assembler.py`

| Línea | Código | Problema |
|-------|--------|----------|
| 161-171 | `_concatenate_clips()` | Usa ffmpeg **concat demuxer** (corte seco) |
| 167-168 | `ffmpeg -f concat` | NO transiciones |

### Flujo

```
assembler.py:79 _concatenate_clips()
  ├─ línea 162-165: Crea filelist.txt con paths
  ├─ línea 166-170: Ejecuta: ffmpeg -f concat -i filelist.txt output.mp4
  └─ Resultado: clips concatenados sin transiciones
```

### Solución requerida

```python
# skills/composed_video_assembler.py
async def _concatenate_with_transitions(self, clip_paths, output_path):
    # Usar ffmpeg xfade filter
    # "transition=fade:duration=0.2:offset=2.8"
    # 200ms fade entre clips
```

---

## PROBLEMA 4: VideoAnimator superficial

### Ubicación: `skills/video_animator.py`

| Línea | Código | Problema |
|-------|--------|----------|
| 17-20 | Clase docstring | Promete "Google Veo" pero no la usa |
| 37-39 | `if not settings.google_veo_api_key:` | Verifica pero **NUNCA USA** Google Veo |
| 91-153 | `_analyze_image_for_motion()` | Usa **Gemini** (no Google Veo) |
| 126 | `GEMINI_API_URL` | Hardcoded Gemini endpoint |
| 155-197 | `_apply_motion_with_ffmpeg()` | Aplica **filtros estáticos** (no keyframes) |
| 161-169 | `ffmpeg_filters = {...}` | Ej: `"zoom_in": "scale=iw*1.2:ih*1.2,crop=iw:ih"` |

### Problemas específicos

**Línea 161-169: Filtros estáticos**
```python
ffmpeg_filters = {
    "zoom_in": "scale=iw*1.2:ih*1.2,crop=iw:ih",  # ← Escala 1.2x CONSTANTE
    "zoom_out": "scale=iw*0.8:ih*0.8,pad=...",    # ← Escala 0.8x CONSTANTE
    "pan_left": "crop=iw*0.9:ih:0:0",             # ← Crop CONSTANTE
}
```

**Debería ser:**
```python
# zoompan con interpolación
"zoom_in": "zoompan=z='min(zoom+0.0033,1.3)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
```

**Línea 37-39: Google Veo no usado**
```python
if not settings.google_veo_api_key:  # Verifica
    await self.emit("log", "GOOGLE_VEO_API_KEY no configurada")
    return SkillResult(status="skipped")
# Nunca llama Google Veo API
```

### Contexto en pipeline

```
ugc_pipeline.py:114-118
  ├─ Assembler (step 6)
  └─ VideoAnimator (step 7)
     ├─ Recibe: final_video_path (video concatenado de 9+ segundos)
     ├─ Aplica: mismo filtro a TODO el video
     └─ Resultado: animación genérica en TODO clip (no por escena)
```

### Impacto

- Animación POST-PROCESSING cara (re-encode de video completo)
- Filtros genéricos (1.2x zoom en todos lados)
- No optimizado para contenido específico

---

## PROBLEMA 5: Contexto sin validación

### Ubicación: `pipelines/base_pipeline.py`

| Línea | Código | Problema |
|-------|--------|----------|
| 39 | `context: dict[str, Any] = {**inputs}` | Contexto inicial sin type hints |
| 60-66 | `skill = step_def.skill_class(...)` | No valida inputs |
| 67 | `context.update(result.outputs)` | **NO VALIDA** outputs antes de mergear |
| 135 | `if isinstance(v, (str, int, float, bool, list, dict, type(None)))` | Filtro débil en _update_step |
| 159-169 | `_get_step_output()` | Retorna dict sin validación |

### Cadena de paso

```
Base case: image_paths

ScriptGenerator
  └─ outputs: {"script": {...}, "image_paths": ["/path/1.png", ...]}

ImageGenerator  (recibe context con "script" + "image_paths")
  ├─ script = inputs["script"]  (del script anterior)
  ├─ image_paths = await self._generate_all()
  └─ outputs: {"image_paths": ["/path/2.png", ...]}  ← sobrescribe

VoiceGenerator  (recibe context actualizado)
  ├─ script = inputs["script"]
  ├─ image_paths = inputs["image_paths"]  (puede estar vacío!)
  ├─ audio_paths = [...]
  └─ outputs: {"audio_paths": [...], "full_voiceover_path": "..."}

Assembler
  ├─ image_paths = inputs["image_paths"]
  ├─ audio_paths = inputs["audio_paths"]
  ├─ if not image_paths: raise Error  ← AQUÍ DETECTA (pero tarde!)
```

### Fallos silenciosos

```python
# assembler.py:62-64
image_paths: list[str] = inputs["image_paths"]  # Podría estar vacío!
audio_paths: list[str] = inputs["audio_paths"]   # Podría estar vacío!
full_voiceover_path: str = inputs["full_voiceover_path"]  # Podría no existir!

# No valida hasta más adelante
# Si inputs["image_paths"] es None o []:
#   - línea 132: for i, (img, audio) in enumerate(zip(image_paths, audio_paths))
#   - zip([], [...]) → [] → ningún clip generado
#   - clips = [] → concat_path es vacío
#   - Video final sin contenido
```

---

## Archivos a CREAR

```
NEW FILES:
├── skills/animated_image_generator.py       (200+ líneas)
├── skills/advanced_subtitle_generator.py    (300+ líneas)
├── skills/composed_video_assembler.py       (500+ líneas)
├── ARQUITECTURA.md                          (Este documento)
├── IMPLEMENTACION_DETALLADA.md
└── ANALISIS_PROBLEMAS.md
```

## Archivos a MODIFICAR

```
MODIFY:
├── pipelines/ugc_pipeline.py                (línea 84-119)
│   ├─ Cambiar ImageGenerator → AnimatedImageGenerator
│   ├─ Cambiar Assembler → ComposedVideoAssembler
│   └─ Remover VideoAnimator
├── skills/script_generator.py               (línea 46-54)
│   └─ Agregar motion_hint al prompt
└── (Opcional) skills/assembler.py
    └─ Deprecate con warning
```

## Archivos a DEPRECATE

```
DEPRECATE:
├── skills/video_animator.py
│   └─ Agregar warning: "Integrado en ComposedVideoAssembler"
└── skills/assembler.py  (opcional)
    └─ Agregar: "Use ComposedVideoAssembler en su lugar"
```

---

## Flujos de Ejecución

### Flujo ACTUAL

```
POST /api/pipelines/run (api/routers/pipelines.py:46)
  └─ UGCPipeline.execute()
     ├─ brand_load (_BrandLoadSkill)
     ├─ script_generate (ScriptGenerator)
     ├─ image_generate (ImageGenerator)
     │  └─ scripts/image_generator.py:64
     │     └─ _generate_all(scenes)
     │        └─ generate_single() × N (semaphore=3)
     ├─ image_enhance (ImageQualityImprover)
     ├─ voice_generate (VoiceGenerator)
     ├─ video_assemble (Assembler)
     │  └─ skills/assembler.py:61
     │     ├─ _build_scene_clips() (línea 74)
     │     ├─ _concatenate_clips() (línea 79)
     │     ├─ _generate_subtitles() (línea 84)
     │     └─ _burn_subtitles() (línea 89)
     └─ video_animate (VideoAnimator)
        └─ skills/video_animator.py:29
           ├─ _analyze_image_for_motion() (Gemini)
           └─ _apply_motion_with_ffmpeg() (ffmpeg filter)

SSE /api/pipelines/sse/{run_id} (api/routers/pipelines.py:90)
  └─ EventBus.emit() → Dashboard
```

### Flujo PROPUESTO

```
POST /api/pipelines/run
  └─ UGCPipeline.execute()
     ├─ brand_load
     ├─ script_generate (ACTUALIZADO: motion_hint en output)
     ├─ image_generate → AnimatedImageGenerator (NUEVO)
     │  └─ _extract_motion_hint()
     │  └─ Guarda motion.json
     ├─ image_enhance
     ├─ voice_generate
     ├─ video_assemble → ComposedVideoAssembler (NUEVO)
     │  ├─ _compose_scene_videos()
     │  │  ├─ Apply motion (zoompan)
     │  │  ├─ Draw on_screen text
     │  │  └─ Overlay logo (safe area)
     │  ├─ _concatenate_with_transitions() (xfade)
     │  ├─ AdvancedSubtitleGenerator (NUEVO)
     │  │  ├─ _transcribe_audio()
     │  │  ├─ _validate_chunk_timings()
     │  │  └─ _write_srt_validated()
     │  ├─ _burn_subtitles_validated()
     │  └─ _add_bgm_if_configured()
     └─ (VideoAnimator REMOVIDO)

SSE stream (SIN CAMBIOS)
```

---

## Tablas de Referencia Rápida

### Constants & Config

```python
# api/config.py
settings.openai_api_key          # OpenAI API key
settings.elevenlabs_api_key      # ElevenLabs TTS
settings.google_veo_api_key      # (NOT USED in video_animator.py)
settings.suno_cookie             # Suno BGM
settings.whisper_model           # "whisper-1"
settings.text_model              # "gpt-4o-mini"
settings.image_model             # "gpt-image-1.5" or "dall-e-3"
settings.outputs_dir             # "./outputs"
settings.brands_dir              # "./brands"

# assembler.py
OUTPUT_WIDTH = 1080              # línea 15
OUTPUT_HEIGHT = 1920             # línea 16
OUTPUT_FPS = 30                  # línea 17
```

### Modelos de datos

```python
# api/models.py
Brand                            # línea 9
  - slug, colors, tone_of_voice, character_anchor

PipelineRun                      # línea 29
  - run_id, pipeline_type, status, mode, input_config

PipelineStep                     # línea 48
  - run_id, step_name, status, input_data, output_data

OutputAsset                      # línea 64
  - asset_type, file_path, asset_metadata
```

### EventBus

```python
# api/events.py
PipelineEvent                    # línea 10
  - event_type: step_start|step_complete|step_error|step_paused|progress|log

EventBus                         # línea 33
  - subscribe(run_id) → Queue
  - emit(event)
  - wait_for_feedback(run_id)
  - submit_feedback(run_id, feedback)
```

---

**FIN DE REFERENCIA**

