# ANÁLISIS DETALLADO DE PROBLEMAS

## 1. MATRIZ DE IMPACTO: Problemas vs Arquitectura

| Problema | Severidad | Ubicación | Impacto en UX | Solución |
|----------|-----------|-----------|---------------|----------|
| Logo fuera de frame | ALTO | `assembler.py:137-140` | Videos descentrados | Reescalado dinámico + safe area |
| Subtítulos desaparecen | ALTO | `assembler.py:192-210` | Video sin contexto | Validación de SRT + error logging |
| Sin transiciones | MEDIO | `assembler.py:161-171` | Cortes secos | xfade filter en concat |
| VideoAnimator superficial | BAJO | `video_animator.py:155-197` | Animación plana | Integrar en Assembler con keyframes |
| Contexto sin validación | BAJO | `base_pipeline.py:67` | Silent failures | Type checking en outputs |

---

## 2. PROBLEMA A: Logo sale del cuadro

### 2.1 Raíz técnica

**Archivo:** `skills/assembler.py`, líneas 137-140

```python
vf = (
    f"scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:force_original_aspect_ratio=decrease,"
    f"pad={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:(ow-iw)/2:(oh-ih)/2"
)
```

**Desglose:**
- `OUTPUT_WIDTH=1080, OUTPUT_HEIGHT=1920` (línea 15-16)
- `force_original_aspect_ratio=decrease` → escala imagen HACIA ABAJO mantieniendo ratio
- `pad=1080:1920:(ow-iw)/2:(oh-ih)/2` → centra la imagen escalada en canvas negro

**Ejemplo:**
```
Imagen DALL-E generada: 1024x1792 (9:16)
    ↓ scale=1080:1920:decrease
Resultado: 1088x1920 (NO cabe en 1080)
    ↓ Se crop automáticamente a 1080x1920
Problema: Logo en esquina se cae fuera del crop
```

### 2.2 Problemas secundarios

1. **No hay safe area:** Márgenes para redes sociales (15% en bordes) ignorados
2. **No hay posicionamiento dinámico:** Logo siempre centrado, nunca en corner
3. **Sin metadata de logo:** No se sabe dónde está el logo en la imagen

### 2.3 Casos de fallo reales

```
Caso 1: Logo en bottom-right de imagen DALL-E
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃         Imagen (1088x1920)    ┃
┃ ┌──────────────────────────┐  ┃
┃ │                          │  ┃
┃ │                          │  ┃
┃ │                       [L]│  ← Logo sale aquí
┃ └──────────────────────────┘  ┃
┃←→ 4px extra en cada lado      ┃
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          ↓ crop 1080x1920
┌─────────────────────────────┐
│                             │
│                             │
│                          ◯  │ ← Logo cortado / fuera
└─────────────────────────────┘
```

### 2.4 Impacto en conversión

- Logo descentrado → menos professional
- Logo parcial → marca débil
- Afecta todas las plataformas (TikTok, Instagram, YouTube)

---

## 3. PROBLEMA B: Desaparecen subtítulos

### 3.1 Flujo de generación actual

```python
# assembler.py línea 82-89
await self.emit("progress", "Generando subtítulos con Whisper...")
srt_path = os.path.join(video_dir, f"{self.run_id}.srt")
await self._generate_subtitles(full_voiceover_path, srt_path)  # ← línea 84

# assembler.py línea 173-190 (_generate_subtitles)
with open(audio_path, "rb") as f:
    transcript = await self.client.audio.transcriptions.create(
        model=settings.whisper_model,
        file=f,
        response_format="verbose_json",
        timestamp_granularities=["word"],  # ← line 182
    )
words = []
if hasattr(transcript, "words") and transcript.words:  # ← line 185
    words = [{"word": w.word, "start": w.start, "end": w.end} for w in transcript.words]
elif hasattr(transcript, "segments") and transcript.segments:  # ← line 187
    for seg in transcript.segments:
        words.append({"word": seg.text.strip(), "start": seg.start, "end": seg.end})
_write_srt(words, srt_path)  # ← line 190

# assembler.py línea 192-210 (_burn_subtitles)
result = subprocess.run(
    ["ffmpeg", "-y", "-i", input_path,
     "-vf", f"subtitles='{abs_srt}':force_style='...'",
     "-c:a", "copy", output_path],
    capture_output=True, timeout=300,
)
if result.returncode != 0 or not os.path.exists(output_path):  # ← line 208
    # Fallback: copy without subtitles
    shutil.copy(input_path, output_path)  # ← line 210 ← PROBLEMA!
```

### 3.2 Puntos de fallo múltiples

