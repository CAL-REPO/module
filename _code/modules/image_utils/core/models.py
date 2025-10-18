# -*- coding: utf-8 -*-
# image_utils/core/models.py
"""Data models for image_utils.

This module contains pure data models (non-policy classes) used across image_utils.
"""

from __future__ import annotations

from typing import Dict, List, Tuple, Optional, TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .policy import OverlayItemPolicy
    from font_utils import FontPolicy


class OCRItem(BaseModel):
    """Single OCR detection item.
    
    Attributes:
        text: Detected text content
        conf: Confidence score (0.0-1.0)
        quad: Quadrilateral coordinates [[x,y], [x,y], [x,y], [x,y]]
        bbox: Bounding box {x_min, y_min, x_max, y_max}
        angle_deg: Text rotation angle in degrees
        lang: Language code (e.g., 'ch', 'en')
        order: Detection order index
    """
    text: str = Field(..., description="Detected text content")
    conf: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    quad: List[List[float]] = Field(
        ..., 
        description="Quadrilateral coordinates [[x,y], [x,y], [x,y], [x,y]]"
    )
    bbox: Dict[str, float] = Field(
        ..., 
        description="Bounding box {x_min, y_min, x_max, y_max}"
    )
    angle_deg: float = Field(0.0, description="Text rotation angle in degrees")
    lang: str = Field("unknown", description="Language code")
    order: int = Field(0, description="Detection order index")
    
    def to_overlay_item(
        self,
        text_override: Optional[str] = None,
        font_policy: Optional["FontPolicy"] = None,
    ) -> "OverlayItemPolicy":
        """Convert OCRItem to OverlayItemPolicy for overlay rendering.
        
        This is a convenience method for pipeline scripts (e.g., oto.py).
        The overlay module itself doesn't need to know about OCRItem.
        
        Args:
            text_override: Override text (e.g., translated text). If None, uses self.text
            font_policy: Font policy for rendering. If None, uses default
        
        Returns:
            OverlayItemPolicy instance ready for ImageOverlayer
        
        Example:
            # In script/oto.py
            ocr_item = OCRItem(...)
            translated_text = translator.translate(ocr_item.text)
            overlay_item = ocr_item.to_overlay_item(text_override=translated_text)
        """
        from .policy import OverlayItemPolicy
        from font_utils import FontPolicy as FP
        
        # quad → polygon 변환 (List[List[float]] → List[Tuple[float, float]])
        polygon = [(p[0], p[1]) for p in self.quad]
        
        return OverlayItemPolicy(
            text=text_override if text_override is not None else self.text,
            polygon=polygon,
            font=font_policy or FP(),  # type: ignore
            # OCRItem 추가 정보 전달 (선택적)
            conf=self.conf,
            bbox=self.bbox,
            angle_deg=self.angle_deg,
            lang=self.lang,
        )
