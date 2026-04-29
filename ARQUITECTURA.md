# ARQUITECTURA - Motor de Contenido Agéntico

## 1. DIAGRAMA DE FLUJO ACTUAL

```
POST /api/pipelines/run (api/routers/pipelines.py:46)
    ↓
Crear PipelineRun en SQLite (models.py)
    ↓
BasePipeline.execute() (pipelines/base_pipeline.py:36)
    ↓
Para cada StepDefinition:
    ├─ _step_completed() → cached (línea 48)
    ├─ _update_step(status="running") (línea 56)
    ├─ Instanciar Skill (línea 60)
    ├─ skill.run(context) (línea 66)
    │   ├─ Emite eventos vía EventBus (skills/__init__.py:27)
    │   └─ Retorna SkillResult con outputs
    ├─ context.update(result.outputs) (línea 67)
    ├─ _update_step(status="completed") (línea 68)
    └─ _emit("step_complete") (línea 69)
    ↓
SSE stream (api/routers/pipelines.py:90)
    ↓
Dashboard recibe eventos en tiempo real
```

### Pipeline: UGC (ugc_pipeline.py)

**Flujo secuencial:**

```
1. brand_load (_BrandLoadSkill)
   └─ Carga brand_slug.json o ejecuta BrandAnalyzer
   
2. script_generate (ScriptGenerator)
   ├─ Genera outline con GPT-4o
   ├─ Expande 4 escenas en paralelo
   └─ Retorna: script (con scenes[i].visual_description, speaker_text)
   
3. image_generate (ImageGenerator)
   ├─ Para c/escena: _build_image_prompt() (skills/image_generator.py:28)
   ├─ Llama DALL-E 3 o gpt-image-1.5 (semaphore=3)
   ├─ Guarda en outputs/images/{run_id}_scene_{i}.png
   └─ Retorna: image_paths[]
   
4. image_enhance (ImageQualityImprover)
   └─ Mejora contraste/calidad de imágenes
   
5. voice_generate (VoiceGenerator)
   ├─ ElevenLabs text_to_speech.convert() (skills/voice_generator.py:89)
   ├─ Fallback a OpenAI TTS si error (línea 85)
   ├─ Output: 44100 Hz stereo MP3
   └─ Retorna: audio_paths[], full_voiceover_path
   
6. video_assemble (Assembler)
   ├─ _build_scene_clips(): ffmpeg -loop 1 → 1080x1920 MP4 (línea 128)
   │   └─ scale={1080}:{1920}, pad center
   ├─ _concatenate_clips(): concat demuxer (línea 161)
   ├─ _generate_subtitles(): Whisper transcription (línea 173)
   │   └─ words → SRT (8-word chunks) (línea 33)
   ├─ _burn_subtitles(): ffmpeg subtitles filter (línea 192)
   └─ Retorna: final_video_path, srt_path
   
7. video_animate (VideoAnimator)
   ├─ _analyze_image_for_motion(): Gemini API (línea 91)
   │   └─ Retorna: zoom_in|zoom_out|pan_left|pan_right|pan_up|pan_down|diagonal
   ├─ _apply_motion_with_ffmpeg(): ffmpeg scale/crop filters (línea 155)
   └─ Retorna: animated_video_path
```

---

## 2. PROBLEMAS IDENTIFICADOS

### 2.1 PROBLEMA: Logo sale del cuadro (Assembler)

**Ubicación:** `skills/assembler.py`, línea 137-140

```python
vf = (
    f"scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:force_original_aspect_ratio=decrease,"
    f"pad={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:(ow-iw)/2:(oh-ih)/2"
)
```

**Raíz del problema:**
- `force_original_aspect_ratio=decrease` mantiene la relación de aspecto pero **reduce** la imagen
- Si imagen es 1024x1024 (cuadrada), se reduce a 1080x1920 (9:16) con cintas negras
- **El logo (png generado por DALL-E) cae en las cintas negras o se escala incorrectamente**
- No hay reescalado dinámico ni posicionamiento del logo

**Impacto:**
- Logo descentrado en videos verticales (9:16)
- Área de seguridad ignorada (15% en bordes para redes sociales)

