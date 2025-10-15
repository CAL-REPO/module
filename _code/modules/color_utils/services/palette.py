# -*- coding: utf-8 -*-
"""Color palette management.

Predefined palettes, palette loading, and manipulation.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Union
from pathlib import Path

from color_utils.core.models import Color, ColorPalette
from color_utils.services.converter import to_rgba

__all__ = [
    "create_palette",
    "load_palette_from_config",
    "BASIC_PALETTE",
    "MATERIAL_PALETTE",
]


def create_palette(name: str, colors: Dict[str, Union[str, tuple, list]]) -> ColorPalette:
    """Create color palette from dictionary.
    
    Args:
        name: Palette name
        colors: Dictionary mapping color names to color values
        
    Returns:
        ColorPalette object
        
    Example:
        >>> palette = create_palette("my_palette", {
        ...     "primary": "#FF0000",
        ...     "secondary": [0, 255, 0],
        ...     "accent": "#0000FF"
        ... })
    """
    color_objects = {}
    
    for color_name, color_value in colors.items():
        r, g, b, a = to_rgba(color_value)
        color_objects[color_name] = Color(r, g, b, a)
    
    return ColorPalette(name=name, colors=color_objects)


def load_palette_from_config(config: Union[Dict, Path, str], section: Optional[str] = None) -> ColorPalette:
    """Load color palette from configuration.
    
    Args:
        config: YAML file path or dictionary
        section: Optional section name in config
        
    Returns:
        ColorPalette object
        
    Example YAML:
        ```yaml
        palette:
          name: "my_theme"
          colors:
            primary: "#FF0000"
            secondary: "#00FF00"
            accent: "#0000FF"
        ```
    """
    # Load from file if path provided
    if isinstance(config, (str, Path)):
        from structured_io import load_yaml
        data = load_yaml(config) or {}
    else:
        data = config
    
    # Extract section if specified
    if section:
        data = data.get(section, {})
    
    # Get palette info
    name = data.get("name", "unnamed")
    colors_data = data.get("colors", {})
    
    return create_palette(name, colors_data)


# Predefined palettes for common use
BASIC_PALETTE = create_palette("basic", {
    "black": "#000000",
    "white": "#FFFFFF",
    "red": "#FF0000",
    "green": "#00FF00",
    "blue": "#0000FF",
    "yellow": "#FFFF00",
    "cyan": "#00FFFF",
    "magenta": "#FF00FF",
    "gray": "#808080",
})


MATERIAL_PALETTE = create_palette("material", {
    "red": "#F44336",
    "pink": "#E91E63",
    "purple": "#9C27B0",
    "deep_purple": "#673AB7",
    "indigo": "#3F51B5",
    "blue": "#2196F3",
    "light_blue": "#03A9F4",
    "cyan": "#00BCD4",
    "teal": "#009688",
    "green": "#4CAF50",
    "light_green": "#8BC34A",
    "lime": "#CDDC39",
    "yellow": "#FFEB3B",
    "amber": "#FFC107",
    "orange": "#FF9800",
    "deep_orange": "#FF5722",
    "brown": "#795548",
    "gray": "#9E9E9E",
    "blue_gray": "#607D8B",
})


# Future extensions for GUI
# def interpolate_colors(color1: Color, color2: Color, steps: int) -> List[Color]:
#     """Create gradient between two colors"""
#     pass
#
# def get_complementary_color(color: Color) -> Color:
#     """Get complementary color"""
#     pass
#
# def lighten(color: Color, amount: float) -> Color:
#     """Lighten color by percentage"""
#     pass
#
# def darken(color: Color, amount: float) -> Color:
#     """Darken color by percentage"""
#     pass
