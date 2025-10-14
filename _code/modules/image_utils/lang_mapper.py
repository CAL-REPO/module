"""Language code normalization for OCR providers."""

from __future__ import annotations


def map_lang_to_paddle(code: str) -> str:
    """Map various language codes to Paddle's short codes."""
    s = (code or "").strip().lower()
    if s in {"ch", "chi", "zh", "zh_cn", "ch_sim", "chinese"}:
        return "ch"
    if s in {"en", "eng", "english"}:
        return "en"
    if s in {"ko", "kor", "korean"}:
        return "ch"  # fallback for Korean
    return "en"