#### Fallo 1: Whisper no devuelve palabras con timing

**Causas:**
- Audio muy corto (< 0.5 segundos)
- Audio muy rápido (conversación acelerada)
- Modelo Whisper incapaz de extraer word-level timestamps

**Symptoma:**
```python
# Línea 185: hasattr(transcript, "words") es False
# → Cae a línea 187: segments
# → segments devuelve timing de SEGMENTO (3-5 segundos)
# → SRT tiene pocas líneas gigantes
# → Video se ve con poco texto a la vez
```

**Código vulnerable:**
```python
if hasattr(transcript, "words") and transcript.words:  # ← FALSO
    words = [...]  # No se ejecuta
elif hasattr(transcript, "segments") and transcript.segments:  # ← VERDADERO
    for seg in transcript.segments:  # Solo 2-3 segmentos
        words.append({...})  # SRT vacío o con pocas líneas
```

#### Fallo 2: Path escaping incorrecto (Windows vs Linux)

**Código línea 199:**
```python
abs_srt = os.path.abspath(srt_path).replace("\\", "/").replace(":", "\\:")
```

**En Windows:**
- Path: `C:\outputs\video\run123.srt`
- `replace("\\", "/")` → `C:/outputs/video/run123.srt`
- `replace(":", "\\:")` → `C\:/outputs/video/run123.srt` ← INCORRECTO

**En Linux:**
- Path: `/outputs/video/run123.srt`
- No hay `:` → no cambia
- Funciona bien

**Pero ffmpeg en Linux con paths incorrectos:**
```bash
ffmpeg -i video.mp4 -vf "subtitles='C\:/outputs/run123.srt'" output.mp4
# ffmpeg intenta abrir "C:/outputs/run123.srt" → NOT FOUND en /C/outputs/
```

#### Fallo 3: Silent fallback sin logging

**Código línea 208-210:**
```python
if result.returncode != 0 or not os.path.exists(output_path):
    # Fallback: copy without subtitles
    shutil.copy(input_path, output_path)
```

**Problema:**
- Si ffmpeg falla, copia video SIN avisar
- Usuario ve video sin subtítulos sin saber por qué
- No hay log de qué falló
- No hay retry o fix

**Usuario experience:**
```
1. User lanza pipeline
2. "Generando subtítulos..." 
3. Video generado
4. SIN SUBTÍTULOS
5. User: "¿Por qué no hay subtítulos?" 
   → No hay forma de saber qué pasó
```

#### Fallo 4: SRT vacío o inválido

**_write_srt() (línea 33-43):**
```python
def _write_srt(words: list[dict], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        chunk_size = 8
        chunks = [words[i:i + chunk_size] for i in range(0, len(words), chunk_size)]
        # ← Si words vacío → chunks vacío → SRT vacío!
        for idx, chunk in enumerate(chunks, 1):
            start = chunk[0]["start"]  # ← IndexError si chunk vacío!
```

Si `words=[]`:
- `chunks=[]`
- Loop no ejecuta
- SRT vacío (0 bytes)
- `_burn_subtitles()` línea 196: `if not os.path.exists(srt_path) or os.path.getsize(srt_path) == 0:`
- Copia video sin subtítulos

### 3.3 Cascada de fallos

```
Audio corto o rápido
    ↓
Whisper sin word-level timestamps
    ↓
transcript.words vacío
    ↓
Cae a transcript.segments
    ↓
SRT con pocas líneas o mal timing
    ↓
ffmpeg intenta grabar subtítulos
    ↓
ffmpeg error (path incorrecto o SRT inválido)
    ↓
Silent copy sin subtítulos
    ↓
Usuario ve video sin subtítulos (SIN SABER POR QUÉ)
```

---

## 4. PROBLEMA C: Concatenación sin transiciones

### 4.1 Flujo actual

**Código línea 161-171 (assembler.py):**

```python
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
```

**FFmpeg concat demuxer (línea 167-168):**
```bash
ffmpeg -f concat -i filelist.txt output.mp4
```

**Comportamiento:**
- Demuxer concatena clips frame-by-frame
- SIN transiciones (corte seco instantáneo)
- Tiempo de entrada == tiempo de salida anterior (no hay overlay)

### 4.2 Impacto visual

```
Escena 1 (3 seg)        Escena 2 (3 seg)
━━━━━━━━━━━━━━         ━━━━━━━━━━━━━━
  [Video Prod]           [Video CTA]
  ...frame 90...         ...frame 1...
  │ │ ↓ CORTE SECO ↓ │ │
  └─┴─────────────────┴─┘
Muy abrupto, poco professional
```

