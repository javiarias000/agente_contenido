#!/usr/bin/env python
"""Analyze Facebook posts to understand visual style and composition."""

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


async def analyze_post(image_path: str, post_num: int) -> dict:
    """Analyze a post image."""
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    ext = Path(image_path).suffix.lower()
    media_type_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }
    media_type = media_type_map.get(ext, "image/jpeg")
    image_data = await encode_image(image_path)

    prompt = f"""Analiza este post #{post_num} de la empresa Mi Idea (corte láser, diseño MDF, acrílico, etc).

Proporciona:
1. **Contenido**: ¿Qué muestra? (producto, proceso, diseño, etc)
2. **Composición visual**: Layout, elementos principales, balance
3. **Colores usados**: Colores principales visibles (hex si es posible)
4. **Calidad**: Evaluación 1-10 (1=muy mala, 10=excelente). ¿Es clara, bien iluminada, enfocada?
5. **Problemas de calidad** (si los hay): Borrosa, mala iluminación, cortes, etc
6. **Tipo de contenido**: Producto, proceso, resultado, inspiración, etc
7. **Engagement potencial**: Baja, Media, Alta (qué tan interesante sería para la audiencia)
8. **Recomendaciones**: Cómo mejorar esta imagen o tipo de contenido similar

Responde en JSON."""

    message = await client.chat.completions.create(
        model="gpt-4o",
        max_tokens=1500,
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

    response_text = message.choices[0].message.content

    try:
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
    posts_dir = Path("/home/ubuntu/agente_contenido/brand_assets/mi-idea/posts")

    # Find all post images
    all_posts = sorted(
        list(posts_dir.glob("**/*.png")) + list(posts_dir.glob("**/*.jpg")) + list(posts_dir.glob("**/*.jpeg"))
    )

    # Limit to 10 posts
    posts_to_analyze = all_posts[:10]

    if not posts_to_analyze:
        print(f"❌ No post images found in {posts_dir}")
        return

    print(f"\n{'='*60}")
    print(f"Analyzing {len(posts_to_analyze)} posts from 'Mi Idea'")
    print(f"{'='*60}\n")

    analyses = {}
    quality_scores = []
    content_types = {}

    for idx, post_file in enumerate(posts_to_analyze, 1):
        print(f"📸 Post {idx}/10: {post_file.name}...", end=" ", flush=True)

        try:
            analysis = await analyze_post(str(post_file), idx)
            analyses[post_file.name] = analysis

            # Track quality
            quality = analysis.get("calidad", {})
            if isinstance(quality, dict):
                score = quality.get("puntuacion", 0)
                quality_scores.append((post_file.name, score))

            # Track content types
            content_type = analysis.get("tipo_de_contenido", "otro")
            content_types[content_type] = content_types.get(content_type, 0) + 1

            print("✅")

        except Exception as e:
            print(f"❌ {type(e).__name__}")
            analyses[post_file.name] = {"error": str(e)}

    # Summary
    print(f"\n{'='*60}")
    print("📊 POSTS ANALYSIS SUMMARY")
    print(f"{'='*60}\n")

    # Quality summary
    if quality_scores:
        avg_quality = sum(s[1] for s in quality_scores) / len(quality_scores)
        print(f"📈 Average Quality Score: {avg_quality:.1f}/10")
        print(f"\nQuality Breakdown:")
        for name, score in sorted(quality_scores, key=lambda x: x[1], reverse=True):
            star = "⭐" * int(score / 2)
            print(f"  {score}/10 {star} - {name}")

    # Content types
    if content_types:
        print(f"\n📋 Content Types Found:")
        for ctype, count in sorted(content_types.items(), key=lambda x: x[1], reverse=True):
            print(f"  • {ctype}: {count} posts")

    # Save analyses
    output_file = Path("/home/ubuntu/agente_contenido/brand_assets/mi-idea/posts_analysis.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "posts_analyzed": len(posts_to_analyze),
                "average_quality": avg_quality if quality_scores else 0,
                "content_types": content_types,
                "detailed_analyses": analyses,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"\n💾 Analysis saved to: {output_file}")

    # Print sample analysis
    if analyses:
        print(f"\n{'='*60}")
        print("📌 Sample Analysis (Post 1):")
        print(f"{'='*60}")
        first_post = next(iter(analyses.items()))
        print(json.dumps(first_post[1], indent=2, ensure_ascii=False)[:800])


if __name__ == "__main__":
    asyncio.run(main())
