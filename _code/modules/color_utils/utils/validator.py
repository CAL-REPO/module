# -*- coding: utf-8 -*-
"""Color validation utilities.

Validates color values, formats, and configurations.
"""

from __future__ import annotations

from typing import Any, Tuple

__all__ = [
    "is_valid_rgb",
    "is_valid_rgba",
    "is_valid_hex",
    "is_valid_color",
]


def is_valid_rgb(value: Tuple[int, int, int]) -> bool:
    """Check if RGB tuple is valid.
    
    Args:
        value: RGB tuple to validate
        
    Returns:
        True if all components are in 0-255 range
    """
    if not isinstance(value, (tuple, list)) or len(value) != 3:
        return False
    
    try:
        r, g, b = value
        return all(0 <= x <= 255 for x in [r, g, b])
    except (TypeError, ValueError):
        return False


def is_valid_rgba(value: Tuple[int, int, int, int]) -> bool:
    """Check if RGBA tuple is valid.
    
    Args:
        value: RGBA tuple to validate
        
    Returns:
        True if all components are in 0-255 range
    """
    if not isinstance(value, (tuple, list)) or len(value) != 4:
        return False
    
    try:
        r, g, b, a = value
        return all(0 <= x <= 255 for x in [r, g, b, a])
    except (TypeError, ValueError):
        return False


def is_valid_hex(value: str) -> bool:
    """Check if hex color string is valid.
    
    Args:
        value: Hex string to validate
        
    Returns:
        True if valid hex format (#RGB, #RRGGBB, or #RRGGBBAA)
    """
    if not isinstance(value, str):
        return False
    
    s = value.strip().lstrip("#")
    
    # Valid lengths: 3 (RGB), 6 (RRGGBB), 8 (RRGGBBAA)
    if len(s) not in [3, 6, 8]:
        return False
    
    # Check if all characters are valid hex digits
    try:
        int(s, 16)
        return True
    except ValueError:
        return False


def is_valid_color(value: Any) -> bool:
    """Check if value is a valid color in any supported format.
    
    Args:
        value: Color value to validate
        
    Returns:
        True if valid color format
    """
    # None is considered invalid
    if value is None:
        return False
    
    # Hex string
    if isinstance(value, str):
        s = value.strip().lower()
        
        # Hex format
        if s.startswith("#"):
            return is_valid_hex(s)
        
        # CSS format (basic validation)
        if s.startswith("rgb"):
            return "(" in s and ")" in s
        
        return False
    
    # Tuple or list
    if isinstance(value, (tuple, list)):
        if len(value) == 3:
            return is_valid_rgb(value)
        if len(value) == 4:
            return is_valid_rgba(value)
        return False
    
    return False


# Future extensions for GUI
# def validate_palette(palette: Dict[str, Any]) -> Tuple[bool, List[str]]:
#     """Validate color palette configuration"""
#     pass
#
# def check_contrast_ratio(color1: Color, color2: Color) -> float:
#     """Calculate WCAG contrast ratio"""
#     pass