**Con transición (fade 200ms):**
```
Escena 1                 Escena 2
━━━━━━━━━━━━━━         ━━━━━━━━━━━━━━
  [Video Prod]      [Video CTA]
  ...frame 90...↓
                  Fade
                  (200ms)
              ↓...frame 1...
Suave, professional
```

### 4.3 Solución técnica

Usar ffmpeg filter `xfade`:

```bash
ffmpeg -i clip1.mp4 -i clip2.mp4 \
  -filter_complex "[0][1]xfade=transition=fade:duration=0.2:offset=2.8[v]; [0:a][1:a]acrossfade=d=0.2[a]" \
  -map "[v]:v" -map "[a]:a" output.mp4
```

---

## 5. PROBLEMA D: VideoAnimator es superficial

### 5.1 Análisis del código

**Ubicación:** `skills/video_animator.py`, línea 155-197

```python
async def _apply_motion_with_ffmpeg(self, input_video: str, output_video: str, motion_type: str) -> bool:
    ffmpeg_filters = {
        "zoom_in": "scale=iw*1.2:ih*1.2,crop=iw:ih",           # ← Escala 1.2x y crop
        "zoom_out": "scale=iw*0.8:ih*0.8,pad=iw:ih:...:black", # ← Escala 0.8x y pad
        "pan_left": "crop=iw*0.9:ih:0:0",                      # ← Crop parte izquierda
        # ...
    }
    
    filter_str = ffmpeg_filters.get(motion_type, ffmpeg_filters["zoom_in"])
    
    cmd = [
        "ffmpeg", "-y", "-i", input_video,
        "-vf", f"format=yuv420p,{filter_str}",  # ← Aplica filter estaticamente
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac",
        output_video
    ]
```

### 5.2 Problemas

#### Problema 1: Filtros estáticos

```
zoom_in: "scale=iw*1.2:ih*1.2,crop=iw:ih"
┌─────────────────────────────┐
│  Imagen ORIGINAL (1080x1920)│
│  ↓ scale 1.2x (1296x2304)   │
│  ↓ crop (1080x1920)         │
│                             │
│  → Resultado: ZOOM 1.2x     │ ← Estático, todo el video
│    a través de TODO el clip │
└─────────────────────────────┘

Frame 1 (t=0s)    Frame 30 (t=1s)    Frame 90 (t=3s)
zoom=1.2x         zoom=1.2x          zoom=1.2x
              ↑ MISMO ZOOM en todos!
```

**Vs. lo que se espera:**
```
Frame 1 (t=0s)    Frame 30 (t=1s)    Frame 90 (t=3s)
zoom=1.0x         zoom=1.1x          zoom=1.2x
              ↑ Zoom progresivo suave
```

#### Problema 2: Google Veo API no se usa

**Código línea 37-39:**
```python
if not settings.google_veo_api_key:
    await self.emit("log", "GOOGLE_VEO_API_KEY no configurada")
    return SkillResult(status="skipped")
```

**Realidad:**
- Se verifica si `GOOGLE_VEO_API_KEY` existe
- Pero **nunca se llama a Google Veo API**
- Solo se usa Gemini para análisis (línea 126-147)
- El nombre "VideoAnimator" con "Google Veo" (línea 17) es engañoso

**Flujo real:**
```
1. _analyze_image_for_motion() (línea 91)
   → Gemini API (línea 126)
   → Retorna motion_type: "zoom_in" | "pan_left" | etc.

2. _apply_motion_with_ffmpeg() (línea 155)
   → ffmpeg static filter
   → NO Google Veo
```

#### Problema 3: Análisis superficial de Gemini

**Código línea 108-120:**
```python
"text": """Analiza esta imagen y recomienda UN SOLO tipo de movimiento de cámara para animarla.

RESPONDE SOLO con UNA de estas opciones (sin explicación):
- zoom_in: acercamiento lento a la imagen
- zoom_out: alejamiento lento de la imagen
- pan_left: movimiento horizontal a la izquierda
- ...

Elige la que sea MÁS apropiada para esta imagen."""
```

**Problemas:**
- Gemini elige tipo de movimiento, pero **no profundidad**
  - Ej: "zoom_in" → pero ¿1.1x? ¿1.5x? ¿2.0x?
- No elige target
  - Ej: ¿zoom hacia cara? ¿hacia producto? ¿hacia centro?
- No elige velocidad
  - Ej: ¿zoom en 1 segundo? ¿en 3 segundos?

**Resultado:** Animación genérica, no optimizada para contenido

#### Problema 4: Post-processing anima TODO el video

**Ubicación:** `ugc_pipeline.py` línea 114-118

