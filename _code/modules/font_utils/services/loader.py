# -*- coding: utf-8 -*-
"""Font file loading with caching.

Provides cached font loading to minimize disk access.
Thread-safe LRU cache for loaded fonts.
"""

from __future__ import annotations

from typing import Optional, List, Union
from pathlib import Path
from functools import lru_cache

try:
    from PIL import ImageFont
    PILLOW_AVAILABLE = True
except ImportError:
    ImageFont = None
    PILLOW_AVAILABLE = False

__all__ = [
    "load_font",
    "find_font_file",
    "get_fonts_directory",
]


def get_fonts_directory() -> Path:
    """Get the fonts directory path.
    
    Returns:
        Path to fonts directory (from path_utils)
    """
    from path_utils import fonts_dir
    return fonts_dir()


@lru_cache(maxsize=256)
def load_font(font_path: str, size: int):
    """Load font with LRU caching.
    
    Thread-safe cached loading to minimize disk access.
    
    Args:
        font_path: Absolute path to font file (string for hashability)
        size: Font size in pixels
        
    Returns:
        PIL ImageFont object
        
    Raises:
        ImportError: If Pillow is not installed
        OSError: If font file cannot be loaded
    """
    if not PILLOW_AVAILABLE:
        raise ImportError("Pillow is required for font loading. Install with: pip install pillow")
    
    return ImageFont.truetype(font_path, size=int(size))


def find_font_file(
    font_name: str,
    fonts_dir: Optional[Path] = None,
    extensions: Optional[List[str]] = None,
) -> Optional[Path]:
    """Find font file by name in fonts directory.
    
    Tries multiple extensions if not specified.
    
    Args:
        font_name: Font file name (with or without extension)
        fonts_dir: Directory to search (None = use default fonts_dir)
        extensions: Extensions to try (default: [.ttf, .otf, .ttc])
        
    Returns:
        Path to font file if found, None otherwise
        
    Example:
        >>> find_font_file("NanumGothic")
        Path("/path/to/fonts/NanumGothic.ttf")
        
        >>> find_font_file("Arial.ttf")
        Path("/path/to/fonts/Arial.ttf")
    """
    if fonts_dir is None:
        fonts_dir = get_fonts_directory()
    
    if extensions is None:
        extensions = [".ttf", ".otf", ".ttc", ".TTF", ".OTF", ".TTC"]
    
    font_path = Path(font_name)
    
    # If absolute path provided
    if font_path.is_absolute():
        if font_path.exists():
            return font_path
        return None
    
    # Relative to fonts_dir
    base_path = fonts_dir / font_path
    
    # If already has extension
    if base_path.suffix:
        if base_path.exists():
            return base_path
        return None
    
    # Try with different extensions
    for ext in extensions:
        candidate = base_path.with_suffix(ext)
        if candidate.exists():
            return candidate
    
    return None


def clear_font_cache():
    """Clear the font loading cache.
    
    Useful for testing or when fonts are updated.
    """
    load_font.cache_clear()


# Future extensions for GUI
# def list_available_fonts(fonts_dir: Optional[Path] = None) -> List[FontInfo]:
#     """List all available fonts in directory"""
#     pass
#
# def get_system_fonts() -> List[FontInfo]:
#     """Get list of system fonts (platform-specific)"""
#     pass
