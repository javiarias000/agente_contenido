# OpenAI Image Generation Guide

## Overview

OpenAI proporciona dos APIs para generación de imágenes:

### 1. **Image API** ✅ (Lo que usamos actualmente)
- Endpoints simples para generar y editar imágenes
- Mejor para casos de uso de una sola imagen
- Menos overhead que Responses API

### 2. **Responses API**
- Generación de imágenes como parte de conversaciones multi-turn
- Mejor para flujos iterativos
- Más complejo pero más poderoso

---

## Modelos Disponibles

### GPT Image Models

| Modelo | Estado | Notas |
|--------|--------|-------|
| **gpt-image-2** | ⭐ Último | Mejor calidad, requiere verificación de organización |
| gpt-image-1.5 | Anterior | Buen balance calidad/velocidad |
| gpt-image-1 | Anterior | Funcional pero más lento |
| gpt-image-1-mini | Anterior | Rápido pero menor calidad |

**Nota**: Todos requieren verificación de organización en https://platform.openai.com/settings/organization/general

---

## Image API - Endpoints

### 1. Generate (Crear imágenes)

```python
from openai import OpenAI
client = OpenAI()

result = client.images.generate(
    model="gpt-image-2",
    prompt="Your image description here",
    size="1024x1024",        # Resolución
    quality="hd",             # Calidad
    n=1,                      # Número de imágenes
    response_format="b64_json" # Formato base64
)

image_base64 = result.data[0].b64_json
```

### 2. Edit (Editar imágenes existentes)

```python
result = client.images.edit(
    model="gpt-image-2",
    image=open("original.png", "rb"),
    prompt="Cambios a realizar",
    size="1024x1024",
    n=1
)
```

### 3. Edit con Mask (Editar áreas específicas)

```python
result = client.images.edit(
    model="gpt-image-2",
    image=open("image.png", "rb"),
    mask=open("mask.png", "rb"),  # Área a editar
    prompt="Reemplazo para el área enmascarada",
    size="1024x1024"
)
```

---

## Opciones de Salida

### Size (Resoluciones)

```python
# Populares (cuadrado más rápido)
"1024x1024"   # Cuadrado
"1536x1024"   # Landscape
"1024x1536"   # Portrait
"2048x2048"   # 2K Cuadrado
"2048x1152"   # 2K Landscape
"3840x2160"   # 4K Landscape
"auto"        # Automático (default)
```

**Restricciones**:
- Max edge: 3840px
- Múltiplos de 16px
- Ratio max: 3:1
- Pixels totales: 655,360 - 8,294,400

### Quality (Calidad)

```python
quality="low"      # Rápido, borradores, thumbnails
quality="medium"   # Balance
quality="high"     # Mejor calidad, más lento
quality="auto"     # Automático (default)
```

### Format (Formato)

```python
response_format="b64_json"  # Base64 (default)
response_format="url"       # URL pública (temporal)

# Para JPEG/WebP
output_format="jpeg"
output_compression=50       # 0-100%
```

---

## Streaming (Parcial)

```python
stream = await client.images.generate(
    model="gpt-image-2",
    prompt="Your prompt",
    stream=True,
    partial_images=2  # Recibir 0-3 imágenes parciales
)

for event in stream:
    if event.type == "image_generation.partial_image":
        idx = event.partial_image_index
        image_base64 = event.b64_json
        # Procesar imagen parcial...
```

---

## Costos y Latencia

### GPT Image 2 - Precios por Output Token

| Quality | 1024x1024 | 1024x1536 | 1536x1024 |
|---------|-----------|-----------|-----------|
| Low     | $0.006    | $0.005    | $0.005    |
| Medium  | $0.053    | $0.041    | $0.041    |
| High    | $0.211    | $0.165    | $0.165    |

### Latencia

- Prompts simples: ~10-30 segundos
- Prompts complejos: hasta 2 minutos
- Streaming parcial: más rápido (feedback visual)

### Partial Images Cost

