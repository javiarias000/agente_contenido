"""Skill to analyze user-uploaded product photo using GPT-4o Vision."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from api.config import settings
from api.events import EventBus
from skills import BaseSkill, SkillResult

ANALYSIS_PROMPT = """Analyze this product photo and provide structured insights for UGC content creation.

Return JSON with these exact fields:
{
  "product_name": "name/category of the product (e.g., laser-cut wood box)",
  "product_description": "detailed description of what the product is and what it does",
  "key_features": ["feature1", "feature2", "feature3"],
  "visual_style": "describe the aesthetic (e.g., minimalist, rustic, luxury, artisanal)",
  "dominant_colors": ["color1", "color2"],
  "emotional_appeal": "what emotions does this product evoke? (e.g., creativity, elegance, comfort)",
  "use_cases": "what problems does this product solve or what needs does it fulfill",
  "suggested_hook": "a compelling opening line for a UGC video about this product",
  "target_audience_hints": "who would want this product? (e.g., designers, home decorators, entrepreneurs)",
  "full_context": "a comprehensive paragraph combining all insights above, suitable for LLM prompt injection"
}

Be specific and use the actual visual details from the photo. Return ONLY valid JSON."""


class PhotoAnalyzer(BaseSkill):
    """Analyze product photo using GPT-4o Vision."""

    skill_name = "photo_analyzer"

    def __init__(
        self,
        event_bus: EventBus,
        run_id: str,
        step_index: int = 0,
    ):
        super().__init__(event_bus, run_id, step_index)
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def run(self, inputs: dict[str, Any], interactive: bool = False) -> SkillResult:
        """Analyze product photo.

        Expected inputs:
            - photo_path: Path to uploaded photo
            - brand_slug: Brand context (optional)
        """
        photo_path = inputs.get("photo_path", "")
        brand_slug = inputs.get("brand_slug", "user_product")

        if not photo_path or not os.path.exists(photo_path):
            return SkillResult(
                status="failed",
                outputs={"error": f"Photo not found: {photo_path}"}
            )

        await self.emit("step_start", f"Analizando foto del producto...")

        try:
            # Read and encode image
            await self.emit("progress", "Codificando imagen...")
            with open(photo_path, "rb") as f:
                image_data = base64.standard_b64encode(f.read()).decode("utf-8")

            # Determine image type from extension
            ext = Path(photo_path).suffix.lower()
            mime_type = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
                ".webp": "image/webp",
            }.get(ext, "image/jpeg")

            # Call GPT-4o Vision
            await self.emit("progress", "Analizando con GPT-4o Vision...")
            response = await self.client.messages.create(
                model="gpt-4o",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime_type,
                                    "data": image_data,
                                },
                            },
                            {
                                "type": "text",
                                "text": ANALYSIS_PROMPT,
                            },
                        ],
                    }
                ],
            )

            # Parse response
            await self.emit("progress", "Parseando análisis...")
            text = response.content[0].text if response.content else "{}"

            # Try to extract JSON
            try:
                analysis = json.loads(text)
            except json.JSONDecodeError:
                # Fallback: wrap response in JSON
                analysis = {
                    "product_description": text,
                    "full_context": text,
                    "suggested_hook": "Mira lo que puedo crear para ti.",
                }

            # Ensure required fields exist
            analysis.setdefault("product_name", "Product")
            analysis.setdefault("product_description", "")
            analysis.setdefault("suggested_hook", "Check this out!")
            analysis.setdefault("full_context", "")

            await self.emit(
                "step_complete",
                f"Análisis completado: {analysis.get('product_name', 'Product')}",
                data={"product_name": analysis.get("product_name")},
            )

            return SkillResult(
                status="completed",
                outputs={
                    "photo_analysis": analysis,
                    "product_name": analysis.get("product_name"),
                    "product_description": analysis.get("product_description"),
                    "suggested_hook": analysis.get("suggested_hook"),
                    "full_context": analysis.get("full_context"),
                }
            )

        except Exception as e:
            await self.emit("progress", f"❌ Error: {e}")
            return SkillResult(
                status="failed",
                outputs={"error": str(e)}
            )
