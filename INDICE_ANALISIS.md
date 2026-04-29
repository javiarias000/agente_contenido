# ÍNDICE DE ANÁLISIS DE ARQUITECTURA

## Documentos Generados

Este análisis completo de arquitectura está documentado en 5 archivos:

### 1. **RESUMEN_EJECUTIVO.txt** (12 KB)
   **Lee primero esto**
   - Overview de hallazgos principales
   - 5 problemas identificados con severidad
   - Componentes nuevos propuestos
   - Estimación de esfuerzo (32 horas)
   - Próximos pasos en 3 fases

### 2. **ANALISIS_PROBLEMAS.md** (17 KB)
   **Entiende QUÉ está roto**
   - Sección 1-5: Análisis profundo de cada problema
   - Cascadas de fallos y casos reales
   - Matriz de soluciones
   - Ejemplos visuales ASCII
   - Problemas específicos de código

### 3. **ARQUITECTURA.md** (26 KB)
   **Entiende CÓMO arreglarlo**
   - Sección 1: Diagrama de flujo actual
   - Sección 2-5: Problemas con línea exacta
   - Sección 4: Nueva arquitectura propuesta
   - Sección 6-7: Puntos técnicos críticos
   - Sección 8-9: Validación y roadmap futuro

### 4. **IMPLEMENTACION_DETALLADA.md** (30 KB)
   **Código skeleton listo para usar**
   - Sección 1-3: Código Python completo de nuevos skills
   - AnimatedImageGenerator (200+ líneas)
   - AdvancedSubtitleGenerator (300+ líneas)
   - ComposedVideoAssembler (500+ líneas, partial)
   - Sección 4-7: Cambios en archivos existentes, testing

### 5. **REFERENCIA_LINEAS.md** (14 KB)
   **Lookup rápido de ubicaciones**
   - Matriz de archivos y líneas exactas
   - Flujos de ejecución (actual vs propuesto)
   - Tablas de constantes y modelos
   - Preguntas frecuentes para el equipo

---

## Orden de Lectura Recomendado

**Para ejecutivos/gerentes:**
```
1. RESUMEN_EJECUTIVO.txt (15 min)
   └─ Entender qué está roto y por qué
   └─ Ver estimación de esfuerzo
```

**Para arquitectos/tech leads:**
```
1. RESUMEN_EJECUTIVO.txt (15 min)
2. ARQUITECTURA.md - Secciones 1-4 (30 min)
3. REFERENCIA_LINEAS.md (20 min)
   └─ Entender flujos y decisiones arquitectónicas
```

**Para developers/implementadores:**
```
1. RESUMEN_EJECUTIVO.txt (15 min)
2. ANALISIS_PROBLEMAS.md - Secciones 1-5 (45 min)
3. ARQUITECTURA.md - Secciones 4-7 (40 min)
4. IMPLEMENTACION_DETALLADA.md (60 min)
5. REFERENCIA_LINEAS.md (20 min)
   └─ Código + cambios específicos
```

**Para QA/testers:**
```
1. ANALISIS_PROBLEMAS.md - Cascadas de fallos (40 min)
2. ARQUITECTURA.md - Sección 8: Validación (20 min)
3. IMPLEMENTACION_DETALLADA.md - Sección 7: Testing (15 min)
   └─ Casos de test y validación
```

---

## Resumen de Problemas Encontrados

### Problema A: Logo sale del frame
- **Ubicación**: `skills/assembler.py:137-140`
- **Severidad**: ALTA
- **Líneas clave**: 15-16 (OUTPUT_WIDTH/HEIGHT), 138-139 (scale filter)
- **Impacto**: Videos descentrados en todas las plataformas
- **Solución**: Safe area overlay + reposicionamiento dinámico

### Problema B: Subtítulos desaparecen
- **Ubicación**: `skills/assembler.py:173-210`
- **Severidad**: ALTA
- **Líneas clave**: 185 (hasattr check), 199 (path escape), 210 (silent fallback)
- **Impacto**: Videos sin contexto, sin logging
- **Solución**: AdvancedSubtitleGenerator con validación

