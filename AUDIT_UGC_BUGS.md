# 🔍 AUDITORÍA CRÍTICA: Pipeline UGC - Bugs & Issues

**Fecha**: 29 Abril 2026  
**Estado**: Revisión de código exhaustiva  
**Objetivo**: Identificar problemas antes de producción con Mi Idea

---

## 🚨 BUGS CRÍTICOS (ALTO IMPACTO)

### BUG #1: Pan effects usan hardcoded values - Causa distorsión visual
**Ubicación**: `skills/composed_video_assembler.py`, líneas 233-238  
**Severidad**: 🔴 CRÍTICO  
**Impacto**: Los efectos pan_left y pan_right generan distorsión porque usan valores float en ffmpeg

```python
# ❌ MALO - Valores float en ffmpeg (espera int)
return f"crop={crop_w}:{OUTPUT_HEIGHT}:{OUTPUT_WIDTH*0.05}:0,..."
# OUTPUT_WIDTH*0.05 = 54.0 (float), ffmpeg espera int
```

**Solución requerida:**
```python
# ✅ CORRECTO
offset = int(OUTPUT_WIDTH * 0.05)
return f"crop={crop_w}:{OUTPUT_HEIGHT}:{offset}:0,pad={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:{offset}:0"
```

---

### BUG #2: Audio path validation incompleta en assembler
**Ubicación**: `skills/composed_video_assembler.py`, línea 166  
**Severidad**: 🟠 ALTO  
**Problema**: Si `audio_path` es string vacío (""), `os.path.exists("")` retorna False pero el código no lo maneja

```python
# ❌ PROBLEMA
duration = _get_audio_duration(audio_path) if os.path.exists(audio_path) else 3.0
# Si audio_path = "", duration = 3.0 
# Pero scene sin audio + 3s default = contenido fuera de sincronización
```

**Impacto**: Videos con duraciones incorrectas, subtítulos desalineados

---

### BUG #3: SRT chunks que sobrepasen audio duration
**Ubicación**: `skills/advanced_subtitle_generator.py`, líneas 45-51  
**Severidad**: 🟠 ALTO  
**Problema**: Los subtítulos pueden ir más allá de la duración del audio

```python
# El problema: no hay validación de duración máxima
for idx, chunk in enumerate(chunks, 1):
    start = chunk[0].get("start", 0.0)
    end = chunk[-1].get("end", start + min_duration)
    
    # ❌ Si end > duration_audio, el SRT queda fuera de rango
```

**Causa**: Si el audio tiene 60s pero los timestamps llegan a 65s, ffmpeg no sabe qué hacer

---

### BUG #4: Voice Generator - Fallback silencioso a OpenAI sin notificación
**Ubicación**: `skills/voice_generator.py`, líneas 79-85  
**Severidad**: 🟡 MEDIO  
**Problema**: Si ElevenLabs falla, fallback a OpenAI SIN validar que el API key es válido

```python
async def _synthesize(self, text: str, voice_id: str, output_path: str) -> None:
    try:
        await self._synthesize_elevenlabs(text, voice_id, output_path)
    except Exception as e:
        # ❌ Fallback ciego - OpenAI podría fallar también
        await self._synthesize_openai(text, output_path)
```

**Riesgo**: Si ambas APIs fallan, el audio no se genera pero el pipeline continúa sin error

---

## ⚠️ BUGS MODERADOS (MEDIO IMPACTO)

### BUG #5: Image paths sin validación antes de pasar al assembler
**Ubicación**: `skills/animated_image_generator.py`, línea 96  
**Severidad**: 🟡 MEDIO  
**Problema**: No valida que las imágenes generadas existan antes de enviarlas al assembler

```python
# ❌ Solo retorna paths, sin chequear si existen
return SkillResult(
    status="completed",
    outputs={
        "image_paths": image_paths,  # Podrían no existir!
        "motion_metadata": motion_metadata,
    }
)
```

**Impacto**: Si ImageGenerator falla silenciosamente, assembler intenta procesar imágenes inexistentes

---

### BUG #6: Cleanup del concat_path puede dejar huérfano el subtitled_path
**Ubicación**: `skills/composed_video_assembler.py`, líneas 122-127  
**Severidad**: 🟡 MEDIO  
**Lógica compleja**: Si subtitled_path falla, concat_path se elimina pero subtitled_path no existe

```python
# Línea 111-112
self._burn_subtitles(concat_path, srt_path, subtitled_path)
if os.path.exists(subtitled_path):
    final_path = subtitled_path

# Línea 122-127
if final_path != concat_path:
    try:
        os.remove(concat_path)  # ❌ Se borra aunque subtitled no exista
    except Exception:
        pass
```

---

### BUG #7: Motion metadata puede estar None o incompleto
**Ubicación**: `skills/composed_video_assembler.py`, línea 170-171  
**Severidad**: 🟡 MEDIO  
**Problema**: No valida que motion_metadata tenga todos los items esperados

```python
motion = None
if motion_metadata and i < len(motion_metadata):
    motion = motion_metadata[i]
    # ❌ No valida que motion tenga "motion_type" key
```

---

## 📋 BUGS MENORES (BAJO IMPACTO)

### BUG #8: SRT numbering issue si hay chunks vacías
**Ubicación**: `skills/advanced_subtitle_generator.py`, línea 58  
**Severidad**: 🟢 BAJO  
**Problema**: Si una chunk tiene text vacío, el contador `idx` se sigue incrementando pero la línea no se escribe

```python
if not text:
    continue  # ❌ Salta la línea pero idx sigue igual
    
f.write(f"{idx}\n")  # Número puede quedar fuera de secuencia
```

---

## 🔧 RESUMEN DE FIXES NECESARIOS

| # | Bug | Fix | Tiempo | Prioridad |
|---|-----|-----|--------|-----------|
| 1 | Pan effects float values | Convertir a int | 10 min | 🔴 CRÍTICO |
| 2 | Audio path validation | Validar antes | 15 min | 🔴 CRÍTICO |
| 3 | SRT duration overflow | Clamp timestamps | 20 min | 🔴 CRÍTICO |
| 4 | Voice fallback ciego | Add error handling | 15 min | 🟠 ALTO |
| 5 | Image path validation | Check exists | 10 min | 🟠 ALTO |
| 6 | Concat cleanup lógica | Fix cleanup order | 15 min | 🟠 ALTO |
| 7 | Motion metadata validation | Add checks | 10 min | 🟡 MEDIO |
| 8 | SRT numbering | Fix counter logic | 5 min | 🟢 BAJO |

**Total estimado**: ~100 minutos

---

## ✅ BUGS YA RESUELTOS (desde commit 7e1c44c)

- ✅ Video deletion (final_path se borraba)
- ✅ FFmpeg double-scaling (optimizado)
- ✅ API key graceful fallback (subtitles skip si no hay key)

---

## 📊 RECOMENDACIÓN PARA MI IDEA

**No ejecutar en producción hasta resolver:**
1. BUG #1 - Pan effects distortion
2. BUG #2 - Audio validation
3. BUG #3 - SRT duration overflow

Los demás son importantes pero no bloquean el MVP.

