# -*- coding: utf-8 -*-
# pillow_utils/saver.py
"""
모듈 설명: 이미지 및 메타데이터 저장 클래스 (FSOOpsPolicy + JsonFileIO + Logger 연동)
"""
from __future__ import annotations
from pathlib import Path
from PIL import Image
from fso_utils import FSOOps, FSOOpsPolicy, ExistencePolicy, FileExtensionPolicy, JsonFileIO
from log_utils import LogManager
from .policy import ImagePolicy, _IMAGE_EXTS, _FMT_MAP
from .model import ImageMeta

class ImageSaver:
    def __init__(self, policy: ImagePolicy):
        self.policy = policy
        logger_args = self.policy.get_logger_args()
        self.logger = LogManager("pillow_saver", **logger_args).setup()
        self.allowed_exts = list(_IMAGE_EXTS)

    def save_image(self, img: Image.Image):
        if not self.policy.save.enabled:
            self.logger.debug("이미지 저장 비활성화")
            return None

        # 디렉토리 정책 (필수 생성)
        dir_policy = FSOOpsPolicy(
            as_type="dir",
            exist=ExistencePolicy(create_if_missing=True)
        )
        out_dir = FSOOps(
            self.policy.save.directory or self.policy.file.path.parent,
            policy=dir_policy
        ).path

        # 확장자 정책 검증
        ext_policy = FSOOpsPolicy(
            as_type="file",
            ext=FileExtensionPolicy(
                require_ext=True,
                allowed_exts=self.allowed_exts
            )
        )

        out_name = f"{self.policy.file.path.stem}{self.policy.save.suffix}{self.policy.file.path.suffix}"
        out_path = out_dir / out_name
        ext_policy.apply_to(out_path)

        ext = out_path.suffix.lower()
        fmt = _FMT_MAP.get(ext, self.policy.save.format or "PNG")

        img.save(str(out_path), format=fmt, quality=self.policy.save.quality)
        self.logger.info(f"이미지 저장 완료: {out_path} ({fmt})")
        return out_path

    def save_meta(self, meta: ImageMeta):
        if not self.policy.meta.enabled:
            self.logger.debug("메타데이터 저장 비활성화")
            return None

        dir_policy = FSOOpsPolicy(as_type="dir", exist=ExistencePolicy(create_if_missing=True))
        out_dir = FSOOps(self.policy.meta.directory or self.policy.file.path.parent, policy=dir_policy).path
        path = out_dir / self.policy.meta.filename

        JsonFileIO(path, policy=FSOOpsPolicy(exist=ExistencePolicy(create_if_missing=True))).write(meta.__dict__)
        self.logger.info(f"메타데이터 저장 완료: {path}")
        return path