**Código afectado:**
- `OUTPUT_WIDTH = 1080, OUTPUT_HEIGHT = 1920` (línea 15-16)
- Todas las imágenes pasan por este filtro sin customización por tipo de asset

---

### 2.2 PROBLEMA: Desaparecen subtítulos (Assembler)

**Ubicación:** `skills/assembler.py`, línea 192-210

```python
def _burn_subtitles(self, input_path: str, srt_path: str, output_path: str) -> None:
    # ...
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", input_path,
         "-vf", f"subtitles='{abs_srt}':force_style='...'",
         "-c:a", "copy", output_path],
        capture_output=True, timeout=300,
    )
    if result.returncode != 0 or not os.path.exists(output_path):
        # Fallback: copy without subtitles
        shutil.copy(input_path, output_path)
```

**Raíz del problema:**
1. **No validación de SRT:** Si `_write_srt()` produce SRT vacío o con timing malo, ffmpeg puede fallar
2. **Escape de paths:** Línea 199 reemplaza `:` en Windows → puede fallar en Linux
3. **Silent fallback:** Si ffmpeg error, copia video SIN subtítulos sin avisar (línea 210)
4. **Timing issues:** `_generate_subtitles()` (línea 173) usa Whisper con timestamps `timestamp_granularities=["word"]`
   - Si audio es corto o muy rápido, Whisper puede no devolver palabras con timing
   - `if hasattr(transcript, "words") and transcript.words:` puede ser falso (línea 185)
5. **Path escaping:** `abs_srt.replace(":", "\\:")` (línea 199) es correcto para Windows pero innecesario en Linux

**Código afectado:**
- `_write_srt()` línea 33-43: No maneja Whisper failures
- `_generate_subtitles()` línea 173-190: Retorna SRT vacío si transcript.words es vacío
- `_burn_subtitles()` línea 192-210: Silent fallback sin logging

---

### 2.3 LIMITACIÓN ARQUITECTÓNICA: Concatenación de clips

**Ubicación:** `skills/assembler.py`, línea 72-79 y 161-171

**Problema:**
```python
# 1. Build per-scene clips via ffmpeg
scene_clips = await self._build_scene_clips(image_paths, audio_paths)  # Línea 74

# 2. Concatenate
self._concatenate_clips(scene_clips, concat_path)  # Línea 79
```

**Limitaciones:**
1. **Cada clip es una imagen estática + audio** (loop 1 imagen por duración audio)
2. **No hay transiciones** entre clips → corte seco
3. **No hay composición visual** (ej: logo + fondo de gradiente)
4. **No hay track de texto dinámico** (on-screen_text grabado en cada clip)
5. **VideoAnimator es POST-PROCESSING:** Anima TODO el video concatenado (línea 65 en video_animator.py)
   - Los filtros son simples: `scale=iw*1.2:ih*1.2,crop=iw:ih` (zoom_in) → no es animación real
   - ffmpeg `-vf` aplica el filtro uniformemente → NO hay keyframes / animación progresiva

**Impacto en arquitectura:**
- No es posible animar POR ESCENA (solo video completo)
- Transiciones estáticas
- Difícil agregar overlays (logo, watermark, texto dinámico)

---

### 2.4 LIMITACIÓN: VideoAnimator es superficial

**Ubicación:** `skills/video_animator.py`, línea 155-197

```python
async def _apply_motion_with_ffmpeg(self, input_video: str, output_video: str, motion_type: str) -> bool:
    ffmpeg_filters = {
        "zoom_in": "scale=iw*1.2:ih*1.2,crop=iw:ih",
        "zoom_out": "scale=iw*0.8:ih*0.8,pad=iw:ih:(ow-iw)/2:(oh-ih)/2:black",
        "pan_left": "crop=iw*0.9:ih:0:0",
        # ...
    }
    filter_str = ffmpeg_filters.get(motion_type, ffmpeg_filters["zoom_in"])
    cmd = ["ffmpeg", "-y", "-i", input_video, "-vf", f"format=yuv420p,{filter_str}", ...]
```

