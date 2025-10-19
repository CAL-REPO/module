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
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from data_utils import GeometryOps
from font_utils import FontPolicy
from ..core.policy import OverlayItemPolicy


class OverlayTextRenderer:
    """Renders individual text overlays with proper positioning and styling."""

    def __init__(self, draw: ImageDraw.ImageDraw):
        """Initialize renderer with a PIL Draw object."""
        self.draw = draw

    def render_text(self, config: OverlayItemPolicy) -> None:
        """Render a single text overlay according to configuration.
        
        Rendering Process:
        1. 흰색 배경 마스킹 bbox 그리기 (polygon 영역)
        2. 텍스트 렌더링 (외곽선 + 채우기)
        
        Note: 
        - config.font가 None이면 기본 FontPolicy 사용
        - fill, stroke_fill, stroke_width는 FontPolicy에서 기본값 제공
        """
        # font가 None이면 기본 FontPolicy 생성
        if config.font is None:
            config.font = FontPolicy()  # type: ignore
        
        # Calculate geometry using data_utils.GeometryOps
        bbox = GeometryOps.polygon_bbox(config.polygon)
        
        # ====================================================================
        # Step 1: 배경 마스킹 (polygon 영역) - mask_opacity 적용
        # ====================================================================
        # mask_opacity가 0보다 크면 배경 마스킹 적용
        if config.mask_opacity > 0.0:
            # RGB 흰색 + 알파 채널 (투명도)
            alpha = int(255 * config.mask_opacity)  # 0.0 → 0 (투명), 1.0 → 255 (불투명)
            fill_color = (255, 255, 255, alpha)  # RGBA
            
            self.draw.polygon(
                config.polygon,
                fill=fill_color,   # 흰색 배경 + 투명도
                outline=None,       # 외곽선 없음
            )
        
        # ====================================================================
        # Step 2: 텍스트 렌더링
        # ====================================================================
        # Determine font size
        if config.font.size is not None and config.font.size != "auto":
            # 명시적 크기 지정
            size = int(config.font.size)
        else:
            # Auto-fit: 실제 폰트 측정 기반 크기 계산
            size = self._calculate_auto_font_size(
                config.text,
                bbox,
                config.font,
                config.max_width_ratio
            )
        
        # Load font with fallback
        font = self._load_font(config.font, size)
        
        # Calculate position (center of bbox + offset)
        center = GeometryOps.bbox_center(bbox)
        position = (
            center[0] + config.offset[0],
            center[1] + config.offset[1],
        )
        
        # Debug: Log geometry calculations
        # print(f"\n[Renderer Geometry Debug]")
        # print(f"  Text: '{config.text}'")
        # print(f"  Polygon: {config.polygon}")
        # print(f"  BBox: {bbox}")
        # print(f"  Center: {center}")
        # print(f"  Position: {position}")
        # print(f"  Font Size: {size}")
        # print(f"  Anchor: {config.anchor}")
        # print(f"  Offset: {config.offset}")
        
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
    
    def _calculate_auto_font_size(
        self,
        text: str,
        bbox: Tuple[float, float, float, float],
        font_policy: FontPolicy,
        width_ratio: float = 0.95,
    ) -> int:
        """Calculate optimal font size by measuring actual text rendering.
        
        Uses binary search to find the largest font size that fits within bbox.
        
        Args:
            text: Text to fit
            bbox: Target bounding box (x_min, y_min, x_max, y_max)
            font_policy: Font configuration
            width_ratio: Maximum ratio of bbox to use (default 0.95)
            
        Returns:
            Optimal font size in pixels (minimum 8, maximum 200)
        """
        if not text:
            return 24  # Default size for empty text
        
        bbox_width, bbox_height = GeometryOps.bbox_dimensions(bbox)
        target_width = bbox_width * width_ratio
        target_height = bbox_height * width_ratio
        
        # Binary search for optimal size
        min_size, max_size = 8, 200
        best_size = min_size
        
        while min_size <= max_size:
            mid_size = (min_size + max_size) // 2
            
            # Load font with current size
            font = self._load_font(font_policy, mid_size)
            
            # Measure text with stroke width included
            try:
                # getbbox returns (left, top, right, bottom)
                bbox_text = font.getbbox(text)
                text_width = bbox_text[2] - bbox_text[0]
                text_height = bbox_text[3] - bbox_text[1]
                
                # Add stroke width to dimensions
                stroke_width = font_policy.stroke_width or 0
                text_width += stroke_width * 2
                text_height += stroke_width * 2
                
                # Check if text fits
                if text_width <= target_width and text_height <= target_height:
                    best_size = mid_size
                    min_size = mid_size + 1  # Try larger
                else:
                    max_size = mid_size - 1  # Try smaller
                    
            except Exception:
                # Fallback to simple calculation if getbbox fails
                return max(12, int(min(target_width / len(text), target_height)))
        
        return max(8, best_size)
    
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