# -*- coding: utf-8 -*-
# pillow_utils/model.py
"""
모듈 설명: 이미지 메타데이터 및 상태 모델 정의
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from pathlib import Path
from PIL import Image

@dataclass
class ImageMeta:
    src_path: str
    width: int
    height: int
    mode: str
    format: Optional[str]
    file_size: Optional[int]
    exif_bytes_len: Optional[int]

@dataclass
class ImageState:
    image: Image.Image
    meta: ImageMeta
    src_path: Path
    saved_image_path: Optional[Path] = None
    saved_meta_path: Optional[Path] = None