**Problemas:**
1. **Los filtros son estáticos**, no progresivos en el tiempo
   - `zoom_in: "scale=iw*1.2:ih*1.2,crop=iw:ih"` aplica zoom 1.2x A TODO el video
   - No hay keyframes para progresión suave: zoom 1.0 → 1.2 en 3 segundos
2. **No usa Google Veo API** (parámetro GOOGLE_VEO_API_KEY nunca se usa)
   - Línea 37-39: Solo se verifica si está configurada, pero nunca se llama a Google Veo
   - El nombre "VideoAnimator" con "Google Gemini + ffmpeg" (línea 17-18) es engañoso
3. **Gemini solo analiza tipo de movimiento**, no genera animación
   - Línea 108-120: Prompt al Gemini solo pide el TIPO (zoom_in, pan_left, etc.)
   - Luego applica filtro ffmpeg crudamente

---

## 3. FLUJO DE DATOS ACTUAL

### Context passing (acumulativo)

```python
context: dict[str, Any] = {**inputs}  # base_pipeline.py:39

Después de each step:
context.update(result.outputs)  # base_pipeline.py:67
```

**Outputs de cada step:**

| Step | Outputs | Ubicación |
|------|---------|-----------|
| brand_load | `{"profile": {...}, "brand_slug": str}` | ugc_pipeline.py:73 |
| script_generate | `{"script": Script}` | script_generator.py |
| image_generate | `{"image_paths": [str]}` | image_generator.py:95 |
| image_enhance | `{...}` (mantiene image_paths) | image_quality_improver.py |
| voice_generate | `{"audio_paths": [str], "full_voiceover_path": str}` | voice_generator.py:75-76 |
| video_assemble | `{"final_video_path": str, "srt_path": str}` | assembler.py:125 |
| video_animate | `{"animated_video_path": str}` or `{"final_video_path": str}` | video_animator.py:77-84 |

**Problema:** Los strings en outputs son rutas absolutas, no hay validación
- Si un step falla a crear archivo, el siguiente step recibe path inválida sin error

---

## 4. PROPUESTA: NUEVA ARQUITECTURA

### 4.1 VISIÓN: Generación de video FROM IMAGE con animación nativa

**Objetivo:**
- Generar cada escena como **video animado**, no imagen estática
- Soportar overlays (logo, texto, watermark)
- Transiciones suaves entre escenas
- Compositor visual centralizado

**Flujo nuevo:**

```
ScriptGenerator
    ↓
AnimatedImageGenerator (NUEVO)
    ├─ Genera imagen base (DALL-E) con instrucciones de movimiento
    ├─ Exporta metadatos de animación (motion_hints.json)
    └─ outputs: image_paths[], motion_metadata[]
    ↓
VoiceGenerator (sin cambios)
    ├─ outputs: audio_paths[], full_voiceover_path
    └─ (ya calibrado para 44100 Hz stereo)
    ↓
ComposedVideoAssembler (NUEVO - reemplaza Assembler)
    ├─ Para cada escena:
    │  ├─ Lee motion_metadata
    │  ├─ Arma grafo ffmpeg con:
    │  │  ├─ Input image
    │  │  ├─ Logo + posicionamiento (safe area)
    │  │  ├─ On-screen text overlay
    │  │  ├─ Audio (sincronizado)
    │  │  └─ Animación (zoom/pan con keyframes)
    │  └─ Genera {run_id}_scene_{i}_animated.mp4
    ├─ Concatena con transiciones
    ├─ Whisper transcription (mejorado)
    ├─ Subtítulos con validación
    └─ outputs: final_video_path, srt_path
    ↓
VideoQualityValidator (NUEVO)
    ├─ Verifica file integrity
    ├─ Valida audio sync
    └─ outputs: validation_report
```

---

### 4.2 MÓDULOS NUEVOS

#### A. AnimatedImageGenerator (Nuevo)

**Propósito:** Generar imágenes CON METADATOS de animación

**Pseudocódigo:**

