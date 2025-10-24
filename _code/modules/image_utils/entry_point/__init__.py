# -*- coding: utf-8 -*-
"""Entry points for image_utils.

외부 진입점 (source 포함):
- ImageLoader: YAML 기반 이미지 로드 EntryPoint
- ImageOverlayer: YAML 기반 오버레이 EntryPoint
- ImageTextRecognizer: YAML 기반 OCR EntryPoint

EntryPoint는 source에서 데이터를 로드하여 Adapter에 전달합니다.
일반 사용자는 EntryPoint를 사용하고, 고급 사용자는 Adapter를 직접 사용할 수 있습니다.
"""

from .loader import ImageLoader
from .overlayer import ImageOverlayer
from .text_recognizer import ImageTextRecognizer

__all__ = [
    "ImageLoader",
    "ImageOverlayer",
    "ImageTextRecognizer",
]
