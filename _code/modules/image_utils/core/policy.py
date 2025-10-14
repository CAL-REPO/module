# -*- coding: utf-8 -*-
# pillow_utils/policy.py
"""Pydantic policies for pillow_utils image processing.

All policies support:
- BaseModel defaults from class definition
- YAML config loading via ConfigLoader
- Runtime **override via keyword arguments
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from pydantic import BaseModel, Field, model_validator

from font_utils import FontPolicy


# ==============================================================================
# Core Image Policies
# ==============================================================================

class ImageSourcePolicy(BaseModel):
    """Source image file configuration."""
    path: Path
    must_exist: bool = Field(False, description="Require source image to exist.")
    convert_mode: Optional[str] = Field(
        None, description="Optional Pillow mode conversion (e.g. 'RGB')."
    )


class ImagePolicy(BaseModel):
    """Image save/copy configuration with FSO_utils integration.
    
    Attributes:
        save_copy: Whether to save a copy of the image
        directory: Target directory (None = use path_utils.download())
        filename: Target filename (None = use original_name_copy.ext)
        suffix: Suffix for filename (default: '_copy')
        format: Target format (None = keep original)
        quality: JPEG/WebP quality (1-100)
        ensure_unique: Add counter suffix to avoid overwriting
    """
    save_copy: bool = Field(True, description="Save copy of image")
    directory: Optional[Path] = Field(
        None, description="Target directory (None = path_utils.download())"
    )
    filename: Optional[str] = Field(
        None, description="Target filename (None = {original_name}_copy{ext})"
    )
    suffix: str = Field("_copy", description="Suffix for auto-generated filename")
    format: Optional[str] = Field(None, description="Target format (None = original)")
    quality: int = Field(95, ge=1, le=100, description="JPEG/WebP quality")
    ensure_unique: bool = Field(True, description="Uniquify filename with counter")


class ImageMetaPolicy(BaseModel):
    """Image metadata save configuration with FSO_utils integration.
    
    Note: enabled field removed - metadata is always generated.
    ImageLoader's existence implies metadata generation.
    
    Attributes:
        save_meta: Whether to save metadata JSON to disk
        directory: Target directory (None = use path_utils.download())
        filename: Metadata filename (None = {original_name}_meta.json)
    """
    save_meta: bool = Field(True, description="Save metadata JSON to disk")
    directory: Optional[Path] = Field(
        None, description="Metadata directory (None = path_utils.download())"
    )
    filename: Optional[str] = Field(
        None, description="Metadata filename (None = {original_name}_meta.json)"
    )


class ImageProcessorPolicy(BaseModel):
    """Image processing operations configuration."""
    resize_to: Optional[Tuple[int, int]] = Field(
        None, description="Target size (width, height) for resize"
    )
    blur_radius: Optional[float] = Field(
        None, description="Gaussian blur radius"
    )
    convert_mode: Optional[str] = Field(
        None, description="PIL mode conversion (e.g., 'RGB', 'L')"
    )


class ImageLoaderPolicy(BaseModel):
    """Complete policy for ImageLoader (1st entrypoint).
    
    Combines file source, image save, metadata save, and processing policies.
    Supports:
    - BaseModel defaults
    - YAML config via ConfigLoader
    - Runtime **kwargs override
    
    Example:
        # From YAML
        policy = ConfigLoader('config.yaml').as_model(ImageLoaderPolicy)
        
        # Runtime override
        policy = ImageLoaderPolicy(**yaml_dict, save_copy=False)
    """
    source: ImageSourcePolicy
    image: ImagePolicy = Field(default_factory=ImagePolicy)  # pyright: ignore
    meta: ImageMetaPolicy = Field(default_factory=ImageMetaPolicy)  # pyright: ignore
    processing: ImageProcessorPolicy = Field(default_factory=ImageProcessorPolicy)  # pyright: ignore


# ==============================================================================
# Overlay Policies (for image_overlay.py entrypoint)
# ==============================================================================

class OverlayTextPolicy(BaseModel):
    """Individual text overlay configuration.
    
    Supports:
    - YAML-based configuration
    - Dict-based runtime override via **kwargs
    - Manual coordinate specification via polygon field
    """
    text: str = Field(..., description="Text to overlay")
    polygon: List[Tuple[float, float]] = Field(
        ...,
        description="Polygon coordinates for text placement area",
    )
    font: FontPolicy = Field(default_factory=FontPolicy)  # pyright: ignore
    anchor: str = Field(
        "mm", description="PIL anchor point (e.g., 'mm', 'lt')"
    )
    offset: Tuple[float, float] = Field(
        (0.0, 0.0), description="Position offset (dx, dy)"
    )
    max_width_ratio: float = Field(
        0.95, gt=0.0, description="Max text width ratio in bbox"
    )


class ImageOverlayPolicy(BaseModel):
    """Complete policy for image overlay operations.
    
    This policy combines source image, output configuration, and overlay specifications.
    All overlay data (coordinates, text) must be provided manually through:
    - YAML configuration
    - Runtime dict override via **kwargs
    
    Note: OCR results integration is handled by translate module entrypoint.
    This policy accepts only pre-transformed overlay specifications.
    
    Attributes:
        source: Source image configuration
        output: Output directory and naming configuration
        meta: Metadata persistence settings
        font: Default font configuration for all overlays
        background_opacity: Background opacity (0.0-1.0)
        texts: Text overlay configurations (YAML or dict-based)
        log: Logging configuration
    """
    # Image I/O
    source: ImageSourcePolicy
    output: ImagePolicy = Field(default_factory=ImagePolicy)  # pyright: ignore
    meta: ImageMetaPolicy = Field(default_factory=ImageMetaPolicy)  # pyright: ignore
    
    # Overlay configuration
    font: FontPolicy = Field(default_factory=FontPolicy)  # pyright: ignore
    background_opacity: float = Field(0.0, ge=0.0, le=1.0, description="Background opacity")
    
    # Manual overlay specifications (from YAML or dict override)
    texts: List[OverlayTextPolicy] = Field(
        default_factory=list,
        description="Text overlay configurations (YAML or dict-based)"
    )
    
    @model_validator(mode="after")
    def validate_overlay_source(self):
        """Ensure texts is provided."""
        if not self.texts:
            raise ValueError("ImageOverlayPolicy requires 'texts' field with at least one overlay specification")
        return self
