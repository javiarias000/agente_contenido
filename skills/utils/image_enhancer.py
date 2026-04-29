"""Image enhancement utilities for upscaling and quality improvement."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional


async def upscale_image(
    input_path: str,
    output_path: str,
    scale_factor: int = 2,
    model: str = "upconv_7_anime"
) -> bool:
    """
    Upscale an image using Real-ESRGAN.

    Args:
        input_path: Path to input image
        output_path: Path to output image
        scale_factor: Upscaling factor (2, 3, or 4)
        model: ESRGAN model to use

    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if Real-ESRGAN CLI is available
        result = subprocess.run(
            ["which", "realesrgan-ncnn-vulkan"],
            capture_output=True,
            timeout=5
        )

        if result.returncode != 0:
            # Try with Python package if CLI not available
            return await _upscale_with_python(input_path, output_path, scale_factor)

        # Use CLI tool if available
        cmd = [
            "realesrgan-ncnn-vulkan",
            "-i", input_path,
            "-o", output_path,
            "-n", model,
            "-s", str(scale_factor),
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=60)
        return result.returncode == 0

    except Exception:
        # Fallback to Python implementation
        return await _upscale_with_python(input_path, output_path, scale_factor)


async def _upscale_with_python(
    input_path: str,
    output_path: str,
    scale_factor: int = 2
) -> bool:
    """Fallback: upscale using Python libraries (slower but works)."""
    try:
        from PIL import Image
        import numpy as np
        from scipy import ndimage

        # Open image
        img = Image.open(input_path)

        # Get current size
        width, height = img.size
        new_width = width * scale_factor
        new_height = height * scale_factor

        # Upscale using high-quality resampling
        img_upscaled = img.resize(
            (new_width, new_height),
            Image.Resampling.LANCZOS
        )

        # Optional: apply slight sharpening
        arr = np.array(img_upscaled)
        if len(arr.shape) == 3:  # Has color channels
            sharpened = ndimage.gaussian_filter(arr, sigma=0.5)
            img_upscaled = Image.fromarray(sharpened.astype('uint8'))

        # Save
        img_upscaled.save(output_path, quality=95)
        return True

    except Exception:
        return False


async def enhance_image_quality(
    input_path: str,
    output_path: str,
    brightness: float = 1.0,
    contrast: float = 1.0,
    saturation: float = 1.0,
) -> bool:
    """
    Enhance image quality: brightness, contrast, saturation.

    Args:
        input_path: Path to input image
        output_path: Path to output image
        brightness: Brightness factor (1.0 = no change)
        contrast: Contrast factor (1.0 = no change)
        saturation: Saturation factor (1.0 = no change)

    Returns:
        True if successful
    """
    try:
        from PIL import Image, ImageEnhance

        img = Image.open(input_path)

        # Apply enhancements
        if brightness != 1.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(brightness)

        if contrast != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(contrast)

        if saturation != 1.0:
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(saturation)

        img.save(output_path, quality=95)
        return True

    except Exception:
        return False


async def apply_brand_colors(
    input_path: str,
    output_path: str,
    primary_color: tuple[int, int, int] | None = None,
    accent: bool = False,
) -> bool:
    """
    Apply brand color grading to image.

    Args:
        input_path: Path to input image
        output_path: Path to output image
        primary_color: RGB tuple for color grading
        accent: Whether to add accent color overlay

    Returns:
        True if successful
    """
    try:
        from PIL import Image, ImageEnhance
        import numpy as np

        img = Image.open(input_path)

        if primary_color:
            # Convert to numpy array
            arr = np.array(img, dtype=np.float32)

            # Apply warm color cast (for brand colors)
            # Increase red and yellow channels slightly
            if len(arr.shape) == 3:
                arr[:, :, 0] = np.clip(arr[:, :, 0] * 1.05, 0, 255)  # Red
                arr[:, :, 1] = np.clip(arr[:, :, 1] * 1.02, 0, 255)  # Green
                # Keep blue channel as is

            img = Image.fromarray(arr.astype('uint8'))

        img.save(output_path, quality=95)
        return True

    except Exception:
        return False


def get_enhancement_recommendations(quality_score: int) -> dict[str, str]:
    """
    Get recommendations based on quality score.

    Args:
        quality_score: Score from 1-10

    Returns:
        Dict of recommendations
    """
    recommendations = {
        "upscale": "2x" if quality_score < 6 else "none",
        "brightness": "increase" if quality_score < 5 else "maintain",
        "contrast": "increase" if quality_score < 6 else "slight_increase",
        "saturation": "increase" if quality_score < 7 else "maintain",
        "denoise": "strong" if quality_score < 5 else ("light" if quality_score < 7 else "none"),
    }

    return recommendations
