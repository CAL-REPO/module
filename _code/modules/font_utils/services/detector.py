# -*- coding: utf-8 -*-
"""Language detection for text rendering.

Lightweight character-based language detection for font selection.
Supports Korean, English, Chinese, Japanese, and common punctuation.
"""

from __future__ import annotations

from typing import List, Tuple, Optional

__all__ = [
    "is_lang_char",
    "detect_char_lang",
    "segment_text_by_lang",
]


def is_lang_char(ch: str, lang: str) -> bool:
    """Check if character belongs to specified language.
    
    Args:
        ch: Single character to check
        lang: Language code (ko, en, zh, ja, space, digit, punct, other)
        
    Returns:
        True if character belongs to language
    """
    if not ch:
        return False
    
    cp = ord(ch)
    
    if lang == "space":
        return ch.isspace()
    
    if lang == "digit":
        return ch.isdigit()
    
    if lang == "en":
        # Basic Latin alphabet (A-Z, a-z)
        return (0x41 <= cp <= 0x5A) or (0x61 <= cp <= 0x7A)
    
    if lang == "ko":
        # Hangul syllables + Hangul Jamo + Hangul Compatibility Jamo
        return (
            (0xAC00 <= cp <= 0xD7A3) or  # Hangul syllables
            (0x1100 <= cp <= 0x11FF) or  # Hangul Jamo
            (0x3130 <= cp <= 0x318F)     # Hangul Compatibility Jamo
        )
    
    if lang == "zh":
        # CJK Unified Ideographs (Chinese characters)
        return (
            (0x4E00 <= cp <= 0x9FFF) or  # CJK Unified Ideographs
            (0x3400 <= cp <= 0x4DBF)     # CJK Extension A
        )
    
    if lang == "ja":
        # Hiragana + Katakana
        return (
            (0x3040 <= cp <= 0x309F) or  # Hiragana
            (0x30A0 <= cp <= 0x30FF)     # Katakana
        )
    
    if lang == "punct":
        # Common punctuation and symbols
        return (
            (0x20 <= cp <= 0x40) or      # Space and ASCII punctuation
            (0x5B <= cp <= 0x60) or      # More ASCII punctuation
            (0x7B <= cp <= 0x7E)         # More ASCII punctuation
        )
    
    return True


def detect_char_lang(ch: str) -> str:
    """Detect language of a single character.
    
    Args:
        ch: Single character to analyze
        
    Returns:
        Language code (ko, en, zh, ja, space, digit, punct, other)
    """
    if not ch:
        return "other"
    
    # Check in priority order
    if is_lang_char(ch, "space"):
        return "space"
    
    if is_lang_char(ch, "digit"):
        return "digit"
    
    if is_lang_char(ch, "ko"):
        return "ko"
    
    if is_lang_char(ch, "en"):
        return "en"
    
    if is_lang_char(ch, "zh"):
        return "zh"
    
    if is_lang_char(ch, "ja"):
        return "ja"
    
    if is_lang_char(ch, "punct"):
        return "punct"
    
    return "other"


def segment_text_by_lang(text: str) -> List[Tuple[str, str]]:
    """Segment text into runs of the same language.
    
    Useful for multi-language text rendering with different fonts.
    Spaces are attached to the preceding language run.
    
    Args:
        text: Text to segment
        
    Returns:
        List of (language, text_run) tuples
        
    Example:
        >>> segment_text_by_lang("Hello 안녕 World")
        [('en', 'Hello '), ('ko', '안녕 '), ('en', 'World')]
    """
    segs: List[Tuple[str, str]] = []
    cur_lang: Optional[str] = None
    buf: List[str] = []
    
    for ch in text:
        lg = detect_char_lang(ch)
        
        # Attach spaces to previous run
        if lg == "space" and buf:
            buf.append(ch)
            continue
        
        # Start first run
        if cur_lang is None:
            cur_lang = lg
            buf.append(ch)
            continue
        
        # Continue current run
        if lg == cur_lang:
            buf.append(ch)
        else:
            # Save current run and start new one
            segs.append((cur_lang, "".join(buf)))
            cur_lang = lg
            buf = [ch]
    
    # Save last run
    if buf:
        segs.append((cur_lang or "other", "".join(buf)))
    
    return segs
