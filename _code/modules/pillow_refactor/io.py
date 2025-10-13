# -*- coding: utf-8 -*-
# pillow_refactor/io.py

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PIL import Image, ImageOps

from fso_utils.core.ops import FSOOps
from fso_utils.core.policy import (
    FSOOpsPolicy,
    ExistencePolicy,
    FileExtensionPolicy,
    FSONamePolicy,
)
from fso_utils.core.path_builder import FSOPathBuilder

from .models import ImageMeta
from .policy import ImageSourcePolicy, ImageTargetPolicy, ImageMetaPolicy


class ImageReader:
    """Load images from disk according to ImageSourcePolicy."""

    def __init__(self, policy: ImageSourcePolicy):
        self.policy = policy
        self._fso = FSOOps(
            policy.path,
            policy=FSOOpsPolicy(
                as_type="file",
                exist=ExistencePolicy(must_exist=policy.must_exist),
            ),
        )

    def load(self) -> tuple[Image.Image, ImageMeta]:
        path = self._fso.path
        image = Image.open(path)
        image = ImageOps.exif_transpose(image)
        if self.policy.convert_mode:
            image = image.convert(self.policy.convert_mode)
        meta = self._collect_meta(image, path)
        return image, meta

    @staticmethod
    def _collect_meta(image: Image.Image, path: Path) -> ImageMeta:
        exif = image.getexif()
        exif_len = len(exif.tobytes()) if exif else 0
        file_size = path.stat().st_size if path.exists() else None
        return ImageMeta(
            src_path=path,
            width=image.width,
            height=image.height,
            mode=image.mode,
            format=image.format,
            file_size=file_size,
            exif_bytes_len=exif_len,
        )


class ImageWriter:
    """Persist processed images and metadata using target policies."""

    def __init__(self, target_policy: ImageTargetPolicy, meta_policy: ImageMetaPolicy):
        self.target_policy = target_policy
        self.meta_policy = meta_policy

    def save_image(self, image: Image.Image, base_path: Path) -> Path:
        target_path = self._build_target_path(base_path)
        format_hint = self.target_policy.format or image.format or target_path.suffix.lstrip(".").upper()
        save_kwargs = {}
        if format_hint.upper() in {"JPEG", "JPG", "WEBP"}:
            save_kwargs["quality"] = self.target_policy.quality
        image.save(target_path, format=format_hint, **save_kwargs)
        return target_path

    def save_meta(self, meta: ImageMeta, base_path: Path) -> Optional[Path]:
        if not self.meta_policy.enabled:
            return None
        directory = self.meta_policy.directory or base_path.parent
        directory.mkdir(parents=True, exist_ok=True)
        filename = self.meta_policy.filename.format(
            stem=base_path.stem,
            suffix=self.target_policy.suffix,
        )
        path = directory / filename
        from fso_utils.core.io import JsonFileIO
        JsonFileIO(
            path,
            ops_policy=FSOOpsPolicy(as_type="file", exist=ExistencePolicy(create_if_missing=True)),
        ).write(meta.__dict__)
        return path

    def _build_target_path(self, base_path: Path) -> Path:
        directory = self.target_policy.directory or base_path.parent
        directory = directory.resolve()
        extension = (
            self.target_policy.format.lower()
            if self.target_policy.format
            else base_path.suffix.lstrip(".")
        )
        stem = base_path.stem
        formatted_name = self.target_policy.filename_template.format(
            stem=stem,
            suffix=self.target_policy.suffix,
            ext=f".{extension}" if extension else "",
        )
        name_part = Path(formatted_name).stem
        ext_part = Path(formatted_name).suffix or (f".{extension}" if extension else "")
        builder = FSOPathBuilder(
            base_dir=directory,
            name_policy=FSONamePolicy(
                as_type="file",
                name=name_part,
                extension=ext_part,
                tail_mode="counter" if self.target_policy.ensure_unique else None,
                ensure_unique=self.target_policy.ensure_unique,
            ),
            ops_policy=FSOOpsPolicy(
                as_type="file",
                exist=ExistencePolicy(create_if_missing=True),
                ext=FileExtensionPolicy(default_ext=ext_part or None),
            ),
        )
        return builder()