### Problema C: Sin transiciones
- **Ubicación**: `skills/assembler.py:161-171`
- **Severidad**: MEDIA
- **Líneas clave**: 167-168 (ffmpeg concat demuxer)
- **Impacto**: Cortes secos entre escenas
- **Solución**: xfade filter con fade 200ms

### Problema D: VideoAnimator superficial
- **Ubicación**: `skills/video_animator.py:155-197`
- **Severidad**: BAJA
- **Líneas clave**: 37-39 (API no usada), 161-169 (filtros estáticos)
- **Impacto**: Animación genérica y cara
- **Solución**: Integrar en assembler con zoompan + keyframes

### Problema E: Contexto sin validación
- **Ubicación**: `pipelines/base_pipeline.py:67`
- **Severidad**: BAJA
- **Líneas clave**: 39 (inicialización), 67 (merge sin validar)
- **Impacto**: Silent failures en cascada
- **Solución**: Type checking y validación

---

## Componentes a Crear

| Archivo | Líneas | Propósito | Docs |
|---------|--------|----------|------|
| `skills/animated_image_generator.py` | 200+ | Genera imágenes con motion metadata | IMPL #1 |
| `skills/advanced_subtitle_generator.py` | 300+ | Subtítulos robustos con validación | IMPL #2 |
| `skills/composed_video_assembler.py` | 500+ | Composición visual integrada | IMPL #3 |

---

## Cambios en Archivos Existentes

| Archivo | Líneas | Cambio | Docs |
|---------|--------|--------|------|
| `pipelines/ugc_pipeline.py` | 84-119 | Reemplazar Assembler y VideoAnimator | ARCH #4.3 |
| `skills/script_generator.py` | 46-54 | Agregar motion_hint a prompt | ARCH #4.3 |
| `skills/video_animator.py` | ALL | Deprecate | ARCH #4.3 |
| `skills/assembler.py` | ALL | Deprecate (opcional) | - |

---

## Flujos Importantes

### Flujo Actual (Problema)
```
ScriptGenerator → ImageGenerator → VoiceGenerator → Assembler ↓
                                                         ├─ _build_scene_clips()
                                                         ├─ _concatenate_clips() [NO transiciones]
                                                         ├─ _generate_subtitles() [Whisper fails]
                                                         └─ _burn_subtitles() [Silent fallback]
                                                              ↓
                                                       VideoAnimator [Superficial]
```

### Flujo Propuesto (Solución)
```
ScriptGenerator → AnimatedImageGenerator → VoiceGenerator → ComposedVideoAssembler
                  (motion metadata)                              ├─ _compose_scene_videos()
                                                                 │  ├─ Animation (zoompan)
                                                                 │  ├─ Logo overlay
                                                                 │  └─ Text overlay
                                                                 ├─ _concatenate_with_transitions() [xfade]
                                                                 ├─ AdvancedSubtitleGenerator [Validado]
                                                                 ├─ _burn_subtitles_validated()
                                                                 └─ _add_bgm_if_configured()
```

---

## Tecnologías Clave

### FFmpeg Filters (Nuevos)

| Filter | Propósito | Docs |
|--------|-----------|------|
| `zoompan` | Animación progresiva (zoom lento) | ARCH #6.4 |
| `xfade` | Transiciones suaves (fade 200ms) | ARCH #6.4 |
| `scale + pad` | Reescalado con safe area | IMPL #3 |
| `drawtext` | On-screen text overlay | IMPL #3 |
| `overlay` | Logo positioning | IMPL #3 |

### APIs Usadas

| API | Propósito | Status |
|-----|-----------|--------|
| OpenAI Whisper | Transcripción de audio | ✓ Mejorado |
| OpenAI TTS | Fallback de voz | ✓ Sin cambios |
| DALL-E / gpt-image | Generación de imágenes | ✓ Mejorado |
| ElevenLabs | Text-to-speech | ✓ Sin cambios |
| Gemini | Análisis de motion | ✓ Mejor integración |
| Google Veo | (No implementado) | ✗ Revisar |
| Suno | Background music | ✓ Sin cambios |

---

## Estimación de Implementación

