"""OCR configuration policies (Pydantic schemas)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pathlib import Path
from pydantic import BaseModel, Field, model_validator

# Import pillow policies
from image_utils.core.policy import ImageSourcePolicy, ImagePolicy, ImageMetaPolicy
# Import log policy
from log_utils.core.policy import LogPolicy


class OcrFilePolicy(BaseModel):
    """File-level behavior policy."""
    file_path: str = Field("", description="Source image path")
    save_img: bool = Field(False)
    save_dir: str = Field("")
    save_suffix: str = Field("_copy")
    save_ocr_meta: bool = Field(False)
    ocr_meta_dir: str = Field("")
    ocr_meta_name: str = Field("meta_ocr.json")


class OcrProviderPolicy(BaseModel):
    """Provider-level configuration."""
    provider: str = Field("paddle")
    langs: List[str] = Field(default_factory=lambda: ["ch_sim", "en"])
    min_conf: float = Field(0.5)
    paddle_device: Optional[str] = Field("gpu")
    paddle_use_angle_cls: bool = Field(True)
    paddle_instance: Dict[str, Any] = Field(default_factory=dict)


class OcrPreprocessPolicy(BaseModel):
    """Image preprocessing policy."""
    resized: bool = Field(False)
    max_width: Optional[int] = Field(None)


class OcrPolicy(BaseModel):
    """Top-level OCR policy integrating ImageLoader and LogManager.
    
    Field priority (for overlapping fields):
    1. OCR-specific fields (file, provider, preprocess)
    2. Pillow fields (source, target, meta) - inherited from ImageLoader
    3. Log fields - for logging configuration
    
    The source.path from pillow takes precedence over file.file_path if both exist.
    """
    # OCR-specific policies
    file: OcrFilePolicy = Field(default_factory=lambda: OcrFilePolicy(**{}))
    provider: OcrProviderPolicy = Field(default_factory=lambda: OcrProviderPolicy(**{}))
    preprocess: OcrPreprocessPolicy = Field(default_factory=lambda: OcrPreprocessPolicy(**{}))
    debug: bool = Field(False)
    
    # ImageLoader integration (pillow policies)
    source: Optional[ImageSourcePolicy] = None
    target: Optional[ImagePolicy] = None
    meta: Optional[ImageMetaPolicy] = None
    
    # LogManager integration
    log: Optional[LogPolicy] = None
    
    @model_validator(mode="after")
    def _resolve_priorities(self) -> "OcrPolicy":
        """Resolve field priorities: OCR > Pillow > defaults.
        
        - If source.path exists, it overrides file.file_path
        - If file.file_path exists but source is None, create source from file
        """
        # Priority 1: source.path → file.file_path
        if self.source and self.source.path:
            self.file.file_path = str(self.source.path)
        elif self.file.file_path and not self.source:
            # Create source from file.file_path
            self.source = ImageSourcePolicy(path=Path(self.file.file_path)) # pyright: ignore[reportCallIssue]
        
        # Set defaults for pillow policies if not provided
        if self.target is None:
            self.target = ImagePolicy() # pyright: ignore[reportCallIssue]
        if self.meta is None:
            self.meta = ImageMetaPolicy() # pyright: ignore[reportCallIssue]
        if self.log is None:
            self.log = LogPolicy() # pyright: ignore[reportCallIssue]
            
        return self


class OCRItem(BaseModel):
    """Single OCR detection item."""
    text: str
    conf: float
    quad: List[List[float]]
    bbox: Dict[str, float]
    angle_deg: float
    lang: str
    order: int
