"""Standalone image loading and optional copy/resizing with metadata and logging.

This module defines a small pipeline for handling a single image after it
has been downloaded.  It loads the image from disk, optionally copies
the image to a target directory using policies defined in :mod:`fso_utils`,
optionally resizes it, computes resize ratios, and persists a JSON
metadata file.  All operations are logged via :mod:`log_utils` using a
configurable :class:`~log_utils.policy.LogPolicy`.

The design adheres to the single responsibility principle (SRP):

* :class:`ImageLoaderPolicy` describes what should happen (source and
  destination directories, naming options, flags for copying and writing
  metadata, resize size, and logging settings).
* :class:`ImageLoader` orchestrates reading, processing and writing while
  delegating path resolution to :mod:`fso_utils` and logging to
  :mod:`log_utils`.
* Image manipulation and metadata generation are contained within this
  module; external data processing or OCR should occur in other modules.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Tuple, Any

from PIL import Image
from pydantic import BaseModel, Field, model_validator

from fso_utils import (
    FSONamePolicy,
    FSOOpsPolicy,
    ExistencePolicy,
    FSOPathBuilder,
)
from log_utils import LogManager, LogPolicy


class ImageLoaderPolicy(BaseModel):
    """Configuration model for loading a single image with optional copy and resize.

    Parameters
    ----------
    src_path: Path
        Path to the source image on disk.  Must exist.
    dest_dir: Optional[Path]
        Directory where the processed image will be saved.  If ``None``, the
        source directory is used.
    meta_dir: Optional[Path]
        Directory where the metadata JSON will be saved.  If ``None``, the
        value of ``dest_dir`` (or the source directory) is used.
    copy: bool
        Whether to copy and optionally resize the image.  If ``False``,
        no image file will be written and the destination path in the
        metadata will match ``src_path``.
    write_meta: bool
        Whether to write a metadata JSON file.  When ``False``, metadata
        will be returned in memory but no file will be created.
    resize_to: Optional[Tuple[int, int]]
        If provided and ``copy`` is ``True``, the image will be resized to this
        ``(width, height)`` using a high‑quality resampling filter.  Ratios are
        computed and stored in metadata.
    suffix: str
        String appended to the filename stem when generating the output
        filename.  Defaults to ``"_copy"``.
    ensure_unique: bool
        Whether to ensure that the output filename is unique by applying a
        counter suffix via :class:`FSOPathBuilder`.
    log_policy: Optional[LogPolicy]
        Optional logging policy used to configure logging via
        :class:`~log_utils.manager.LogManager`.  When ``None``, a default
        policy is used.
    """

    src_path: Path
    dest_dir: Optional[Path] = None
    meta_dir: Optional[Path] = None
    copy: bool = Field(True, description="Whether to copy/resize the image.")
    write_meta: bool = Field(True, description="Whether to write metadata JSON to disk.")
    resize_to: Optional[Tuple[int, int]] = None
    suffix: str = Field("_copy", description="Suffix appended to the filename stem.")
    ensure_unique: bool = Field(True, description="Ensure the output filename is unique.")
    log_policy: Optional[LogPolicy] = None

    @model_validator(mode="after")
    def _validate_source(self) -> "ImageLoaderPolicy":
        if not self.src_path.exists():
            raise FileNotFoundError(f"Source image not found: {self.src_path}")
        return self


class ImageLoader:
    """Loads a single image and optionally copies/resizes it.

    The loader reads an image from ``policy.src_path`` and, depending on
    :attr:`ImageLoaderPolicy.copy`, optionally resizes it and writes the processed
    image to ``policy.dest_dir``.  It also writes a metadata JSON to
    ``policy.meta_dir`` containing original and new dimensions and the
    resize ratios.  Logging is performed via the provided
    :class:`~log_utils.manager.LogManager`.
    """

    def __init__(self, policy: ImageLoaderPolicy):
        self.policy = policy
        # Resolve default directories relative to the source path
        self.dest_dir = (policy.dest_dir or policy.src_path.parent).resolve()
        self.meta_dir = (policy.meta_dir or self.dest_dir).resolve()
        # Use provided log policy or a default one
        self.log_policy = policy.log_policy or LogPolicy()

    def _build_dest_path(self) -> Path:
        """Construct a destination path for the processed image using fso_utils."""
        src = self.policy.src_path
        stem = src.stem + self.policy.suffix
        ext = src.suffix
        name_policy = FSONamePolicy(
            as_type="file",
            name=stem,
            extension=ext,
            tail_mode="counter" if self.policy.ensure_unique else None,
            ensure_unique=self.policy.ensure_unique,
        )
        ops_policy = FSOOpsPolicy(
            as_type="file",
            exist=ExistencePolicy(create_if_missing=True),
        )
        builder = FSOPathBuilder(base_dir=self.dest_dir, name_policy=name_policy, ops_policy=ops_policy)
        return builder()

    def _build_meta_path(self, image_path: Path) -> Path:
        """Construct a path for the metadata JSON file based on the image path."""
        filename = image_path.stem + ".json"
        return self.meta_dir / filename

    def run(self, image: Optional[Image.Image] = None) -> dict[str, Any]:
        """Execute the image load, optional copy/resize, and metadata persistence.

        Parameters
        ----------
        image: Optional[Image.Image]
            An already loaded PIL Image object.  If provided, the loader
            will use this instead of reading from ``policy.src_path``.  This
            allows callers to avoid reloading the image when it is already
            available in memory.

        Returns
        -------
        dict
            A dictionary containing the original image path, the (possibly new)
            image path, the metadata path (if written), original and new sizes,
            and resize ratios.  In case of failure, logs will capture the
            exception and the exception will be re‑raised.
        """
        # Set up logging
        manager = LogManager(name="ImageLoader", policy=self.log_policy)
        logger = manager.setup()
        logger.info(f"[ImageLoader] 시작: {self.policy.src_path}")
        try:
            # Load the source image if not provided
            img = image or Image.open(self.policy.src_path)
            orig_width, orig_height = img.size
            logger.info(f"[ImageLoader] 원본 크기: {orig_width}x{orig_height}")

            # Determine whether to copy and/or resize
            if self.policy.copy:
                # Optionally resize
                new_width, new_height = orig_width, orig_height
                processed_img = img
                ratio_x = ratio_y = 1.0
                if self.policy.resize_to:
                    new_width, new_height = self.policy.resize_to
                    processed_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    ratio_x = new_width / orig_width
                    ratio_y = new_height / orig_height
                    logger.info(
                        f"[ImageLoader] 리사이즈: {orig_width}x{orig_height} → {new_width}x{new_height} (ratio {ratio_x:.4f}, {ratio_y:.4f})"
                    )

                # Build destination path and save the image
                dest_path = self._build_dest_path()
                processed_img.save(dest_path)
                logger.info(f"[ImageLoader] 이미지 저장: {dest_path}")
            else:
                # No copy: use original image path and sizes
                dest_path = self.policy.src_path
                new_width, new_height = orig_width, orig_height
                ratio_x = ratio_y = 1.0
                logger.info("[ImageLoader] 복사를 건너뜁니다: 원본 이미지를 그대로 사용합니다")

            # Build metadata and save to JSON
            meta_path = self._build_meta_path(dest_path)
            metadata = {
                "src_path": str(self.policy.src_path),
                "dest_path": str(dest_path),
                "orig_width": orig_width,
                "orig_height": orig_height,
                "new_width": new_width,
                "new_height": new_height,
                "ratio_x": ratio_x,
                "ratio_y": ratio_y,
            }
            if self.policy.write_meta:
                self.meta_dir.mkdir(parents=True, exist_ok=True)
                meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
                logger.info(f"[ImageLoader] 메타데이터 저장: {meta_path}")
            else:
                logger.info("[ImageLoader] 메타데이터 저장을 건너뜁니다")

            logger.info("[ImageLoader] 완료")
            # Include meta_path only if written
            metadata["meta_path"] = str(meta_path) if self.policy.write_meta else None
            return metadata
        except Exception as e:
            # Log the error and re‑raise
            logger.error(f"[ImageLoader] 오류 발생: {e}")
            raise