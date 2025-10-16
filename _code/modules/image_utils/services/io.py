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
from fso_utils.core.policy import FSOOpsPolicy, ExistencePolicy
from fso_utils.core.path_builder import FSOPathBuilder

from ..core.policy import ImageSourcePolicy, ImageSavePolicy, ImageMetaPolicy


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
    """Persist images and metadata using FSO_utils policies."""

    def __init__(self, target_policy: ImageSavePolicy, meta_policy: ImageMetaPolicy):
        self.target_policy = target_policy
        self.meta_policy = meta_policy

    def save_image(self, image: Image.Image, base_path: Path) -> Path:
        """Save image to disk using FSO-based target policy."""
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
        """Save metadata dict to JSON file using FSO policy."""
        if not self.meta_policy.save_meta:
            return None
        
        # Use FSO PathBuilder for metadata with name and ops policy
        # 빈 문자열, ".", None 모두 base_path.parent로 대체
        directory = self.meta_policy.directory
        if not directory or directory in ("", "."):
            directory = base_path.parent
        else:
            directory = Path(directory)
        directory = directory.resolve()
        directory.mkdir(parents=True, exist_ok=True)
        
        # Use FSO to build metadata path
        meta_builder = FSOPathBuilder(
            base_dir=directory,
            name_policy=self.meta_policy.name.model_copy(
                update={"name": base_path.stem}
            ),
            ops_policy=self.meta_policy.ops,
        )
        path = meta_builder()
        
        path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def _build_target_path(self, base_path: Path) -> Path:
        """Build target path using FSO policies directly."""
        # 빈 문자열, ".", None 모두 base_path.parent로 대체
        directory = self.target_policy.directory
        if not directory or directory in ("", "."):
            directory = base_path.parent
        else:
            directory = Path(directory)
        directory = directory.resolve()
        
        # Determine extension from policy or source
        ext = self.target_policy.format or base_path.suffix.lstrip(".")
        if ext and not ext.startswith("."):
            ext = f".{ext}"
        
        # Use FSO PathBuilder with policy's name and ops settings
        builder = FSOPathBuilder(
            base_dir=directory,
            name_policy=self.target_policy.name.model_copy(
                update={
                    "name": base_path.stem,
                    "extension": ext,
                }
            ),
            ops_policy=self.target_policy.ops,
        )
        return builder()

