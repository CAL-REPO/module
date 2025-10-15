# -*- coding: utf-8 -*-
"""Font-related data models.

Simple data containers for font information, language detection results, etc.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Optional
from pathlib import Path


@dataclass
class FontInfo:
    """Font file information.
    
    Attributes:
        path: Absolute path to font file
        family: Font family name (if available)
        style: Font style (regular, bold, italic, etc.)
        weight: Font weight (100-900)
        format: Font format (ttf, otf, ttc, etc.)
    """
    path: Path
    family: Optional[str] = None
    style: Optional[str] = None
    weight: Optional[int] = None
    format: Optional[str] = None


@dataclass
class TextSegment:
    """Text segment with language information.
    
    Used for language-aware text rendering.
    
    Attributes:
        text: Text content
        lang: Detected language code (ko, en, zh, ja, etc.)
        start: Start position in original text
        end: End position in original text
    """
    text: str
    lang: str
    start: int
    end: int


@dataclass
class FontMetrics:
    """Font rendering metrics for GUI layout.
    
    Attributes:
        ascent: Pixels above baseline
        descent: Pixels below baseline
        line_height: Total line height
        max_advance: Maximum character advance width
    """
    ascent: int
    descent: int
    line_height: int
    max_advance: int


# Future extensions for GUI
# @dataclass
# class FontFamily:
#     """Font family with variants (regular, bold, italic, etc.)"""
#     name: str
#     regular: Optional[Path] = None
#     bold: Optional[Path] = None
#     italic: Optional[Path] = None
#     bold_italic: Optional[Path] = None

# @dataclass
# class FontCollection:
#     """Collection of fonts for different purposes (UI, code, heading, etc.)"""
#     ui_font: Optional[FontFamily] = None
#     code_font: Optional[FontFamily] = None
#     heading_font: Optional[FontFamily] = None
