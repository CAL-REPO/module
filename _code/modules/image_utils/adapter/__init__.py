# -*- coding: utf-8 -*-
"""Adapters for image_utils.

비즈니스 로직 (source 없음):
- ImageLoad: 순수 이미지 로드 로직
- ImageOverlay: 순수 오버레이 로직
- ImageTextRecognize: 순수 OCR 로직

Adapter는 source를 받지 않고 데이터를 인자로 받아 처리합니다.
EntryPoint가 source에서 데이터를 로드하여 Adapter에 전달합니다.
"""

from .load import ImageLoad
from .overlay import ImageOverlay
from .text_recognize import ImageTextRecognize

__all__ = [
    "ImageLoad",
    "ImageOverlay",
    "ImageTextRecognize",
]
