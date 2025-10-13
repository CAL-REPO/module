# -*- coding: utf-8 -*-
# pillow_refactor/processor.py

from __future__ import annotations

from typing import Tuple

from PIL import Image, ImageFilter

from .policy import ImageProcessingPolicy


class ImageProcessor:
    """Applies lightweight processing steps defined in ImageProcessingPolicy."""

    def __init__(self, policy: ImageProcessingPolicy):
        self.policy = policy

    def apply(self, image: Image.Image) -> Image.Image:
        processed = image

        if self.policy.resize_to:
            processed = self._resize(processed, self.policy.resize_to)
        if self.policy.blur_radius:
            processed = self._blur(processed, self.policy.blur_radius)
        if self.policy.convert_mode:
            processed = processed.convert(self.policy.convert_mode)

        return processed

    @staticmethod
    def _resize(image: Image.Image, size: Tuple[int, int]) -> Image.Image:
        return image.resize(size, Image.Resampling.LANCZOS)

    @staticmethod
    def _blur(image: Image.Image, radius: float) -> Image.Image:
        return image.filter(ImageFilter.GaussianBlur(radius))
