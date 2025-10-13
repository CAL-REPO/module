# -*- coding: utf-8 -*-
# pillow_refactor/pipeline.py

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .io import ImageReader, ImageWriter
from .models import ImagePipelineResult
from .policy import ImagePipelinePolicy
from .processor import ImageProcessor


class ImagePipeline:
    """High level helper that loads → processes → saves an image."""

    def __init__(self, policy: ImagePipelinePolicy):
        self.policy = policy
        self.reader = ImageReader(policy.source)
        self.processor = ImageProcessor(policy.processing)
        self.writer = ImageWriter(policy.target, policy.meta)

    def run(self) -> ImagePipelineResult:
        image, meta = self.reader.load()
        processed = self.processor.apply(image)

        saved_image_path: Optional[Path] = None
        saved_meta_path: Optional[Path] = None

        if self.policy.target:
            saved_image_path = self.writer.save_image(processed, meta.src_path)
        if self.policy.meta.enabled:
            saved_meta_path = self.writer.save_meta(meta, saved_image_path or meta.src_path)

        return ImagePipelineResult(
            image=processed,
            meta=meta,
            saved_image_path=saved_image_path,
            saved_meta_path=saved_meta_path,
        )