- Cada imagen parcial: +100 tokens de output

---

## Uso en el Proyecto - Mi Idea

### Pipeline Actual

```
ScriptGenerator (genera prompts)
    ↓
ImageGenerator (usa gpt-image-2)
    ├─ Colores: #D35400, #A84327, #5C2B17
    ├─ Size: 1024x1792 (TikTok vertical)
    ├─ Quality: "hd"
    └─ Response: base64
    ↓
ImageQualityImprover (mejora calidad)
    └─ Upscaling, brillo, contraste
```

### Ejemplo de Prompt Mejorado

```python
# Sin colores (ANTES)
prompt = "A laser cutting design in MDF"

# Con colores de marca (AHORA)
prompt = """
A laser cutting design in MDF with professional presentation.
Color palette: #D35400 (Orange), #A84327 (Brown), #5C2B17 (Dark Brown).
Use these brand colors prominently in the design.
Professional laser-cut precision, minimalist modern style.
Photorealistic, high quality, professional lighting.
"""
```

---

## Limitaciones Conocidas

| Limitación | Impacto | Solución |
|-----------|---------|----------|
| Texto en imágenes | Puede estar impreciso | Usar overlays de texto |
| Consistencia | Mismo personaje varía | Usar character_anchor detallado |
| Composición | Difícil control preciso | Prompts muy específicos |
| Latencia | Hasta 2 min en complejos | Usar quality="low" para drafts |
| No hay transparencia | gpt-image-2 no lo soporta | Usar backgrounds sólidos |

---

## Moderation (Content Policy)

```python
# Default: Standard filtering
moderation="auto"

# Less restrictive
moderation="low"
```

---

## Implementación en ImageGenerator

### Archivo: `skills/image_generator.py`

**Función clave**: `_build_image_prompt()`

```python
def _build_image_prompt(
    visual_description: str,
    character_anchor: str,
    style_notes: str,
    scene_index: int,
    brand_colors: list[str] | None = None,
    color_mood: str = "",
) -> str:
    parts = []
    if character_anchor:
        parts.append(f"Character: {character_anchor}")
    parts.append(visual_description)
    
    # NUEVO: Incluir colores de marca
    if brand_colors:
        colors_str = ", ".join(brand_colors)
        parts.append(f"Color palette: {colors_str}. Use these brand colors prominently")
    if color_mood:
        parts.append(f"Color mood: {color_mood}")
    
    parts.append("Photorealistic, high quality, professional lighting")
    return ". ".join(p.strip(". ") for p in parts)
```

**Configuración**:
- Model: `gpt-image-2` (con fallback a `dall-e-3`)
- Size: `1024x1792` (vertical para TikTok)
- Quality: `"hd"`
- Format: `"b64_json"`
- N: 1 (una imagen por escena)

---

## Troubleshooting

### Error: "insufficient_quota"
**Causa**: API key sin créditos  
**Solución**: Agregar créditos en https://platform.openai.com/account/billing/overview

### Error: "Organization not verified"
**Causa**: Organización no verificada para gpt-image-2  
**Solución**: Verificar en https://platform.openai.com/settings/organization/general

### Error: "Invalid size"
**Causa**: Resolución no válida  
**Solución**: Usar resoluciones válidas (múltiplos de 16, ratio max 3:1)

### Imagen lenta (>60s)
**Causa**: Prompt complejo o quality="high"  
**Solución**: Simplificar prompt o usar quality="low" para drafts

---

## Next Steps

1. ✅ **Implementar**: colores de marca en prompts
2. ✅ **Integrar**: ImageQualityImprover en pipeline
3. ⏳ **Verificar**: Organización en OpenAI
4. ⏳ **Cambiar a gpt-image-2**: cuando verificación esté lista
5. 📋 **Optimizar**: prompts basados en resultados reales

---

**Última actualización**: 29 de Abril de 2026  
**Modelo en uso**: `dall-e-3` (temporal)  
**Modelo objetivo**: `gpt-image-2` (cuando se verifique)