```python
class AnimatedImageGenerator(BaseSkill):
    async def run(self, inputs, interactive):
        scenes = inputs["script"]["scenes"]
        motion_metadata = []
        image_paths = []
        
        for i, scene in enumerate(scenes):
            # Analizar visual_description para hints
            motion_hint = self._extract_motion_hint(scene.visual_description)
            # ej: "zoom in on face" → {"type": "zoom", "direction": "in", "target": "face"}
            
            # Generar imagen sin metadata
            img_path = await self._generate_image_dall_e(scene, i)
            image_paths.append(img_path)
            
            # Guardar metadata
            metadata = {
                "scene_index": i,
                "image_path": img_path,
                "motion_type": motion_hint.get("type", "none"),
                "motion_direction": motion_hint.get("direction"),
                "motion_target": motion_hint.get("target"),
                "duration_seconds": scene.duration_seconds,
                "speaker_text": scene.speaker_text,
                "on_screen_text": scene.on_screen_text,
            }
            motion_metadata.append(metadata)
            
            # Guardar metadata.json
            metadata_path = img_path.replace(".png", "_motion.json")
            with open(metadata_path, "w") as f:
                json.dump(metadata, f)
        
        return SkillResult(
            status="completed",
            outputs={
                "image_paths": image_paths,
                "motion_metadata": motion_metadata,
            }
        )
```

**Cambios en ScriptGenerator:**
- Actualizar `SCENE_SYSTEM` prompt (línea 46 en script_generator.py)
- Agregar al final: `"motion_hint": "zoom in on product" o "pan left" o "static"`
- Los hints no son mandatorios, solo sugerencias

---

#### B. ComposedVideoAssembler (Reemplaza Assembler)

**Propósito:** Armar video con composición, animación y texto

**Estructura:**

```python
class ComposedVideoAssembler(BaseSkill):
    async def run(self, inputs, interactive):
        image_paths = inputs["image_paths"]
        audio_paths = inputs["audio_paths"]
        motion_metadata = inputs.get("motion_metadata", [])
        profile = inputs.get("profile", {})
        script = inputs.get("script", {})
        
        video_dir = os.path.join(settings.outputs_dir, "video")
        
        # 1. Generar clips animados por escena
        scene_videos = await self._compose_scene_videos(
            image_paths, audio_paths, motion_metadata, profile, script
        )
        
        # 2. Concatenar con transiciones
        concat_path = await self._concatenate_with_transitions(scene_videos)
        
        # 3. Subtítulos mejorados
        srt_path = await self._generate_subtitles_improved(inputs["full_voiceover_path"])
        
        # 4. Quemar subtítulos CON validación
        subtitled_path = await self._burn_subtitles_validated(concat_path, srt_path)
        
        # 5. BGM (opcional)
        final_path = await self._add_bgm_if_configured(subtitled_path, script)
        
        return SkillResult(
            status="completed",
            outputs={"final_video_path": final_path, "srt_path": srt_path}
        )

    async def _compose_scene_videos(self, image_paths, audio_paths, motion_metadata, profile, script):
        """Genera MP4 animado para cada escena.
        
        FFmpeg graph para escena i:
        
        [0:v] (image)
          → scale=1080:1920 (fit vertical 9:16)
          → pad=1080:1920:0:0:black (center if needed)
          → [scaled]
        
        [scaled]
          → (aplicar animación según motion_type)
          → [animated]
        
        [animated]
          → drawtext=fontfile=...:text='on_screen_text':... (overlay)
          → [text_overlaid]
        
        [text_overlaid]
          → overlay=logo_pos_x:logo_pos_y [final_scene]
        
        [final_scene] [audio]
          → concat=n=1:v=1:a=1
          → aac @ 44100 Hz stereo
          → output: {run_id}_scene_{i}_animated.mp4
        """
```

**Detalle: Animación con ffmpeg + keyframes**

En lugar de:
```python
filter_str = ffmpeg_filters.get(motion_type)  # "scale=iw*1.2:ih*1.2,crop=iw:ih"
```

Usar interpolación con `zoompan` filter (ffmpeg built-in):

