# -*- coding: utf-8 -*-
# pillow_utils/loader.py
"""
모듈 설명: 이미지 로드 및 메타데이터 추출 담당 클래스 (FSOOpsPolicy + Logger 연동)
"""
from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageOps
from fso_utils import FSOOps, FSOOpsPolicy, ExistencePolicy
from log_utils import LogManager
from .model import ImageMeta
from .policy import ImagePolicy

class ImageLoader:
    def __init__(self, policy: ImagePolicy):
        self.policy = policy
        logger_args = self.policy.get_logger_args()
        self.logger = LogManager("pillow_loader", **logger_args).setup()
        # 파일 정책: must_exist=False (기본)
        self.fso = FSOOps(
            self.policy.file.path,
            policy=FSOOpsPolicy(
                as_type="file",
                exist=ExistencePolicy(must_exist=self.policy.file.must_exist)
            )
        )

    def load(self):
        path = self.fso.path
        self.logger.info(f"이미지 로드 시도: {path}")
        im = Image.open(path)
        im = ImageOps.exif_transpose(im)
        if self.policy.file.convert_mode:
            im = im.convert(self.policy.file.convert_mode)
        meta = self._extract_meta(im, path)
        self.logger.info(f"이미지 로드 완료: {meta.width}x{meta.height}, {meta.mode}")
        return im, meta

    def _extract_meta(self, im: Image.Image, path: Path) -> ImageMeta:
        exif = im.getexif()
        exif_len = len(exif.tobytes()) if exif else 0
        return ImageMeta(
            src_path=str(path),
            width=im.width,
            height=im.height,
            mode=im.mode,
            format=im.format,
            file_size=path.stat().st_size if path.exists() else None,
            exif_bytes_len=exif_len
        )