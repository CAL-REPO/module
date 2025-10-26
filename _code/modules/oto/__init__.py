# -*- coding: utf-8 -*-
"""
oto
---
OCR → Translate → Overlay Pipeline Module

Main Components:
- OTO: Adapter for OTO pipeline (OCR → Translate → Overlay)

Usage:
    >>> from oto import OTO
    >>> 
    >>> # From YAML config
    >>> oto = OTO("configs/oto.yaml")
    >>> result_image = oto.run(source_image)
    
    >>> # With runtime override
    >>> oto = OTO("config.yaml", ocr__threshold=0.8)
"""

from .adapter.oto import OTO
from .core.policy import OTOPolicy

__all__ = [
    "OTO",
    "OTOPolicy",
]