```python
# Para zoom_in progresivo de 1.0 a 1.3 en 3 segundos a 30fps
motion_filters = {
    "zoom_in": "zoompan=z='min(zoom+0.0033,1.3)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
    "zoom_out": "zoompan=z='max(zoom-0.0033,1.0)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
    "pan_left": "crop=min(iw\\,ih*16/9):ih:min(t*iw*0.2\\,iw-ih*16/9):0",
    "pan_right": "crop=min(iw\\,ih*16/9):ih:max(0\\,iw-ih*16/9-t*iw*0.2):0",
    # etc.
}
```

El filter `zoompan`:
- `z='min(zoom+0.0033,1.3)'` → incrementa zoom 0.33% por frame (llega a 1.3 en 100 frames ≈ 3 seg)
- `d=1` → output 1 frame por input frame
- `x='iw/2-(iw/zoom/2)'` → mantiene centro

---

#### C. AdvancedSubtitleGenerator (Nuevo)

**Propósito:** Generar SRTs validados y robustos

```python
class AdvancedSubtitleGenerator:
    async def generate_srt(self, audio_path: str, script: dict) -> tuple[str, dict]:
        """Genera SRT mejorado.
        
        Retorna: (srt_path, metadata)
        metadata = {
            "total_duration": 45.5,
            "subtitle_count": 12,
            "coverage_percent": 95,
            "validation_errors": [],
        }
        """
        
        # 1. Transcribir con Whisper
        transcript = await self._transcribe_with_whisper(audio_path)
        
        # 2. Extraer palabras con timing
        words = self._extract_words_from_transcript(transcript)
        if not words:
            # Fallback: crear subtítulos del script
            words = self._synthesize_from_script(script, audio_path)
        
        # 3. Agrupar en chunks (máx 10 palabras por subtítulo)
        chunks = self._chunk_words(words, chunk_size=10)
        
        # 4. Validar timings
        chunks = self._validate_chunk_timings(chunks)
        
        # 5. Escribir SRT
        srt_path = await self._write_srt_safe(chunks)
        
        # 6. Validar output
        validation = self._validate_srt_file(srt_path)
        
        return srt_path, validation
```

---

### 4.3 CAMBIOS EN EXISTENTES

#### Cambio 1: assembler.py → deprecated, mover lógica a ComposedVideoAssembler

**Ubicación actual:** `skills/assembler.py`
**Nuevo:** `skills/composed_video_assembler.py`

**Pasos:**
1. Crear `composed_video_assembler.py` con `ComposedVideoAssembler(BaseSkill)`
2. Mantener `assembler.py` como deprecated (backward compat)
3. Actualizar `ugc_pipeline.py` línea 111 para usar `ComposedVideoAssembler`

---

#### Cambio 2: video_animator.py → mejorar o remover

**Problema actual:** VideoAnimator es superficial y caro (POST-PROCESSING)

**Opción A: Integrar en ComposedVideoAssembler (RECOMENDADO)**
- Mover lógica de Gemini analysis a AnimatedImageGenerator
- Aplicar animación POR ESCENA, no al video completo
- Eliminar VideoAnimator como step independiente

**Opción B: Mejorar VideoAnimator**
- Usar ffmpeg `zoompan` filter con keyframes
- Aplicar análisis de Gemini ANTES de Assembler
- Pasar motion_metadata al Assembler

**RECOMENDACIÓN:** Opción A

---

#### Cambio 3: ScriptGenerator prompt

**Ubicación:** `skills/script_generator.py`, línea 46-54

**Actualizar SCENE_SYSTEM:**

```python
SCENE_SYSTEM = """You are an expert short-form video scriptwriter. Expand this scene into full content.
Return JSON with:
{
  "visual_description": "string (detailed visual prompt for AI image generation...)",
  "speaker_text": "string (exact words to speak in this scene)",
  "on_screen_text": "string or null (text overlay)",
  "motion_hint": "string: none | zoom_in | zoom_out | pan_left | pan_right | pan_up | pan_down | slow_pan | subtle_zoom | diagonal"
}
...
"""
```

---

### 4.4 NUEVA ESTRUCTURA DE ARCHIVOS

