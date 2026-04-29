#!/usr/bin/env python
"""Test gpt-image-1.5 directly with Mi Idea brand context."""

import asyncio
import base64
from pathlib import Path
from openai import AsyncOpenAI
from api.config import settings


async def test_image_generation():
    """Test gpt-image-1.5 image generation with Mi Idea brand."""

    print(f"\n{'='*60}")
    print(f"Testing GPT-Image-1.5 for Mi Idea")
    print(f"{'='*60}\n")

    client = AsyncOpenAI(api_key=settings.openai_api_key)

    # Prompt específico para Mi Idea con colores de marca
    prompt = """
    A professional product showcase of a laser-cut MDF box for wine bottles.
    The design features personalized engraving with elegant text.
    Color palette: #D35400 (Orange), #A84327 (Brown), #5C2B17 (Dark Brown).
    Use these brand colors prominently in the wood texture and highlights.

    Details:
    - Wooden MDF construction visible
    - Precise laser-cut edges and details
    - Professional presentation on white background
    - Minimalist modern style
    - Product photography, high quality lighting
    - Photorealistic, sharp focus, professional
    """

    print("🎨 Generating image with gpt-image-1.5...")
    print(f"Prompt (truncated): {prompt[:150]}...\n")

    try:
        response = await client.images.generate(
            model="gpt-image-1.5",
            prompt=prompt,
            size="1024x1024",
            quality="high",
            n=1,
        )

        print("✅ Image generated successfully!\n")

        # Get image URL and download it
        image_url = response.data[0].url
        print(f"📍 Image URL: {image_url[:80]}...\n")

        # Download image
        import httpx
        async with httpx.AsyncClient() as http_client:
            image_response = await http_client.get(image_url)
            image_bytes = image_response.content

        output_path = Path("/home/ubuntu/agente_contenido/outputs/images")
        output_path.mkdir(parents=True, exist_ok=True)

        image_file = output_path / "test_gpt_image_1_5.png"
        with open(image_file, "wb") as f:
            f.write(image_bytes)

        print(f"📸 Image saved: {image_file}")
        print(f"📊 Size: {len(image_bytes):,} bytes")
        print(f"🖼️  Resolution: 1024x1024")
        print(f"⭐ Quality: hd")
        print(f"\n✨ SUCCESS - Image generated with brand colors!")

        return str(image_file)

    except Exception as e:
        print(f"❌ Error: {type(e).__name__}")
        print(f"Message: {e}")
        return None


if __name__ == "__main__":
    result = asyncio.run(test_image_generation())
    if result:
        print(f"\n🎉 Test completed successfully!")
        print(f"Output: {result}")
    else:
        print(f"\n⚠️  Test failed")
