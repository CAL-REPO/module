# -*- coding: utf-8 -*-
# font_utils/policy.py
"""Pydantic policies for font_utils.

Font configuration policy used across overlay and text rendering operations.
Supports:
- BaseModel defaults
- YAML config loading
- Runtime **kwargs override
- OS-specific default font directories
"""

from __future__ import annotations

import platform
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class FontPolicy(BaseModel):
    """Font configuration for text overlay and rendering.
    
    Attributes:
        font_dir: Custom font directory to load fonts from (None = OS default)
        family: Font family or path (None = Pillow default)
        size: Font size in pixels (None = auto-fit)
        fill: Text color
        stroke_fill: Stroke color (None = no stroke)
        stroke_width: Stroke width in pixels
    
    Note:
        If font_dir is None, defaults to OS-specific font directory:
        - Windows: C:/Windows/Fonts
        - macOS: /Library/Fonts or /System/Library/Fonts
        - Linux: /usr/share/fonts
    """
    font_dir: Optional[str] = Field(None, description="Custom font directory to load fonts from")
    family: Optional[str] = Field(
        None, description="Font family or path (None = Pillow default)"
    )
    size: Optional[int] = Field(
        None, description="Font size in pixels (None = auto-fit)"
    )
    fill: str = Field("#000000", description="Text color")
    stroke_fill: Optional[str] = Field(None, description="Stroke color")
    stroke_width: int = Field(0, ge=0, description="Stroke width")
    
    @model_validator(mode="after")
    def set_default_font_dir(self):
        """Set OS-specific default font directory if not provided.
        
        Returns:
            self with font_dir set to OS default if it was None
        """
        if self.font_dir is None:
            system = platform.system()
            
            if system == "Windows":
                self.font_dir = "C:/Windows/Fonts"
            elif system == "Darwin":  # macOS
                # Try user fonts first, then system fonts
                user_fonts = Path.home() / "Library" / "Fonts"
                if user_fonts.exists():
                    self.font_dir = str(user_fonts)
                else:
                    self.font_dir = "/Library/Fonts"
            elif system == "Linux":
                self.font_dir = "/usr/share/fonts"
            else:
                # Unknown OS, keep None
                pass
        
        return self