```
skills/
├── assembler.py                           # DEPRECATED
├── composed_video_assembler.py            # NUEVO
├── animated_image_generator.py            # NUEVO (mejora image_generator.py)
├── advanced_subtitle_generator.py         # NUEVO
├── video_quality_validator.py             # NUEVO
└── video_animator.py                      # PUEDE ELIMINARSE
```

---

## 5. TIMELINE DE IMPLEMENTACIÓN

### Fase 1: Fundamentos (Semana 1)

```
1. Crear AnimatedImageGenerator
   - Heredar de ImageGenerator
   - Agregar _extract_motion_hint()
   - Guardar motion.json junto a cada imagen
   - Test con UGC pipeline (sin cambiar flow)

2. Crear AdvancedSubtitleGenerator
   - Mover lógica de _generate_subtitles() desde Assembler
   - Agregar validación
   - Test con existing video

3. Refactor composición:
   - Crear helpers en assembler.py:
     - _get_logo_positioned()
     - _get_safe_area_overlay()
     - _render_on_screen_text()
```

### Fase 2: ComposedVideoAssembler (Semana 2)

```
1. Crear composed_video_assembler.py
   - Implementar _compose_scene_videos()
   - Usar ffmpeg zoompan para animación
   - Soportar overlays
   - Mantener backward compat con outputs

2. Actualizar ugc_pipeline.py
   - Reemplazar Assembler por ComposedVideoAssembler
   - Remover VideoAnimator step

3. Test end-to-end
```

### Fase 3: Validación (Semana 3)

```
1. Crear VideoQualityValidator
2. Agregar checks de integridad
3. Documentación de cambios
4. Deprecation warnings en Assembler
```

---

## 6. PUNTOS TÉCNICOS CRÍTICOS

### 6.1 Audio synchronization (Crítico)

**Requisito:** Audio SIEMPRE a 44100 Hz stereo

```python
# En ComposedVideoAssembler._compose_scene_videos():
audio_resampling = (
    f"[audio] aresample=44100:channel_layout=stereo [audio_resampled]"
)

# Luego:
# [final_scene][audio_resampled] concat=n=1:v=1:a=1 [output]
```

---

### 6.2 Safe area para logos

**Estándar:** 5% margin en todos lados para plataformas sociales

```python
# Para 1080x1920 (9:16):
SAFE_LEFT = int(1080 * 0.05)      # 54px
SAFE_RIGHT = int(1080 * 0.95)     # 1026px
SAFE_TOP = int(1920 * 0.05)       # 96px
SAFE_BOTTOM = int(1920 * 0.95)    # 1824px

# Posicionar logo:
# Bottom-right corner:
logo_x = SAFE_RIGHT - logo_width - 10
logo_y = SAFE_BOTTOM - logo_height - 10
```

---

### 6.3 Transiciones suaves

```python
# FFmpeg concat demuxer no soporta transiciones
# Solución: usar overlay filter con fade

# Entre clip N y N+1:
# [clipN_with_fade_out][clipN+1_with_fade_in] overlay=... [transitioned]

# O usar simple cross-dissolve (200ms):
# ffmpeg -i clipN.mp4 -i clipN+1.mp4 \
#   -filter_complex "[0][1]xfade=transition=dissolve:duration=0.2:offset=..." \
#   output.mp4
```

---

### 6.4 Manejo de errores robusto

**Logging detallado en cada paso:**

```python
class ComposedVideoAssembler(BaseSkill):
    async def _compose_scene_videos(self, ...):
        for i, (img, audio) in enumerate(...):
            try:
                clip = await self._compose_single_scene(img, audio, motion_metadata[i])
                await self.emit("progress", f"Scene {i} OK", {"file_size": os.path.getsize(clip)})
            except Exception as e:
                await self.emit("log", f"Scene {i} FAILED: {str(e)}", {"error": str(e)})
                raise  # No silenciar errores
```

**Nunca:** Silent fallback (como en línea 210 de assembler.py)

---

## 7. VALIDACIÓN Y TESTING

### Unit tests necesarios:

