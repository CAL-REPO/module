# -*- coding: utf-8 -*-
"""Color utilities - conversion, validation, and palette management.

Modular structure:
    - core/: Models and policies
    - services/: Color conversion and palette management
    - utils/: Validation utilities

Public API:
    - to_rgba, to_rgb, to_hex: Color format conversions
    - Color, ColorPalette: Data models
    - ColorPolicy: Pydantic policy for color configuration
    - is_valid_color, is_valid_hex: Validation
    - BASIC_PALETTE, MATERIAL_PALETTE: Predefined palettes

No Pillow dependency - pure Python implementation.
"""

# Core API
from color_utils.core import (
    Color,
    ColorPalette,
    ColorPolicy,
    RGB,
    RGBA,
    HexColor,
)

# Services API
from color_utils.services import (
    # Conversion
    to_rgb,
    to_rgba,
    to_hex,
    parse_css_color,
    
    # Palette management
    create_palette,
    load_palette_from_config,
    BASIC_PALETTE,
    MATERIAL_PALETTE,
)

# Utils API
from color_utils.utils import (
    is_valid_rgb,
    is_valid_rgba,
    is_valid_hex,
    is_valid_color,
)

__all__ = [
    # Core
    "Color",
    "ColorPalette",
    "ColorPolicy",
    "RGB",
    "RGBA",
    "HexColor",
    
    # Conversion
    "to_rgb",
    "to_rgba",
    "to_hex",
    "parse_css_color",
    
    # Palette management
    "create_palette",
    "load_palette_from_config",
    "BASIC_PALETTE",
    "MATERIAL_PALETTE",
    
    # Validation
    "is_valid_rgb",
    "is_valid_rgba",
    "is_valid_hex",
    "is_valid_color",
]
