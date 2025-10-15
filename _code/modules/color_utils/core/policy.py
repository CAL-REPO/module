# -*- coding: utf-8 -*-
"""Pydantic policies for color_utils.

Color configuration policy for GUI, rendering, and styling.
"""

from __future__ import annotations

from typing import Union, Tuple, Optional
from pydantic import BaseModel, Field, field_validator


class ColorPolicy(BaseModel):
    """Color configuration policy.
    
    Supports multiple input formats:
    - Hex string: "#RRGGBB" or "#RRGGBBAA"
    - RGB tuple: [r, g, b]
    - RGBA tuple: [r, g, b, a]
    - CSS-like: "rgb(r,g,b)" or "rgba(r,g,b,a)"
    
    Attributes:
        value: Color value in any supported format
        opacity: Optional opacity override (0.0-1.0)
    """
    value: Union[str, Tuple[int, int, int], Tuple[int, int, int, int]] = Field(
        "#000000",
        description="Color value (hex, RGB, or RGBA)"
    )
    opacity: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Optional opacity override (0.0-1.0)"
    )
    
    @field_validator('opacity')
    @classmethod
    def validate_opacity(cls, v):
        """Ensure opacity is in valid range."""
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError("Opacity must be between 0.0 and 1.0")
        return v


# Future extensions for GUI
# class PalettePolicy(BaseModel):
#     """Color palette configuration"""
#     primary: ColorPolicy
#     secondary: Optional[ColorPolicy] = None
#     accent: Optional[ColorPolicy] = None
#     background: ColorPolicy = Field(default_factory=lambda: ColorPolicy(value="#FFFFFF"))
#     foreground: ColorPolicy = Field(default_factory=lambda: ColorPolicy(value="#000000"))
#
# class ThemePolicy(BaseModel):
#     """UI theme configuration"""
#     name: str
#     light: Optional[PalettePolicy] = None
#     dark: Optional[PalettePolicy] = None
