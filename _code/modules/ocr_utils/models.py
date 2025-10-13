"""Pydantic models for OCR configuration and result schemas.

These models are intentionally minimal and map closely to the
configuration keys used by the pipeline. Using pydantic gives us
validation, defaulting and a clean shape when loading YAML configs.

Note: these are configuration/data shapes only — runtime instances
for providers (PaddleOCR objects, etc.) are created by the
recognizer adapter at runtime and stored in `paddle_instance` as
opaque values.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class OcrFileModel(BaseModel):
    """Configuration for file-level behavior.

    Attributes:
        file_path: Path to the source image file.
        save_img: When True the processed image copy will be saved.
        save_dir: Destination directory for saved images (optional).
        save_suffix: Filename suffix to append when saving copies.
        save_ocr_meta: When True, write meta JSON (see pipeline meta format).
        ocr_meta_dir: Directory to write meta JSON (optional).
        ocr_meta_name: Filename for saved meta JSON.
    """
    file_path: str = Field("", description="Source image path")
    save_img: bool = Field(False)
    save_dir: str = Field("")
    save_suffix: str = Field("_copy")
    save_ocr_meta: bool = Field(False)
    ocr_meta_dir: str = Field("")
    ocr_meta_name: str = Field("meta_ocr.json")


class OcrProviderModel(BaseModel):
    """Provider-level configuration.

    This file currently contains fields primarily for PaddleOCR. If you
    add other providers (tesseract/easyocr) the adapter should map these
    config fields appropriately.
    """
    provider: str = Field("paddle")
    langs: List[str] = Field(default_factory=lambda: ["ch_sim", "en"])
    min_conf: float = Field(0.5)
    paddle_device: Optional[str] = Field("gpu")
    paddle_use_angle_cls: bool = Field(True)
    # runtime cache for provider instances (lang -> instance)
    paddle_instance: Dict[str, Any] = Field(default_factory=dict)


class OcrPreprocessModel(BaseModel):
    """Image preprocessing configuration (resize, etc.)."""
    resized: bool = Field(False)
    max_width: Optional[int] = Field(None)


class OcrConfig(BaseModel):
    """Top-level OCR configuration object.

    Compose of file/provider/preprocess sections used by the pipeline.
    """
    # Use explicit empty kwargs in default_factory to make static analyzers
    # recognize we are calling the model without required runtime args.
    file: OcrFileModel = Field(default_factory=lambda: OcrFileModel(**{}))
    provider: OcrProviderModel = Field(default_factory=lambda: OcrProviderModel(**{}))
    preprocess: OcrPreprocessModel = Field(default_factory=lambda: OcrPreprocessModel(**{}))
    debug: bool = Field(False)


class OCRItemModel(BaseModel):
    """Schema for a single OCR detection item returned by the pipeline.

    Fields correspond to the pipeline meta format (text, conf, quad, bbox,
    angle_deg, lang, order).
    """
    text: str
    conf: float
    quad: List[List[float]]
    bbox: Dict[str, float]
    angle_deg: float
    lang: str
    order: int
