# -*- coding: utf-8 -*-
"""Color-related data models.

Simple data containers for color information, palettes, themes, etc.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple, Optional, List


# Type aliases
RGB = Tuple[int, int, int]
RGBA = Tuple[int, int, int, int]
HexColor = str  # "#RRGGBB" or "#RRGGBBAA"


@dataclass
class Color:
    """Unified color representation.
    
    Stores color in RGBA format (0-255) and provides conversions.
    
    Attributes:
        r: Red component (0-255)
        g: Green component (0-255)
        b: Blue component (0-255)
        a: Alpha component (0-255), 255 = fully opaque
    """
    r: int
    g: int
    b: int
    a: int = 255
    
    @property
    def rgb(self) -> RGB:
        """Get RGB tuple."""
        return (self.r, self.g, self.b)
    
    @property
    def rgba(self) -> RGBA:
        """Get RGBA tuple."""
        return (self.r, self.g, self.b, self.a)
    
    @property
    def hex(self) -> str:
        """Get hex color string (#RRGGBB or #RRGGBBAA)."""
        if self.a == 255:
            return f"#{self.r:02X}{self.g:02X}{self.b:02X}"
        return f"#{self.r:02X}{self.g:02X}{self.b:02X}{self.a:02X}"
    
    @property
    def opacity(self) -> float:
        """Get opacity as float (0.0-1.0)."""
        return self.a / 255.0
    
    def with_alpha(self, alpha: int) -> 'Color':
        """Create new color with different alpha."""
        return Color(self.r, self.g, self.b, alpha)
    
    def with_opacity(self, opacity: float) -> 'Color':
        """Create new color with different opacity (0.0-1.0)."""
        return Color(self.r, self.g, self.b, int(opacity * 255))


@dataclass
class ColorPalette:
    """Collection of related colors.
    
    Useful for themes, UI design, etc.
    
    Attributes:
        name: Palette name
        colors: Dictionary of color names to Color objects
    """
    name: str
    colors: dict[str, Color]
    
    def get(self, name: str, default: Optional[Color] = None) -> Optional[Color]:
        """Get color by name."""
        return self.colors.get(name, default)
    
    def __getitem__(self, name: str) -> Color:
        """Get color by name (raises KeyError if not found)."""
        return self.colors[name]


# Future extensions for GUI
# @dataclass
# class Theme:
#     """UI theme with multiple palettes (light/dark mode, etc.)"""
#     name: str
#     primary: ColorPalette
#     secondary: Optional[ColorPalette] = None
#     accent: Optional[ColorPalette] = None
#
# @dataclass
# class Gradient:
#     """Color gradient definition"""
#     colors: List[Color]
#     stops: Optional[List[float]] = None  # 0.0-1.0
