# -*- coding: utf-8 -*-
"""Color conversion utilities.

Convert between different color formats: hex, RGB, RGBA, CSS-like strings.
No Pillow dependency - pure Python implementation.
"""

from __future__ import annotations

from typing import Any, Tuple, Union

__all__ = [
    "to_rgb",
    "to_rgba",
    "to_hex",
    "parse_css_color",
]

# Type aliases
RGB = Tuple[int, int, int]
RGBA = Tuple[int, int, int, int]


def _clamp255(x: int) -> int:
    """Clamp value to 0-255 range."""
    return max(0, min(255, int(x)))


def _from_hex(s: str) -> RGBA:
    """Parse hex color string to RGBA.
    
    Args:
        s: Hex string like "#RGB", "#RRGGBB", or "#RRGGBBAA"
        
    Returns:
        RGBA tuple (0-255)
    """
    s = s.strip().lstrip("#")
    
    # Short form: #RGB -> #RRGGBB
    if len(s) == 3:
        r = int(s[0] * 2, 16)
        g = int(s[1] * 2, 16)
        b = int(s[2] * 2, 16)
        return (r, g, b, 255)
    
    # Standard form: #RRGGBB
    if len(s) == 6:
        r = int(s[0:2], 16)
        g = int(s[2:4], 16)
        b = int(s[4:6], 16)
        return (r, g, b, 255)
    
    # With alpha: #RRGGBBAA
    if len(s) == 8:
        r = int(s[0:2], 16)
        g = int(s[2:4], 16)
        b = int(s[4:6], 16)
        a = int(s[6:8], 16)
        return (r, g, b, a)
    
    # Invalid format
    return (0, 0, 0, 0)


def parse_css_color(s: str) -> RGBA:
    """Parse CSS-like color string.
    
    Supports:
    - "rgb(r, g, b)"
    - "rgba(r, g, b, a)"
    
    Args:
        s: CSS color string
        
    Returns:
        RGBA tuple (0-255)
    """
    s = s.strip().lower()
    
    if not (s.startswith("rgb") and "(" in s and ")" in s):
        return (0, 0, 0, 0)
    
    try:
        # Extract content between parentheses
        inside = s[s.index("(") + 1 : s.rindex(")")]
        
        # Parse comma-separated values
        parts = [x.strip() for x in inside.split(",")]
        
        if len(parts) == 3:
            # rgb(r, g, b)
            r, g, b = [int(x) for x in parts]
            return (_clamp255(r), _clamp255(g), _clamp255(b), 255)
        
        if len(parts) == 4:
            # rgba(r, g, b, a) - a can be 0-255 or 0.0-1.0
            r, g, b = [int(x) for x in parts[:3]]
            a_val = float(parts[3])
            
            # If alpha is 0-1, convert to 0-255
            if 0.0 <= a_val <= 1.0:
                a = int(a_val * 255)
            else:
                a = int(a_val)
            
            return (_clamp255(r), _clamp255(g), _clamp255(b), _clamp255(a))
    
    except (ValueError, IndexError):
        pass
    
    return (0, 0, 0, 0)


def to_rgba(value: Any) -> RGBA:
    """Convert any color format to RGBA tuple.
    
    Supported formats:
    - Hex string: "#RRGGBB", "#RRGGBBAA", "#RGB"
    - RGB tuple/list: [r, g, b]
    - RGBA tuple/list: [r, g, b, a]
    - CSS-like: "rgb(r,g,b)", "rgba(r,g,b,a)"
    - None: returns transparent black (0, 0, 0, 0)
    
    Args:
        value: Color in any supported format
        
    Returns:
        RGBA tuple with values 0-255
        
    Example:
        >>> to_rgba("#FF0000")
        (255, 0, 0, 255)
        
        >>> to_rgba([128, 128, 128])
        (128, 128, 128, 255)
        
        >>> to_rgba("rgb(255, 0, 0)")
        (255, 0, 0, 255)
    """
    if value is None:
        return (0, 0, 0, 0)
    
    # List or tuple
    if isinstance(value, (list, tuple)):
        if len(value) == 3:
            r, g, b = (_clamp255(x) for x in value)
            return (r, g, b, 255)
        
        if len(value) == 4:
            r, g, b, a = (_clamp255(x) for x in value)
            return (r, g, b, a)
        
        return (0, 0, 0, 0)
    
    # String
    s = str(value).strip()
    
    # Hex format
    if s.startswith("#"):
        return _from_hex(s)
    
    # CSS format
    if s.lower().startswith("rgb"):
        return parse_css_color(s)
    
    # Unsupported format
    return (0, 0, 0, 0)


def to_rgb(value: Any) -> RGB:
    """Convert any color format to RGB tuple (drops alpha).
    
    Args:
        value: Color in any supported format
        
    Returns:
        RGB tuple with values 0-255
        
    Example:
        >>> to_rgb("#FF0000")
        (255, 0, 0)
    """
    r, g, b, _ = to_rgba(value)
    return (r, g, b)


def to_hex(value: Any, *, include_alpha: bool = False) -> str:
    """Convert any color format to hex string.
    
    Args:
        value: Color in any supported format
        include_alpha: Include alpha channel in output
        
    Returns:
        Hex color string ("#RRGGBB" or "#RRGGBBAA")
        
    Example:
        >>> to_hex([255, 0, 0])
        "#FF0000"
        
        >>> to_hex([255, 0, 0, 128], include_alpha=True)
        "#FF000080"
    """
    r, g, b, a = to_rgba(value)
    
    if include_alpha:
        return f"#{r:02X}{g:02X}{b:02X}{a:02X}"
    
    return f"#{r:02X}{g:02X}{b:02X}"


# Future extensions for GUI
# def to_hsl(value: Any) -> Tuple[float, float, float]:
#     """Convert to HSL (Hue, Saturation, Lightness)"""
#     pass
#
# def to_hsv(value: Any) -> Tuple[float, float, float]:
#     """Convert to HSV (Hue, Saturation, Value)"""
#     pass
#
# def from_hsl(h: float, s: float, l: float) -> RGB:
#     """Convert from HSL to RGB"""
#     pass
