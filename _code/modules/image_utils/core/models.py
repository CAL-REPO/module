# -*- coding: utf-8 -*-
# image_utils/core/models.py
"""Data models for image_utils.

This module contains pure data models (non-policy classes) used across image_utils.
"""

from __future__ import annotations

from typing import Dict, List
from pydantic import BaseModel, Field


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
