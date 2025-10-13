# -*- coding: utf-8 -*-
# pillow_refactor/models.py

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PIL import Image


@dataclass(slots=True)
class ImageMeta:
    src_path: Path
    width: int
    height: int
    mode: str
    format: Optional[str]
    file_size: Optional[int]
    exif_bytes_len: Optional[int]


@dataclass(slots=True)
class ImagePipelineResult:
    image: Image.Image
    meta: ImageMeta
    saved_image_path: Optional[Path] = None
    saved_meta_path: Optional[Path] = None
