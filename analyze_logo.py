#!/usr/bin/env python
"""Analyze brand logos using Claude Vision to extract colors, typography, and design elements."""

import asyncio
import base64
import json
from pathlib import Path
from openai import AsyncOpenAI
from api.config import settings


async def encode_image(image_path: str) -> str:
    """Encode image to base64."""
    with open(image_path, "rb") as image_file:
        return base64.standard_b64encode(image_file.read()).decode("utf-8")


async def analyze_logo(image_path: str) -> dict:
    """Analyze a logo image using Claude Vision."""
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    # Determine media type
    ext = Path(image_path).suffix.lower()
    media_type_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }
    media_type = media_type_map.get(ext, "image/png")

    # Encode image
    image_data = await encode_image(image_path)

    prompt = """Analiza este logo de marca en detalle y proporciona:

1. **Colores principales** (lista cada color hexadecimal #XXXXXX):
   - Color primario
   - Color secundario
   - Color terciario
   - Cualquier otro color importante

2. **Tipografía** (si hay texto):
   - Estilo de fuente (sans-serif, serif, script, etc.)
   - Peso (light, regular, bold, etc.)
   - Características especiales

3. **Elementos visuales**:
   - Elementos geométricos (formas, líneas)
   - Símbolos o iconos
   - Composición y equilibrio
   - Estilo (moderno, clásico, minimalista, etc.)

4. **Paleta de colores general**:
   - Temperatura (cálida, fría, neutral)
   - Contraste (alto, medio, bajo)
   - Sentimiento que transmite

5. **Recomendaciones para contenido visual**:
   - Colores complementarios para usar en posts
   - Estilo de imágenes que combinarían bien
   - Mood/atmósfera a mantener

Sé específico con los códigos hex de colores. Responde en JSON."""

    message = await client.chat.completions.create(
        model="gpt-4o",
        max_tokens=2000,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{image_data}",
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }
        ],
    )

    # Parse response
    response_text = message.choices[0].message.content

    # Try to extract JSON
    try:
        # Find JSON in response
        start_idx = response_text.find("{")
        end_idx = response_text.rfind("}") + 1
        if start_idx >= 0 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx]
            return json.loads(json_str)
        else:
            return {"raw_analysis": response_text}
    except json.JSONDecodeError:
        return {"raw_analysis": response_text}


async def main():
    logo_dir = Path("/home/ubuntu/agente_contenido/brand_assets/mi-idea/logo")

    if not logo_dir.exists():
        print(f"❌ Logo directory not found: {logo_dir}")
        return

    logo_files = list(logo_dir.glob("*.png")) + list(logo_dir.glob("*.jpg")) + list(logo_dir.glob("*.jpeg"))

    if not logo_files:
        print(f"❌ No logo files found in {logo_dir}")
        return

    print(f"\n{'='*60}")
    print(f"Analyzing {len(logo_files)} logo(s) for 'Mi Idea'")
    print(f"{'='*60}\n")

    all_colors = set()
    analyses = {}

    for logo_file in logo_files:
        print(f"\n📸 Analyzing: {logo_file.name}")
        print(f"   Path: {logo_file}")

        try:
            analysis = await analyze_logo(str(logo_file))
            analyses[logo_file.name] = analysis

            # Extract colors
            colors = analysis.get("colores_principales", {})
            if isinstance(colors, dict):
                for color_type, color_code in colors.items():
                    if isinstance(color_code, str) and color_code.startswith("#"):
                        all_colors.add(color_code.upper())
                        print(f"   ✅ {color_type}: {color_code}")

            print("\n📋 Full Analysis:")
            print(json.dumps(analysis, indent=2, ensure_ascii=False)[:500])

        except Exception as e:
            print(f"   ❌ Error: {type(e).__name__}: {e}")

    # Summary
    print(f"\n{'='*60}")
    print("🎨 BRAND COLOR SUMMARY")
    print(f"{'='*60}")

    all_colors_sorted = sorted(list(all_colors))
    print(f"\nAll colors found: {len(all_colors_sorted)}")
    for color in all_colors_sorted:
        print(f"  {color}")

    # Save analyses
    output_file = Path("/home/ubuntu/agente_contenido/brand_assets/mi-idea/logo_analysis.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "logos_analyzed": len(logo_files),
                "all_colors": list(all_colors_sorted),
                "detailed_analyses": analyses,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"\n💾 Analysis saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
