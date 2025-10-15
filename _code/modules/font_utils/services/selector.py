# -*- coding: utf-8 -*-
"""Font selection based on language and configuration.

Selects appropriate font for given language from configuration.
Integrates with detector for language-aware rendering.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Union, Any
from pathlib import Path

from font_utils.services.loader import load_font, find_font_file, get_fonts_directory

try:
    from PIL import ImageFont
    PILLOW_AVAILABLE = True
except ImportError:
    ImageFont = None
    PILLOW_AVAILABLE = False

__all__ = [
    "select_font_for_lang",
    "extract_font_map_from_config",
]


def select_font_for_lang(
    lang: str,
    fonts_map: Dict[str, List[str]],
    *,
    size: int = 28,
    fonts_dir: Optional[Path] = None,
):
    """Select and load font for specified language.
    
    Args:
        lang: Language code (ko, en, zh, ja, etc.)
        fonts_map: Mapping of language -> list of font filenames
        size: Font size in pixels
        fonts_dir: Fonts directory (None = use default)
        
    Returns:
        PIL ImageFont object (falls back to default font if none found)
        
    Raises:
        ImportError: If Pillow is not installed
        
    Example:
        >>> fonts_map = {"ko": ["NanumGothic", "Malgun Gothic"], "en": ["Arial"]}
        >>> font = select_font_for_lang("ko", fonts_map, size=24)
    """
    if not PILLOW_AVAILABLE:
        raise ImportError("Pillow is required. Install with: pip install pillow")
    
    if fonts_dir is None:
        fonts_dir = get_fonts_directory()
    
    # Get candidate fonts for language (with fallbacks)
    candidates = (
        fonts_map.get(lang) or
        fonts_map.get("other") or
        fonts_map.get("en") or
        []
    )
    
    # Try each candidate font
    for font_name in candidates:
        font_path = find_font_file(font_name, fonts_dir)
        if font_path is None:
            continue
        
        try:
            return load_font(str(font_path.resolve()), int(size))
        except Exception:
            continue
    
    # Fallback to PIL default font
    return ImageFont.load_default()


def extract_font_map_from_config(config: Union[Dict[str, Any], Path, str]) -> Dict[str, List[str]]:
    """Extract language->fonts mapping from configuration.
    
    Supports both YAML files and dict objects.
    Normalizes font names to lists.
    
    Args:
        config: YAML file path, dict, or config object
        
    Returns:
        Dictionary mapping language codes to lists of font names
        
    Example YAML structure:
        ```yaml
        fonts:
          ko: ["NanumGothic", "Malgun Gothic"]
          en: "Arial"
          zh: "SimSun"
          other: "NanumGothic"
        ```
        
    Example dict structure:
        ```python
        {
            "fonts": {
                "ko": ["NanumGothic", "Malgun Gothic"],
                "en": "Arial"
            }
        }
        ```
    """
    # Load from file if path provided
    if isinstance(config, (str, Path)):
        from structured_io import load_yaml
        root = load_yaml(config) or {}
    elif isinstance(config, dict):
        root = config
    else:
        return {}
    
    # Try to find fonts section
    # Support both {"fonts": {...}} and top-level structure
    fonts_data = None
    
    # First try "fonts" key
    if "fonts" in root:
        fonts_data = root["fonts"]
    # Try "overlay" section (legacy compatibility)
    elif "overlay" in root and isinstance(root["overlay"], dict):
        if "fonts" in root["overlay"]:
            fonts_data = root["overlay"]["fonts"]
    
    if not isinstance(fonts_data, dict):
        return {}
    
    # Normalize to Dict[str, List[str]]
    result: Dict[str, List[str]] = {}
    for lang, value in fonts_data.items():
        if value is None:
            continue
        
        if isinstance(value, (list, tuple)):
            result[lang] = [str(x) for x in value]
        else:
            result[lang] = [str(value)]
    
    return result


# Future extensions for GUI
# def select_font_family(family_name: str, style: str = "regular", weight: int = 400) -> Optional[Path]:
#     """Select font by family name and style"""
#     pass
#
# def get_best_font_for_text(text: str, fonts_map: Dict, size: int) -> ImageFont:
#     """Automatically select best font based on text content"""
#     pass
