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
from ..core.policy import OverlayTextPolicy


class OverlayTextRenderer:
    """Renders individual text overlays with proper positioning and styling."""

    def __init__(self, draw: ImageDraw.ImageDraw):
        """Initialize renderer with a PIL Draw object."""
        self.draw = draw

    def render_text(self, config: OverlayTextPolicy) -> None:
        """Render a single text overlay according to configuration.
        
        Rendering Process:
        1. 흰색 배경 마스킹 bbox 그리기 (polygon 영역)
        2. 텍스트 렌더링 (외곽선 + 채우기)
        
        Note: 
        - config.font는 항상 FontPolicy 인스턴스 (default_factory 보장)
        - fill, stroke_fill, stroke_width는 FontPolicy에서 기본값 제공
        """
        # Calculate geometry using data_utils.GeometryOps
        bbox = GeometryOps.polygon_bbox(config.polygon)
        
        # ====================================================================
        # Step 1: 흰색 배경 마스킹 (polygon 영역)
        # ====================================================================
        # polygon을 흰색으로 채우기 (배경 마스킹)
        self.draw.polygon(
            config.polygon,
            fill="#FFFFFF",  # 흰색 배경
            outline=None,     # 외곽선 없음
        )
        
        # ====================================================================
        # Step 2: 텍스트 렌더링
        # ====================================================================
        # Determine font size
        if config.font.size:
            size = config.font.size
        else:
            # Auto-fit size based on bbox and text length
            size = GeometryOps.auto_font_size(
                config.text, bbox, config.max_width_ratio
            )
        
        # Load font with fallback
        font = self._load_font(config.font, size)
        
        # Calculate position (center of bbox + offset)
        center = GeometryOps.bbox_center(bbox)
        position = (
            center[0] + config.offset[0],
            center[1] + config.offset[1],
        )
        
        # Draw text with stroke (외곽선) and fill (채우기)
        # stroke_width=0이면 외곽선 없이 텍스트만 그려짐
        self.draw.text(
            position,
            config.text,
            font=font,
            fill=config.font.fill,              # 텍스트 색상 (기본: #000000)
            anchor=config.anchor,                # 앵커 (기본: "mm" - 중앙)
            stroke_width=config.font.stroke_width,  # 외곽선 두께 (기본: 0)
            stroke_fill=config.font.stroke_fill,    # 외곽선 색상 (기본: None)
        )
        
        # Debug: Log rendering details (개발 중에만 활성화)
        # print(f"[Renderer] text='{config.text}', pos={position}, size={size}, "
        #       f"fill={config.font.fill}, stroke={config.font.stroke_width}px")
    
    @staticmethod
    def _load_font(font_policy: FontPolicy, size: int):
        """Load font with fallback chain.
        
        Font loading priority:
        1. family as absolute file path
        2. family as filename in font_dir
        3. family as system font name
        4. Arial fallback
        5. Pillow default font
        
        Args:
            font_policy: FontPolicy with font_dir, family, etc.
            size: Font size in pixels
            
        Returns:
            PIL ImageFont object
        """
        font_path = font_policy.family
        font_dir = font_policy.font_dir
        
        # 1. Try as absolute file path
        if font_path and Path(font_path).exists():
            try:
                return ImageFont.truetype(str(font_path), size=size)  # type: ignore
            except Exception:
                pass
        
        # 2. Try as filename in font_dir
        if font_path and font_dir:
            font_file = Path(font_dir) / font_path
            if font_file.exists():
                try:
                    return ImageFont.truetype(str(font_file), size=size)  # type: ignore
                except Exception:
                    pass
        
        # 3. Try as system font name
        if font_path:
            try:
                return ImageFont.truetype(font_path, size=size)  # type: ignore
            except Exception:
                pass
        
        # 4. Try Arial fallback
        try:
            return ImageFont.truetype("arial.ttf", size=size)  # type: ignore
        except Exception:
            pass
        
        # 5. Default font (very small, bitmap)
        return ImageFont.load_default()  # type: ignore


# Pure functional helpers - no classes needed for simple rendering