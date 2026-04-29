"""Skill to improve image quality using enhancement and upscaling."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from api.events import EventBus
from skills import BaseSkill, SkillResult
from skills.utils.image_enhancer import (
    enhance_image_quality,
    upscale_image,
    apply_brand_colors,
    get_enhancement_recommendations,
)


class ImageQualityImprover(BaseSkill):
    """Improve image quality through upscaling and enhancement."""

    skill_name = "image_quality_improver"

    def __init__(
        self,
        event_bus: EventBus,
        run_id: str,
        step_index: int = 0,
    ):
        super().__init__(event_bus, run_id, step_index)

    async def run(self, inputs: dict[str, Any], interactive: bool = False) -> SkillResult:
        """
        Improve image quality.

        Expected inputs:
            - image_path: Path to image to improve
            - quality_score: Current quality score (1-10, optional)
            - apply_brand_colors: Whether to apply brand color grading
        """
        image_path = inputs.get("image_path")
        quality_score = inputs.get("quality_score", 5)
        apply_colors = inputs.get("apply_brand_colors", False)

        if not image_path or not Path(image_path).exists():
            return SkillResult(
                status="failed",
                outputs={"error": f"Image not found: {image_path}"}
            )

        await self.emit("step_start", f"Mejorando calidad de imagen: {Path(image_path).name}")

        # Generate output path
        input_path = Path(image_path)
        output_dir = input_path.parent / "enhanced"
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"{input_path.stem}_enhanced{input_path.suffix}"

        try:
            # Get recommendations based on quality score
            recommendations = get_enhancement_recommendations(quality_score)

            # Step 1: Upscale if needed
            if recommendations.get("upscale") != "none":
                await self.emit("progress", f"Escalando imagen ({recommendations['upscale']})...")
                scale_factor = 2 if recommendations["upscale"] == "2x" else 1
                if scale_factor > 1:
                    success = await upscale_image(
                        str(image_path),
                        str(output_path),
                        scale_factor=scale_factor
                    )
                    if success:
                        image_path = str(output_path)
                        await self.emit("progress", "✅ Escalado completado")
                    else:
                        await self.emit("progress", "⚠️ No se pudo escalar, continuando...")

            # Step 2: Enhance brightness, contrast, saturation
            await self.emit("progress", "Mejorando brillo y contraste...")

            brightness = 1.1 if recommendations["brightness"] == "increase" else 1.0
            contrast = 1.15 if recommendations["contrast"] == "increase" else (
                1.05 if recommendations["contrast"] == "slight_increase" else 1.0
            )
            saturation = 1.1 if recommendations["saturation"] == "increase" else 1.0

            success = await enhance_image_quality(
                image_path,
                str(output_path),
                brightness=brightness,
                contrast=contrast,
                saturation=saturation,
            )

            if success:
                await self.emit("progress", "✅ Mejora de brillo/contraste completada")
            else:
                return SkillResult(
                    status="failed",
                    outputs={"error": "Failed to enhance image"}
                )

            # Step 3: Apply brand colors if requested
            if apply_colors:
                await self.emit("progress", "Aplicando colores de marca...")
                # Mi Idea primary color: #D35400 (RGB: 211, 84, 0)
                success = await apply_brand_colors(
                    str(output_path),
                    str(output_path),
                    primary_color=(211, 84, 0),
                    accent=True,
                )
                if success:
                    await self.emit("progress", "✅ Colores de marca aplicados")

            # Summary
            improvements = []
            if brightness != 1.0:
                improvements.append(f"Brillo: +{int((brightness-1)*100)}%")
            if contrast != 1.0:
                improvements.append(f"Contraste: +{int((contrast-1)*100)}%")
            if saturation != 1.0:
                improvements.append(f"Saturación: +{int((saturation-1)*100)}%")

            summary = f"Mejoras aplicadas: {', '.join(improvements)}"

            await self.emit("step_complete", summary, data={
                "original_path": str(image_path),
                "improved_path": str(output_path),
                "quality_score_before": quality_score,
                "estimated_quality_after": min(10, quality_score + 2),
                "improvements": improvements,
            })

            return SkillResult(
                status="completed",
                outputs={
                    "original_path": str(image_path),
                    "improved_path": str(output_path),
                    "quality_improvement": 2,  # Estimated points gained
                }
            )

        except Exception as e:
            await self.emit("progress", f"❌ Error: {e}")
            return SkillResult(
                status="failed",
                outputs={"error": str(e)}
            )