```
tests/
├── test_animated_image_generator.py
│   ├── test_motion_hint_extraction()
│   ├── test_metadata_file_creation()
│   └── test_image_generation_with_metadata()
│
├── test_composed_video_assembler.py
│   ├── test_scene_composition()
│   ├── test_logo_positioning_safe_area()
│   ├── test_on_screen_text_overlay()
│   ├── test_animation_application()
│   ├── test_audio_sync()
│   └── test_concatenation_with_transitions()
│
├── test_advanced_subtitle_generator.py
│   ├── test_word_extraction()
│   ├── test_chunk_validation()
│   ├── test_srt_generation()
│   └── test_fallback_on_whisper_failure()
│
└── test_integration_ugc_pipeline.py
    └── test_full_pipeline_e2e()
```

---

## 8. ROADMAP A FUTURO

### Post-MVP:
1. **Lip-sync real:** Integrar lip_sync.py en composición
2. **Efectos dinámicos:** Transiciones, filtros por plataforma
3. **Caché de renders:** Evitar re-render de escenas idénticas
4. **Multi-threading:** Paralelizar composición por escena
5. **Quality metrics:** Validar resolución, bitrate, aspecto ratio por plataforma

---

## 9. RESUMEN DE CAMBIOS NECESARIOS

| Archivo | Acción | Razón |
|---------|--------|-------|
| `skills/assembler.py` | Deprecate | Mover lógica a ComposedVideoAssembler |
| `skills/composed_video_assembler.py` | Crear | Nuevo core assembly con animación |
| `skills/animated_image_generator.py` | Crear | Generar imagenes con metadatos motion |
| `skills/advanced_subtitle_generator.py` | Crear | Subtítulos robustos y validados |
| `skills/video_animator.py` | Eliminar o integrar | Superficial; mover a assembler |
| `skills/script_generator.py` | Actualizar prompt | Agregar motion_hint a output |
| `pipelines/ugc_pipeline.py` | Actualizar steps | Usar nuevos skills; remover VideoAnimator |
| `api/models.py` | Sin cambios | Architecture works with existing models |

---

## 10. APÉNDICE: Problemas específicos del código actual

### A. assembler.py línea 33-43: _write_srt() sin validación

```python
def _write_srt(words: list[dict], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        chunk_size = 8
        chunks = [words[i:i + chunk_size] for i in range(0, len(words), chunk_size)]
        # ← NO VALIDA: ¿words vacío? ¿timings negativos? ¿duplicados?
        for idx, chunk in enumerate(chunks, 1):
            start = chunk[0]["start"]
            end = chunk[-1]["end"]
            # ← NO VALIDA: start >= end?
```

**Fix:**
```python
def _write_srt(words: list[dict], path: str) -> dict:
    """Retorna metadata de validación."""
    if not words:
        return {"errors": ["No words to write"], "count": 0}
    
    errors = []
    for word in words:
        if "start" not in word or "end" not in word:
            errors.append(f"Missing timing: {word}")
        elif word["start"] > word["end"]:
            errors.append(f"Invalid timing: {word['start']} > {word['end']}")
    
    if errors:
        return {"errors": errors, "count": 0}
    
    # ... escribir SRT
    return {"errors": [], "count": len(chunks)}
```

### B. video_animator.py línea 37: GOOGLE_VEO_API_KEY nunca usado

```python
if not settings.google_veo_api_key:
    await self.emit("log", "GOOGLE_VEO_API_KEY no configurada")
    return SkillResult(status="skipped")
```

La variable se verifica pero **nunca se envía a Google Veo API**. Solo se envía a Gemini.

**Arquitectura esperada vs realidad:**
- **Esperada:** Google Veo recibe imagen + motion type → genera video animado
- **Real:** Gemini identifica motion type → ffmpeg aplica filtro simple

### C. base_pipeline.py línea 135: Type narrowing insuficiente

```python
step.input_data = {k: v for k, v in input_data.items() if isinstance(v, (str, int, float, bool, list, dict, type(None)))}
```

Cuando se guardan inputs, se filtran tipos. Pero en `_get_step_output()` (línea 159) se retorna directamente sin tipo hints.

**Risk:** Outputs podrían ser corrupted en DB → siguiente step recibe None o dict vacío

---

**FIN DEL DOCUMENTO**

Generated: 2025-04-29 | Ver. 1.0
