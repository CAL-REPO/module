# -*- coding: utf-8 -*-
# image_utils/core/policy.py
"""Unified policy definitions for image_utils.

All policies support:
- BaseModel defaults from class definition
- YAML config loading via ConfigLoader
- Runtime **kwargs override via model_copy()

This module consolidates all policy classes for the 3 entrypoints:
1. ImageLoader
2. ImageOCR
3. ImageOverlay
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, model_validator

from font_utils import FontPolicy
from logs_utils import LogPolicy
from fso_utils import FSONamePolicy, FSOOpsPolicy, ExistencePolicy, FileExtensionPolicy


# ==============================================================================
# Common Policies (Shared across entrypoints)
# ==============================================================================

class ImageSourcePolicy(BaseModel):
    """Source image file configuration.
    
    Attributes:
        path: Path to source image file
        must_exist: Require source image to exist before processing
        convert_mode: Optional PIL mode conversion (e.g., 'RGB', 'L')
    """
    path: Path = Field(..., description="Path to source image file")
    must_exist: bool = Field(False, description="Require source to exist")
    convert_mode: Optional[str] = Field(
        None, 
        description="Optional Pillow mode conversion (e.g. 'RGB')"
    )


class ImageSavePolicy(BaseModel):
    """Image save/copy configuration using FSO_utils.
    
    Integrates with fso_utils for consistent file naming and path building
    across the entire project.
    
    Attributes:
        save_copy: Whether to save a copy of the image
        directory: Target directory (None = use path_utils.downloads())
        name: FSO name policy for file naming (prefix, suffix, tail_mode, etc.)
        ops: FSO operations policy for file existence/extension handling
        format: Target format (None = keep original format)
        quality: JPEG/WebP quality (1-100)
    """
    save_copy: bool = Field(True, description="Save copy of image")
    directory: Optional[Path] = Field(
        None, 
        description="Target directory (None = path_utils.downloads())"
    )
    name: FSONamePolicy = Field(
        default_factory=lambda: FSONamePolicy(
            as_type="file",
            suffix="_processed",
            tail_mode="counter",
            ensure_unique=True,
        ),  # type: ignore
        description="FSO name policy for file naming"
    )
    ops: FSOOpsPolicy = Field(
        default_factory=lambda: FSOOpsPolicy(
            as_type="file",
            exist=ExistencePolicy(create_if_missing=True),  # type: ignore
        ),  # type: ignore
        description="FSO operations policy"
    )
    format: Optional[str] = Field(None, description="Target format (None = original)")
    quality: int = Field(95, ge=1, le=100, description="JPEG/WebP quality")


class ImageMetaPolicy(BaseModel):
    """Image metadata save configuration using FSO_utils.
    
    Note: Metadata is always generated internally.
    This policy controls whether to persist it to disk.
    
    Attributes:
        save_meta: Whether to save metadata JSON to disk
        directory: Target directory (None = same as image)
        name: FSO name policy for metadata file naming
        ops: FSO operations policy for metadata file handling
    """
    save_meta: bool = Field(True, description="Save metadata JSON to disk")
    directory: Optional[Path] = Field(
        None, 
        description="Metadata directory (None = same as image)"
    )
    name: FSONamePolicy = Field(
        default_factory=lambda: FSONamePolicy(
            as_type="file",
            suffix="_meta",
            extension=".json",
            ensure_unique=False,
        ),  # type: ignore
        description="FSO name policy for metadata file"
    )
    ops: FSOOpsPolicy = Field(
        default_factory=lambda: FSOOpsPolicy(
            as_type="file",
            exist=ExistencePolicy(create_if_missing=True, overwrite=True),  # type: ignore
            ext=FileExtensionPolicy(default_ext=".json"),  # type: ignore
        ),  # type: ignore
        description="FSO operations policy for metadata"
    )


# ==============================================================================
# 1st EntryPoint: ImageLoader
# ==============================================================================

class ImageProcessPolicy(BaseModel):
    """Image processing operations configuration.
    
    Attributes:
        resize_to: Target size (width, height) for resize
        blur_radius: Gaussian blur radius
        convert_mode: PIL mode conversion (e.g., 'RGB', 'L')
    """
    resize_to: Optional[Tuple[int, int]] = Field(
        None, 
        description="Target size (width, height)"
    )
    blur_radius: Optional[float] = Field(
        None, 
        description="Gaussian blur radius"
    )
    convert_mode: Optional[str] = Field(
        None, 
        description="PIL mode conversion (e.g., 'RGB', 'L')"
    )


class ImageLoaderPolicy(BaseModel):
    """Complete policy for ImageLoader (1st entrypoint).
    
    Combines source, save, metadata, and processing policies.
    
    Supports:
    - BaseModel defaults
    - YAML config via ConfigLoader
    - Runtime **kwargs override
    
    Example:
        # From YAML
        loader = ConfigLoader('config.yaml')
        policy = loader.as_model(ImageLoaderPolicy)
        
        # Runtime override
        policy = ImageLoaderPolicy(**yaml_dict, save_copy=False)
    """
    source: ImageSourcePolicy
    save: ImageSavePolicy = Field(default_factory=ImageSavePolicy)  # type: ignore
    meta: ImageMetaPolicy = Field(default_factory=ImageMetaPolicy)  # type: ignore
    process: ImageProcessPolicy = Field(default_factory=ImageProcessPolicy)  # type: ignore
    log: LogPolicy = Field(default_factory=LogPolicy)  # type: ignore


# ==============================================================================
# 2nd EntryPoint: ImageOCR
# ==============================================================================

class OCRProviderPolicy(BaseModel):
    """OCR provider configuration.
    
    Attributes:
        provider: OCR provider name ('paddle', 'tesseract', etc.)
        langs: Language codes for OCR (e.g., ['ch', 'en'])
        min_conf: Minimum confidence threshold (0.0-1.0)
        paddle_device: PaddleOCR device ('cpu', 'gpu')
        paddle_use_angle_cls: Enable angle classification in PaddleOCR
        paddle_instance: Cached PaddleOCR instances (internal use)
    """
    provider: str = Field("paddle", description="OCR provider name")
    langs: List[str] = Field(
        default_factory=lambda: ["ch", "en"], 
        description="Language codes"
    )
    min_conf: float = Field(0.5, ge=0.0, le=1.0, description="Min confidence")
    
    # PaddleOCR specific
    paddle_device: str = Field("cpu", description="PaddleOCR device")
    paddle_use_angle_cls: bool = Field(True, description="Enable angle classification")
    paddle_instance: Optional[Any] = Field(
        None, 
        description="Cached PaddleOCR instances (internal)"
    )


class OCRPreprocessPolicy(BaseModel):
    """OCR preprocessing configuration.
    
    Attributes:
        max_width: Maximum width for OCR (resize if image is wider)
    """
    max_width: Optional[int] = Field(
        None, 
        description="Max width for OCR (resize if wider)"
    )


class OCRPostprocessPolicy(BaseModel):
    """OCR postprocessing configuration.
    
    Attributes:
        strip_special_chars: Remove special characters from text
        filter_alphanumeric: Filter out alphanumeric-only text
        deduplicate_iou_threshold: IoU threshold for bbox deduplication
        prefer_lang_order: Language preference order for deduplication
    """
    strip_special_chars: bool = Field(
        True, 
        description="Remove special characters"
    )
    filter_alphanumeric: bool = Field(
        True, 
        description="Filter alphanumeric-only text"
    )
    deduplicate_iou_threshold: float = Field(
        0.7, 
        ge=0.0, 
        le=1.0, 
        description="IoU threshold for deduplication"
    )
    prefer_lang_order: List[str] = Field(
        default_factory=lambda: ["ch", "en"], 
        description="Language preference order"
    )


class ImageOCRPolicy(BaseModel):
    """Complete policy for ImageOCR (2nd entrypoint).
    
    Combines source, OCR provider, preprocessing, postprocessing,
    save, metadata, and logging policies.
    
    Example:
        # From YAML
        ocr = ConfigLoader('ocr_config.yaml')
        policy = ocr.as_model(ImageOCRPolicy)
        
        # Runtime override
        policy = ImageOCRPolicy(
            source=ImageSourcePolicy(path=Path('image.jpg')),
            provider=OCRProviderPolicy(langs=['ch', 'en'])
        )
    """
    source: ImageSourcePolicy
    provider: OCRProviderPolicy = Field(default_factory=OCRProviderPolicy)  # type: ignore
    preprocess: OCRPreprocessPolicy = Field(default_factory=OCRPreprocessPolicy)  # type: ignore
    postprocess: OCRPostprocessPolicy = Field(default_factory=OCRPostprocessPolicy)  # type: ignore
    save: ImageSavePolicy = Field(default_factory=ImageSavePolicy)  # type: ignore
    meta: ImageMetaPolicy = Field(default_factory=ImageMetaPolicy)  # type: ignore
    log: LogPolicy = Field(default_factory=LogPolicy)  # type: ignore


# ==============================================================================
# 3rd EntryPoint: ImageOverlay
# ==============================================================================

class OverlayItemPolicy(BaseModel):
    """Individual overlay item configuration.
    
    Compatible with OCRItem structure for seamless integration.
    OCRItem can be converted to OverlayItemPolicy via to_overlay_item() method.
    
    Attributes:
        text: Text to overlay
        polygon: Polygon coordinates for text placement (same as OCRItem.quad)
        font: Font configuration
        anchor: PIL anchor point (e.g., 'mm', 'lt')
        offset: Position offset (dx, dy)
        max_width_ratio: Max text width ratio in bbox
        
        # OCRItem compatible fields (optional)
        conf: Confidence score from OCR
        bbox: Bounding box from OCR
        angle_deg: Text rotation angle from OCR
        lang: Language code from OCR
    """
    text: str = Field(..., description="Text to overlay")
    polygon: List[Tuple[float, float]] = Field(
        ...,
        description="Polygon coordinates [(x,y), ...] (compatible with OCRItem.quad)"
    )
    font: FontPolicy = Field(default_factory=FontPolicy)  # type: ignore
    anchor: str = Field("mm", description="PIL anchor point")
    offset: Tuple[float, float] = Field((0.0, 0.0), description="Position offset")
    max_width_ratio: float = Field(
        0.95, 
        gt=0.0, 
        description="Max text width ratio"
    )
    
    # OCRItem compatible fields (optional, for metadata/debugging)
    conf: Optional[float] = Field(None, description="OCR confidence score")
    bbox: Optional[Dict[str, float]] = Field(None, description="OCR bounding box")
    angle_deg: Optional[float] = Field(None, description="OCR text angle")
    lang: Optional[str] = Field(None, description="OCR language code")


class ImageOverlayPolicy(BaseModel):
    """Complete policy for ImageOverlay (3rd entrypoint).
    
    Combines source, overlay item specifications, save, metadata,
    and logging policies.
    
    Note: ImageOverlay follows SRP - it only overlays provided items.
    OCR → Translation → OverlayItem conversion is handled in pipeline scripts.
    
    Attributes:
        source: Source image configuration
        items: Overlay item configurations
        background_opacity: Background opacity (0.0-1.0)
        save: Image save configuration
        meta: Metadata save configuration
        log: Logging configuration
    
    Example:
        # From YAML
        overlay = ConfigLoader('overlay_config.yaml')
        policy = overlay.as_model(ImageOverlayPolicy)
        
        # Runtime override
        policy = ImageOverlayPolicy(
            source=ImageSourcePolicy(path=Path('image.jpg')),
            items=[
                OverlayItemPolicy(
                    text="Hello",
                    polygon=[(10,10), (100,10), (100,50), (10,50)]
                )
            ]
        )
    """
    source: ImageSourcePolicy
    items: List[OverlayItemPolicy] = Field(
        default_factory=list,
        description="Overlay item configurations"
    )
    background_opacity: float = Field(
        0.0, 
        ge=0.0, 
        le=1.0, 
        description="Background opacity"
    )
    save: ImageSavePolicy = Field(default_factory=ImageSavePolicy)  # type: ignore
    meta: ImageMetaPolicy = Field(default_factory=ImageMetaPolicy)  # type: ignore
    log: LogPolicy = Field(default_factory=LogPolicy)  # type: ignore


# ==============================================================================
# Backward Compatibility Aliases (Deprecated)
# ==============================================================================

# Keep old names for backward compatibility (will be removed in future)
ImagePolicy = ImageSavePolicy  # Updated alias
ImageProcessorPolicy = ImageProcessPolicy
OverlayTextPolicy = OverlayItemPolicy  # Deprecated: use OverlayItemPolicy
