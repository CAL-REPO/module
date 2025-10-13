# -*- coding: utf-8 -*-
# pillow_refactor/overlay.py

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple

from PIL import Image, ImageDraw, ImageFont

from .policy import OverlayPolicy, OverlayTextPolicy, ImageMetaPolicy
from .io import ImageReader, ImageWriter


class OverlayRenderer:
    """Draws text overlays described by OverlayPolicy."""

    def __init__(self, policy: OverlayPolicy):
        self.policy = policy

    def render(self) -> Path:
        reader = ImageReader(self.policy.image)
        writer = ImageWriter(self.policy.output, ImageMetaPolicy(enabled=False))
        image, _meta = reader.load()
        if image.mode != "RGBA":
            image = image.convert("RGBA")

        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        for text_cfg in self.policy.texts:
            self._draw_text(draw, text_cfg)

        alpha = int(max(0.0, min(1.0, self.policy.background_opacity)) * 255)
        if alpha:
            background = Image.new("RGBA", image.size, (255, 255, 255, alpha))
            overlay = Image.alpha_composite(background, overlay)

        composed = Image.alpha_composite(image, overlay)
        target_path = writer.save_image(composed.convert("RGB"), self.policy.image.path)
        return target_path

    def _draw_text(self, draw: ImageDraw.ImageDraw, cfg: OverlayTextPolicy) -> None:
        bbox = self._polygon_bbox(cfg.polygon)
        size = cfg.font.size or self._auto_size(cfg.text, bbox, cfg.max_width_ratio)
        font = self._load_font(cfg, size)
        position = self._center_of_bbox(bbox)
        position = (position[0] + cfg.offset[0], position[1] + cfg.offset[1])

        draw.text(
            position,
            cfg.text,
            font=font,
            fill=cfg.font.fill,
            anchor=cfg.anchor,
            stroke_width=cfg.font.stroke_width,
            stroke_fill=cfg.font.stroke_fill,
        )

    @staticmethod
    def _polygon_bbox(points: Iterable[Tuple[float, float]]) -> Tuple[float, float, float, float]:
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return min(xs), min(ys), max(xs), max(ys)

    @staticmethod
    def _center_of_bbox(bbox: Tuple[float, float, float, float]) -> Tuple[float, float]:
        x0, y0, x1, y1 = bbox
        return (x0 + x1) / 2.0, (y0 + y1) / 2.0

    def _load_font(self, cfg: OverlayTextPolicy, size: int) -> ImageFont.ImageFont:
        font_path = cfg.font.family
        if font_path and Path(font_path).exists():
            return ImageFont.truetype(str(font_path), size=size)
        if font_path:
            try:
                return ImageFont.truetype(font_path, size=size)
            except Exception:
                pass
        try:
            return ImageFont.truetype("arial.ttf", size=size)
        except Exception:
            return ImageFont.load_default()

    @staticmethod
    def _auto_size(text: str, bbox: Tuple[float, float, float, float], ratio: float) -> int:
        width = max(1, int(bbox[2] - bbox[0]))
        height = max(1, int(bbox[3] - bbox[1]))
        if not text:
            return max(12, int(height * ratio))
        approx_width = width * ratio
        approx_height = height * ratio
        return max(12, int(min(approx_width / max(1, len(text)), approx_height)))