```python
StepDefinition(
    name="video_assemble",
    skill_class=Assembler,
    skill_kwargs={},
),
StepDefinition(
    name="video_animate",
    skill_class=VideoAnimator,  # ← Último step
    skill_kwargs={},
),
```

**Problema:**
- VideoAnimator recibe VIDEO CONCATENADO
- Aplica MISMO filtro a TODO el video
- Resultado: zoom_in en toda la duración (3+3+3 = 9 segundos)
- No hay animación POR ESCENA

**Ejemplo:**
```
Escena 1 (3s): zoom_in
┌────────────────┐
│ zoom: 1.0 → 1.2│  ← Zoom lento
└────────────────┘

Escena 2 (3s): zoom_in  (CONTINUACIÓN del zoom anterior)
┌────────────────┐
│ zoom: 1.2 → 1.4│  ← Zoom continúa desde 1.2
└────────────────┘

Escena 3 (3s): zoom_in  (CONTINUACIÓN)
┌────────────────┐
│ zoom: 1.4 → 1.6│  ← Zoom continúa desde 1.4
└────────────────┘

Resultado: Zoom progresivo en TODO el video
Esperado: Zoom RESET en cada escena
```

---

## 6. PROBLEMA E: Contexto sin validación

### 6.1 Código

**`base_pipeline.py` línea 36-79:**

```python
async def execute(self, inputs: dict[str, Any], interactive: bool = False) -> dict[str, Any]:
    steps = self.build_steps(inputs)
    total = len(steps)
    context: dict[str, Any] = {**inputs}  # ← línea 39: context inicial
    
    for idx, step_def in enumerate(steps):
        # ...
        skill = step_def.skill_class(
            event_bus=self.event_bus,
            run_id=self.run_id,
            step_index=idx,
            **step_def.skill_kwargs,
        )
        result = await skill.run(context, interactive=interactive)  # ← línea 66
        context.update(result.outputs)  # ← línea 67: ACUMULA outputs
        # ...
```

**Problema línea 67:**
```python
context.update(result.outputs)
```

Sin validación:
- Si `result.outputs` tiene rutas inválidas → siguiente step falla silenciosamente
- Si `result.outputs` vacío → contexto no cambia
- Si tipos incorrectos → error más adelante

### 6.2 Ejemplo de fallo en cascada

```
ScriptGenerator
  ↓ outputs: {"script": {...}, "scenes": [...]}
  ↓ context.update() → OK

ImageGenerator
  ↓ outputs: {"image_paths": ["/path/1.png", "/path/2.png"]}
  ↓ context.update() → OK

VoiceGenerator
  ↓ outputs: {"audio_paths": [], "full_voiceover_path": "/path/audio.mp3"}
  ↓ context.update() → OK (pero audio_paths vacío!)

Assembler
  ↓ inputs = context
  ↓ audio_paths = [] ← de VoiceGenerator
  ↓ No valida: if not audio_paths: raise ValueError(...)
  ↓ Silenciosamente trata [] como "sin audio"
  ↓ Video sin audio
  ↓ Subtítulos sin timing
  ↓ Usuario: "¿Por qué sin audio?"
```

---

## 7. MATRIZ DE SOLUCIONES

| Problema | Causa | Solución | Archivo | Líneas |
|----------|-------|----------|---------|--------|
| Logo fuera | scale=decrease + crop | Safe area + overlay | composed_video_assembler.py | NEW |
| Subtítulos desaparecen | Multiple failures | Validación + logging | advanced_subtitle_generator.py | NEW |
| Sin transiciones | Concat demuxer | xfade filter | composed_video_assembler.py | NEW |
| Animación superficial | Filtros estáticos | zoompan + keyframes | composed_video_assembler.py | NEW |
| Google Veo no usado | Código incompleto | Integrar o remover | Remover video_animator.py | DEPRECATED |
| Contexto no validado | No type checking | Validar outputs | base_pipeline.py | 67 |

---

## 8. ESTIMACIÓN DE ESFUERZO

| Tarea | Horas | Riesgo |
|-------|-------|--------|
| AnimatedImageGenerator | 4 | BAJO |
| AdvancedSubtitleGenerator | 6 | MEDIO (Whisper quirks) |
| ComposedVideoAssembler | 12 | ALTO (ffmpeg complexity) |
| Integración en ugc_pipeline | 2 | BAJO |
| Testing completo | 8 | MEDIO |
| **Total** | **32** | - |

**Timeline:** ~1 semana (con 6-8 horas/día)

---

**Fin del análisis. Ver ARQUITECTURA.md para la propuesta de solución completa.**