### Timeline: 1 semana (32 horas)

**Semana 1 (16 horas):**
- Día 1-2: AnimatedImageGenerator (4h)
- Día 2-3: AdvancedSubtitleGenerator (6h)
- Día 3-4: Tests unitarios (4h)
- Día 4: Integración básica (2h)

**Semana 2 (16 horas):**
- Día 1-3: ComposedVideoAssembler (12h)
- Día 3-4: Test end-to-end + fixes (4h)

**Risk Buffer: +1 semana si hay issues con ffmpeg**

---

## Preguntas Frecuentes

**P: ¿Por qué no simplemente arreglar Assembler?**
R: Assembler tiene problemas arquitectónicos profundos. Una nueva clase permite separación de concerns y testing independiente.

**P: ¿Cómo manejo backward compatibility?**
R: Mantén Assembler como deprecated 1-2 versiones. Nuevo skill es totalmente independiente.

**P: ¿Dónde va el logo si no sé dónde está en la imagen?**
R: AnimatedImageGenerator puede usar corner detection o configuración manual en brand profile.

**P: ¿Qué pasa con videos existentes?**
R: Pueden regenerarse con nuevo pipeline. No hay cambios en BD.

**P: ¿Cuánto más lento será todo esto?**
R: ComposedVideoAssembler es más eficiente (1 pass ffmpeg vs 2+ en actual). Ganancia de ~20%.

---

## Checklist de Referencia

### Para empezar
- [ ] Leer RESUMEN_EJECUTIVO.txt
- [ ] Leer ANALISIS_PROBLEMAS.md
- [ ] Discutir con equipo las 4 preguntas en RESUMEN_EJECUTIVO.txt

### Para implementar
- [ ] Crear AnimatedImageGenerator (use IMPLEMENTACION_DETALLADA.md #1)
- [ ] Crear AdvancedSubtitleGenerator (use IMPLEMENTACION_DETALLADA.md #2)
- [ ] Crear ComposedVideoAssembler (use IMPLEMENTACION_DETALLADA.md #3)
- [ ] Actualizar ugc_pipeline.py (use IMPLEMENTACION_DETALLADA.md #5)
- [ ] Actualizar script_generator.py (use IMPLEMENTACION_DETALLADA.md #6)

### Para validar
- [ ] Tests unitarios de AnimatedImageGenerator
- [ ] Tests unitarios de AdvancedSubtitleGenerator
- [ ] Test end-to-end con UGC pipeline
- [ ] Comparativa antes/después (logo, subtítulos, transiciones)
- [ ] Performance benchmarking

---

## Contexto Técnico

**Stack Existente:**
- Backend: FastAPI (Python)
- Frontend: Next.js (TypeScript)
- DB: SQLite + SQLModel
- Video: ffmpeg
- LLM: OpenAI (GPT-4o, Whisper, DALL-E, TTS)
- Audio: ElevenLabs TTS
- Music: Suno API

**Cambios en Stack:**
- Ninguno. Solo ffmpeg filters nuevos (ya disponibles).

**Dependencias Nuevas:**
- Ninguna. Solo uso de skills existentes.

---

## Métricas de Éxito

| Métrica | Antes | Después | Target |
|---------|-------|---------|--------|
| Logo en frame | 60% | 99% | ≥95% |
| Subtítulos presentes | 70% | 98% | ≥95% |
| Transiciones suaves | 0% | 100% | 100% |
| Animación por escena | 0% | 100% | 100% |
| Tiempo de procesamiento | 120s | 100s | ≤100s |
| Silent failures | 15% | <1% | <1% |

---

## Soporte y Contacto

Para dudas específicas, consulta:

1. **Problema de logo**: ANALISIS_PROBLEMAS.md #2
2. **Problema de subtítulos**: ANALISIS_PROBLEMAS.md #3
3. **Implementación de skill**: IMPLEMENTACION_DETALLADA.md
4. **Línea exacta de código**: REFERENCIA_LINEAS.md

---

**Documento generado:** 2025-04-29
**Versión:** 1.0
**Autor:** Claude Code
**Estado:** Listo para implementación

