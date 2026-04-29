"""Skill to generate images with animation metadata."""

from __future__ import annotations

import json
import os
from typing import Any

from api.config import settings
from api.events import EventBus
from skills import BaseSkill, SkillResult
from skills.image_generator import ImageGenerator


class AnimatedImageGenerator(ImageGenerator):
    """Extends ImageGenerator to include motion/animation metadata.

    For each scene, extracts motion hints from visual_description and
    saves motion.json metadata file.
    """

    skill_name = "animated_image_generator"

    MOTION_PATTERNS = {
        "zoom in": "zoom_in",
        "zoom out": "zoom_out",
        "zoom": "zoom_in",
        "pan left": "pan_left",
        "pan right": "pan_right",
        "pan up": "pan_up",
        "pan down": "pan_down",
        "pan": "pan_left",
        "slow pan": "slow_pan",
        "subtle zoom": "subtle_zoom",
        "diagonal": "diagonal",
        "move forward": "zoom_in",
        "move backward": "zoom_out",
        "slide left": "pan_left",
        "slide right": "pan_right",
        "static": "static",
        "none": "none",
    }

    async def run(self, inputs: dict[str, Any], interactive: bool = False) -> SkillResult:
        """Generate images with motion metadata."""
        script: dict = inputs["script"]
        profile: dict = inputs.get("profile", {})
        platform: str = inputs.get("platform", "tiktok")

        # Use parent class to generate images
        result = await super().run(inputs, interactive)

        if result.status != "completed":
            return result

        image_paths = result.outputs.get("image_paths", [])
        scenes = script.get("scenes", [])

        # Extract motion metadata for each image
        motion_metadata = []
        for i, (scene, img_path) in enumerate(zip(scenes, image_paths)):
            motion_hint = self._extract_motion_hint(
                scene.get("visual_description", "")
            )

            metadata = {
                "scene_index": i,
                "image_path": img_path,
                "motion_type": motion_hint.get("type", "static"),
                "motion_direction": motion_hint.get("direction"),
                "motion_target": motion_hint.get("target"),
                "duration_seconds": scene.get("duration_seconds", 3),
                "speaker_text": scene.get("speaker_text", ""),
                "on_screen_text": scene.get("on_screen_text"),
            }
            motion_metadata.append(metadata)

            # Save metadata file
            metadata_path = img_path.replace(".png", "_motion.json")
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            await self.emit(
                "progress",
                f"Metadata scene {i+1}/{len(scenes)}: {motion_hint.get('type')}",
            )

        await self.emit(
            "step_complete",
            f"Generated motion metadata for {len(image_paths)} images",
            data={"motion_metadata": motion_metadata},
        )

        return SkillResult(
            status="completed",
            outputs={
                "image_paths": image_paths,
                "motion_metadata": motion_metadata,
            }
        )

    def _extract_motion_hint(self, visual_description: str) -> dict[str, Any]:
        """Extract motion type from visual description.

        Returns:
            {
                "type": "zoom_in" | "pan_left" | "static" | ...,
                "direction": "in" | "left" | None,
                "target": "face" | "product" | None,
            }
        """
        text = visual_description.lower()
        motion_type = "static"
        direction = None
        target = None

        # Detect motion type with keywords
        for pattern, motion in self.MOTION_PATTERNS.items():
            if pattern in text:
                motion_type = motion

                # Extract target
                for target_word in ["face", "product", "subject", "object", "center"]:
                    if target_word in text:
                        target = target_word
                        break

                # Extract direction
                if "in" in motion_type:
                    direction = "in"
                elif "out" in motion_type:
                    direction = "out"
                elif "left" in motion_type:
                    direction = "left"
                elif "right" in motion_type:
                    direction = "right"
                elif "up" in motion_type:
                    direction = "up"
                elif "down" in motion_type:
                    direction = "down"

                break

        return {
            "type": motion_type,
            "direction": direction,
            "target": target,
        }
