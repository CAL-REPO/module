# -*- coding: utf-8 -*-
"""Font utilities - configuration, loading, selection, and language detection.

Modular structure:
    - core/: Policy and models
    - services/: Font loading, selection, language detection
    - utils/: Validation utilities

Public API:
    - FontPolicy: Pydantic policy for font configuration
    - load_font, find_font_file: Font file operations
    - select_font_for_lang: Language-aware font selection
    - detect_char_lang, segment_text_by_lang: Language detection
    - is_valid_font_file, validate_font_config: Validation
"""

# Core API
from font_utils.core import (
    FontPolicy,
    FontInfo,
    TextSegment,
    FontMetrics,
)

# Services API
from font_utils.services import (
    # Language detection
    is_lang_char,
    detect_char_lang,
    segment_text_by_lang,
    
    # Font loading
    load_font,
    find_font_file,
    get_fonts_directory,
    
    # Font selection
    select_font_for_lang,
    extract_font_map_from_config,
)

# Utils API
from font_utils.utils import (
    is_valid_font_file,
    validate_font_size,
    validate_font_config,
)

__all__ = [
    # Core
    "FontPolicy",
    "FontInfo",
    "TextSegment",
    "FontMetrics",
    
    # Language detection
    "is_lang_char",
    "detect_char_lang",
    "segment_text_by_lang",
    
    # Font loading
    "load_font",
    "find_font_file",
    "get_fonts_directory",
    
    # Font selection
    "select_font_for_lang",
    "extract_font_map_from_config",
    
    # Validation
    "is_valid_font_file",
    "validate_font_size",
    "validate_font_config",
]
