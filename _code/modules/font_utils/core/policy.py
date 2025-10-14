# -*- coding: utf-8 -*-
# font_utils/policy.py
"""Pydantic policies for font_utils.

Font configuration policy used across overlay and text rendering operations.
Supports:
- BaseModel defaults
- YAML config loading
- Runtime **kwargs override
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class FontPolicy(BaseModel):
    """Font configuration for text overlay and rendering.
    
    Attributes:
        family: Font family or path (None = Pillow default)
        size: Font size in pixels (None = auto-fit)
        fill: Text color
        stroke_fill: Stroke color (None = no stroke)
        stroke_width: Stroke width in pixels
    """
    family: Optional[str] = Field(
        None, description="Font family or path (None = Pillow default)"
    )
    size: Optional[int] = Field(
        None, description="Font size in pixels (None = auto-fit)"
    )
    fill: str = Field("#000000", description="Text color")
    stroke_fill: Optional[str] = Field(None, description="Stroke color")
    stroke_width: int = Field(0, ge=0, description="Stroke width")
