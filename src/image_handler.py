"""
Image handling module for direct image ingestion with vision-capable LLMs.
Supports encoding images for multiple LLM backends (OpenAI Vision, Google Gemini Vision, Claude Vision).
"""

import base64
import io
import logging
from pathlib import Path
from typing import Union

from PIL import Image


class ImageHandler:
    """Handles image encoding and conversion for vision-capable LLM backends."""

    MAX_IMAGE_SIZE = 4096  # Max dimension for resizing large images
    QUALITY = 85  # JPEG quality for encoding

    @staticmethod
    def load_image(path: Union[str, Path]) -> Image.Image:
        """Load an image from file path."""
        return Image.open(str(path))

    @staticmethod
    def resize_if_needed(image: Image.Image, max_size: int = MAX_IMAGE_SIZE) -> Image.Image:
        """Resize image if any dimension exceeds max_size while preserving aspect ratio."""
        if image.width > max_size or image.height > max_size:
            image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            logging.info("Resized image to %dx%d", image.width, image.height)
        return image

    @staticmethod
    def image_to_base64(image: Image.Image, format: str = "JPEG") -> str:
        """Convert PIL Image to base64-encoded string."""
        buffer = io.BytesIO()
        # Convert RGBA to RGB if needed
        if image.mode in {"RGBA", "LA", "P"}:
            rgb_image = Image.new("RGB", image.size, (255, 255, 255))
            rgb_image.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
            image = rgb_image
        image.save(buffer, format=format, quality=ImageHandler.QUALITY)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    @staticmethod
    def encode_image_for_openai(image: Image.Image) -> str:
        """Encode image for OpenAI Vision API (base64)."""
        image = ImageHandler.resize_if_needed(image)
        return ImageHandler.image_to_base64(image)

    @staticmethod
    def encode_image_for_google(image: Image.Image) -> str:
        """Encode image for Google Gemini Vision API (base64)."""
        image = ImageHandler.resize_if_needed(image)
        return ImageHandler.image_to_base64(image)

    @staticmethod
    def encode_image_for_claude(image: Image.Image) -> str:
        """Encode image for Claude Vision API (base64)."""
        image = ImageHandler.resize_if_needed(image)
        return ImageHandler.image_to_base64(image)

    @staticmethod
    def extract_images_from_bytes(image_data: bytes) -> Image.Image:
        """Extract PIL Image from bytes."""
        return Image.open(io.BytesIO(image_data))
