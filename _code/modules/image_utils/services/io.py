# -*- coding: utf-8 -*-
# pillow_utils/io.py
"""Image I/O utilities for reading and writing images with metadata.

Uses dict for metadata instead of ImageMetaResult dataclass.
Compatible with new policy structure.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

from PIL import Image, ImageOps

from fso_utils.core.ops import FSOOps
from fso_utils.core.policy import (
    FSOOpsPolicy,
    ExistencePolicy,
    FileExtensionPolicy,
    FSONamePolicy,
)
from fso_utils.core.path_builder import FSOPathBuilder

from ..core.policy import ImageSourcePolicy, ImagePolicy, ImageMetaPolicy


class ImageReader:
    """Load images from disk with metadata collection."""

    def __init__(self, policy: ImageSourcePolicy):
        self.policy = policy
        self._fso = FSOOps(
            policy.path,
            policy=FSOOpsPolicy(
                as_type="file",
                exist=ExistencePolicy(must_exist=policy.must_exist), # pyright: ignore[reportCallIssue]
            ),
        )

    def load(self) -> Tuple[Image.Image, Dict[str, Any]]:
        """Load image and collect metadata as dict."""
        path = self._fso.path
        image = Image.open(path)
        image = ImageOps.exif_transpose(image)
        if self.policy.convert_mode:
            image = image.convert(self.policy.convert_mode)
        meta = self._collect_meta(image, path)
        return image, meta

    @staticmethod
    def _collect_meta(image: Image.Image, path: Path) -> Dict[str, Any]:
        """Collect image metadata as dict instead of dataclass."""
        exif = image.getexif()
        exif_len = len(exif.tobytes()) if exif else 0
        file_size = path.stat().st_size if path.exists() else None
        
        return {
            "src_path": str(path),
            "width": image.width,
            "height": image.height,
            "mode": image.mode,
            "format": image.format,
            "file_size": file_size,
            "exif_bytes_len": exif_len,
        }


class ImageWriter:
    """Persist images and metadata with new policy structure."""

    def __init__(self, target_policy: ImagePolicy, meta_policy: ImageMetaPolicy):
        self.target_policy = target_policy
        self.meta_policy = meta_policy

    def save_image(self, image: Image.Image, base_path: Path) -> Path:
        """Save image to disk using target policy."""
        target_path = self._build_target_path(base_path)
        format_hint = self.target_policy.format or image.format or target_path.suffix.lstrip(".").upper()
        
        # Normalize JPG to JPEG (PIL only supports 'JPEG')
        if format_hint.upper() == "JPG":
            format_hint = "JPEG"
        
        save_kwargs = {}
        if format_hint.upper() in {"JPEG", "WEBP"}:
            save_kwargs["quality"] = self.target_policy.quality
        image.save(target_path, format=format_hint, **save_kwargs)
        return target_path

    def save_meta(self, meta: Dict[str, Any], base_path: Path) -> Optional[Path]:
        """Save metadata dict to JSON file."""
        if not self.meta_policy.save_meta:
            return None
        
        directory = self.meta_policy.directory or base_path.parent
        directory.mkdir(parents=True, exist_ok=True)
        
        # Determine filename
        if self.meta_policy.filename:
            filename = self.meta_policy.filename
        else:
            filename = f"{base_path.stem}_meta.json"
        
        path = directory / filename
        path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def _build_target_path(self, base_path: Path) -> Path:
        """Build target path using new ImagePolicy structure."""
        directory = self.target_policy.directory or base_path.parent
        directory = directory.resolve()
        
        # Determine filename
        if self.target_policy.filename:
            name = self.target_policy.filename
        else:
            ext = self.target_policy.format or base_path.suffix.lstrip(".")
            name = f"{base_path.stem}{self.target_policy.suffix}.{ext}" if ext else f"{base_path.stem}{self.target_policy.suffix}"
        
        name_part = Path(name).stem
        ext_part = Path(name).suffix
        
        builder = FSOPathBuilder(
            base_dir=directory,
            name_policy=FSONamePolicy(
                as_type="file",
                name=name_part,
                extension=ext_part,
                tail_mode="counter" if self.target_policy.ensure_unique else None,
                ensure_unique=self.target_policy.ensure_unique,
            ), # pyright: ignore[reportCallIssue]
            ops_policy=FSOOpsPolicy(
                as_type="file",
                exist=ExistencePolicy(create_if_missing=True), # pyright: ignore[reportCallIssue]
                ext=FileExtensionPolicy(default_ext=ext_part or None), # pyright: ignore[reportCallIssue]
            ),
        )
        return builder()

