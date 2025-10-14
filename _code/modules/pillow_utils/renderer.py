# -*- coding: utf-8 -*-
# pillow_utils/renderer.py
"""Pure functional overlay rendering utilities.

This module provides simple rendering functions without policy or logging concerns.
Policy and logging are handled by image_overlay.py (the entrypoint).

This module uses:
- GeometryOps from data_utils for geometric calculations
- PIL for drawing operations
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image, ImageDraw, ImageFont

from data_utils import GeometryOps
from font_utils import FontPolicy
from .policy import OverlayTextPolicy


class OverlayTextRenderer:
    """Renders individual text overlays with proper positioning and styling."""

    def __init__(self, draw: ImageDraw.ImageDraw):
        """Initialize renderer with a PIL Draw object."""
        self.draw = draw

    def render_text(self, config: OverlayTextPolicy) -> None:
        """Render a single text overlay according to configuration."""
        # Calculate geometry using data_utils.GeometryOps
        bbox = GeometryOps.polygon_bbox(config.polygon)
        
        # Determine font size
        if config.font.size:
            size = config.font.size
        else:
            size = GeometryOps.auto_font_size(
                config.text, bbox, config.max_width_ratio
            )
        
        # Load font with fallback
        font = self._load_font(config.font, size)
        
        # Calculate position
        center = GeometryOps.bbox_center(bbox)
        position = (
            center[0] + config.offset[0],
            center[1] + config.offset[1],
        )
        
        # Draw text
        self.draw.text(
            position,
            config.text,
            font=font,
            fill=config.font.fill,
            anchor=config.anchor,
            stroke_width=config.font.stroke_width,
            stroke_fill=config.font.stroke_fill,
        )
    
    @staticmethod
    def _load_font(font_policy: FontPolicy, size: int):
        """Load font with fallback chain."""
        font_path = font_policy.family
        
        # Try as file path
        if font_path and Path(font_path).exists():
            try:
                return ImageFont.truetype(str(font_path), size=size)  # type: ignore
            except Exception:
                pass
        
        # Try as font name
        if font_path:
            try:
                return ImageFont.truetype(font_path, size=size)  # type: ignore
            except Exception:
                pass
        
        # Try Arial fallback
        try:
            return ImageFont.truetype("arial.ttf", size=size)  # type: ignore
        except Exception:
            pass
        
        # Default font
        return ImageFont.load_default()  # type: ignore


# Pure functional helpers - no classes needed for simple rendering