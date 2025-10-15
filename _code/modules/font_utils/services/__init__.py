# -*- coding: utf-8 -*-
"""Font services - loading, selection, and language detection."""

from font_utils.services.detector import (
    is_lang_char,
    detect_char_lang,
    segment_text_by_lang,
)

from font_utils.services.loader import (
    load_font,
    find_font_file,
    get_fonts_directory,
)

from font_utils.services.selector import (
    select_font_for_lang,
    extract_font_map_from_config,
)

__all__ = [
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
]
