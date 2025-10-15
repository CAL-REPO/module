# -*- coding: utf-8 -*-
"""Font validation utilities.

Validates font files, configurations, and rendering parameters.
"""

from __future__ import annotations

from typing import Optional, List
from pathlib import Path

__all__ = [
    "is_valid_font_file",
    "validate_font_size",
    "validate_font_config",
]


def is_valid_font_file(path: Path) -> bool:
    """Check if file is a valid font file.
    
    Args:
        path: Path to potential font file
        
    Returns:
        True if file exists and has valid font extension
    """
    if not path.exists() or not path.is_file():
        return False
    
    valid_extensions = {".ttf", ".otf", ".ttc", ".TTF", ".OTF", ".TTC"}
    return path.suffix in valid_extensions


def validate_font_size(size: int, *, min_size: int = 6, max_size: int = 500) -> bool:
    """Validate font size is within reasonable bounds.
    
    Args:
        size: Font size in pixels
        min_size: Minimum allowed size (default: 6)
        max_size: Maximum allowed size (default: 500)
        
    Returns:
        True if size is valid
    """
    return min_size <= size <= max_size


def validate_font_config(
    config: dict,
    *,
    required_langs: Optional[List[str]] = None
) -> tuple[bool, List[str]]:
    """Validate font configuration dictionary.
    
    Args:
        config: Font configuration to validate
        required_langs: Languages that must be present (None = no requirement)
        
    Returns:
        Tuple of (is_valid, list_of_errors)
        
    Example:
        >>> config = {"ko": ["NanumGothic"], "en": "Arial"}
        >>> is_valid, errors = validate_font_config(config, required_langs=["ko", "en"])
        >>> is_valid
        True
    """
    errors = []
    
    if not isinstance(config, dict):
        errors.append("Config must be a dictionary")
        return False, errors
    
    # Check required languages
    if required_langs:
        for lang in required_langs:
            if lang not in config:
                errors.append(f"Missing required language: {lang}")
    
    # Validate each entry
    for lang, fonts in config.items():
        if not isinstance(lang, str):
            errors.append(f"Language key must be string: {lang}")
        
        if fonts is None:
            continue
        
        if isinstance(fonts, (list, tuple)):
            if not fonts:
                errors.append(f"Empty font list for language: {lang}")
            for font in fonts:
                if not isinstance(font, str):
                    errors.append(f"Font name must be string in {lang}: {font}")
        elif not isinstance(fonts, str):
            errors.append(f"Font value must be string or list for {lang}: {type(fonts)}")
    
    return len(errors) == 0, errors


# Future extensions for GUI
# def check_font_rendering_capability(font_path: Path, text: str) -> bool:
#     """Check if font can render given text"""
#     pass
#
# def get_missing_glyphs(font_path: Path, text: str) -> List[str]:
#     """Get list of characters that font cannot render"""
#     pass
