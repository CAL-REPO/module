# -*- coding: utf-8 -*-
# pillow_refactor/policy.py

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field, model_validator


class ImageSourcePolicy(BaseModel):
    path: Path
    must_exist: bool = Field(False, description="Require source image to exist.")
    convert_mode: Optional[str] = Field(
        None, description="Optional Pillow mode conversion (e.g. 'RGB')."
    )


class ImageTargetPolicy(BaseModel):
    directory: Optional[Path] = Field(
        None, description="Directory for the processed image (default: source dir)."
    )
    filename_template: str = Field(
        "{stem}{suffix}{ext}", description="Format string for target filename."
    )
    suffix: str = Field("_processed", description="Suffix appended to the stem.")
    format: Optional[str] = Field(None, description="Target image format (default original).")
    quality: int = Field(95, ge=1, le=100, description="Encoder quality for JPEG/WebP.")
    ensure_unique: bool = Field(True, description="Avoid overwriting by uniquifying filenames.")


class ImageMetaPolicy(BaseModel):
    enabled: bool = Field(False, description="Persist metadata alongside the image.")
    directory: Optional[Path] = Field(None, description="Directory for metadata JSON.")
    filename: str = Field("{stem}{suffix}.json", description="Metadata filename template.")


class ImageProcessingPolicy(BaseModel):
    resize_to: Optional[Tuple[int, int]] = Field(
        None, description="Optional max size (width, height)."
    )
    blur_radius: Optional[float] = Field(
        None, description="Gaussian blur radius to apply after resize."
    )
    convert_mode: Optional[str] = Field(
        None, description="Override colour conversion for processed output."
    )


class ImagePipelinePolicy(BaseModel):
    source: ImageSourcePolicy
    target: ImageTargetPolicy = Field(default_factory=ImageTargetPolicy)
    processing: ImageProcessingPolicy = Field(default_factory=ImageProcessingPolicy)
    meta: ImageMetaPolicy = Field(default_factory=ImageMetaPolicy)


# ---------------------------------------------------------------------------
# Overlay policies
# ---------------------------------------------------------------------------

class OverlayFontPolicy(BaseModel):
    family: Optional[str] = Field(
        None, description="Font family or path. None uses Pillow default."
    )
    size: Optional[int] = Field(
        None, description="Font size in px. None triggers auto-fitting."
    )
    fill: str = Field("#000000", description="Text colour.")
    stroke_fill: Optional[str] = Field(None, description="Stroke colour.")
    stroke_width: int = Field(0, ge=0, description="Stroke width.")


class OverlayTextPolicy(BaseModel):
    text: str = Field(...)
    polygon: List[Tuple[float, float]] = Field(
        ...,
        description="Polygon coordinates defining the placement area.",
    )
    font: OverlayFontPolicy = Field(default_factory=OverlayFontPolicy)
    anchor: str = Field(
        "mm", description="Pillow anchor for text drawing (e.g. 'mm', 'lt')."
    )
    offset: Tuple[float, float] = Field(
        (0.0, 0.0), description="Offset applied to the anchor (dx, dy)."
    )
    max_width_ratio: float = Field(
        0.95, gt=0.0, description="Max width ratio of text within bounding box."
    )


class OverlayPolicy(BaseModel):
    image: ImageSourcePolicy
    output: ImageTargetPolicy = Field(default_factory=ImageTargetPolicy)
    texts: List[OverlayTextPolicy] = Field(default_factory=list)
    background_opacity: float = Field(
        0.0, ge=0.0, le=1.0, description="Overlay background opacity."
    )

    @model_validator(mode="after")
    def validate_texts(self):
        if not self.texts:
            raise ValueError("OverlayPolicy requires at least one text item.")
        return self
