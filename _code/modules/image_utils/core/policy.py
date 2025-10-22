# -*- coding: utf-8 -*-
"""
Image processing policy (Pydantic)
-----------------------------

translate_utils 패턴을 정확히 따라 Adapter/EntryPoint Policy 분리:
- Adapter Policy: source 없음, 순수 처리 로직 설정만
- EntryPoint Policy: source + Adapter Policy 포함

Adapter Policies (source 없음):
- ImageLoadPolicy: ImageLoad(Adapter) 전용 - save + meta + process + log
- ImageTextRecognizePolicy: ImageTextRecognize(Adapter) 전용 - provider + preprocess + postprocess + log
- ImageOverlayPolicy: ImageOverlay(Adapter) 전용 - items + background_opacity + log

EntryPoint Policies (source 포함):
- ImageLoaderPolicy: ImageLoader(EntryPoint) 전용 - source + image_load(ImageLoadPolicy)
- ImageTextRecognizerPolicy: ImageTextRecognizer(EntryPoint) 전용 - source + text_recognize(ImageTextRecognizePolicy)
- ImageOverlayerPolicy: ImageOverlayer(EntryPoint) 전용 - source + overlay(ImageOverlayPolicy)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, model_validator

from font_utils import FontPolicy
from logs_utils import LogPolicy
from fso_utils import FSONamePolicy, FSOOpsPolicy, ExistencePolicy, FileExtensionPolicy


# ==============================================================================
# Common Policies (Shared across Adapters & EntryPoints)
# ==============================================================================

class ImageSourcePolicy(BaseModel):
    """Source image file configuration (EntryPoint 전용).
    
    Adapter는 source를 받지 않고, EntryPoint에서만 사용합니다.
    
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
# 1st Adapter: ImageLoad
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


class ImageLoadPolicy(BaseModel):
    """ImageLoad(Adapter) 전용 Policy - 순수 이미지 처리 로직 설정
    
    source를 받지 않습니다. EntryPoint(ImageLoader)에서 이미지를 로드한 후
    Image 객체를 받아서 처리합니다.
    
    Attributes:
        save: 이미지 저장 설정
        meta: 메타데이터 저장 설정
        process: 이미지 처리 설정 (리사이즈, 블러 등)
        log: 로깅 설정 (Optional, EntryPoint에서 주입 가능)
    """
    name: str = Field(default="image_load", description="Section name in YAML config")
    save: ImageSavePolicy = Field(default_factory=ImageSavePolicy)  # type: ignore
    meta: ImageMetaPolicy = Field(default_factory=ImageMetaPolicy)  # type: ignore
    process: ImageProcessPolicy = Field(default_factory=ImageProcessPolicy)  # type: ignore
    log: Optional[LogPolicy] = None  # ✨ logging 설정 (Optional)


class ImageLoaderPolicy(BaseModel):
    """ImageLoader(EntryPoint) 전용 Policy - YAML 기반 진입점 설정
    
    translate_utils의 TranslatorPolicy와 동일한 구조:
    - source: 소스 이미지 로딩 설정 (파일 경로)
    - image_loader: ImageLoad 내부 Policy (ImageLoadPolicy 포함)
    
    Attributes:
        source: 소스 이미지 파일 설정
        image_loader: ImageLoad adapter 설정 (ImageLoadPolicy)
    """
    name: str = Field(default="image_loader", description="Section name in YAML config")
    source: ImageSourcePolicy
    image: ImageLoadPolicy = Field(default_factory=ImageLoadPolicy)  # type: ignore


# ==============================================================================
# 2nd Adapter: ImageTextRecognize
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
    paddle_use_doc_orientation_classify: bool = Field(False, description="Enable document orientation classification")
    paddle_use_doc_unwarping: bool = Field(False, description="Enable document unwarping (distortion correction)")
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


class ImageTextRecognizePolicy(BaseModel):
    """ImageTextRecognize(Adapter) 전용 Policy - 순수 OCR 로직 설정
    
    source를 받지 않습니다. EntryPoint(ImageTextRecognizer)에서 이미지를 로드한 후
    Image 객체를 받아서 OCR을 수행합니다.
    
    Attributes:
        provider: OCR Provider 설정 (PaddleOCR 등)
        preprocess: OCR 전처리 설정 (리사이즈 등)
        postprocess: OCR 후처리 설정 (필터링, 중복 제거 등)
        log: 로깅 설정 (Optional, EntryPoint에서 주입 가능)
    """
    name: str = Field(default="text_recognize", description="Section name in YAML config")
    provider: OCRProviderPolicy = Field(default_factory=OCRProviderPolicy)  # type: ignore
    preprocess: OCRPreprocessPolicy = Field(default_factory=OCRPreprocessPolicy)  # type: ignore
    postprocess: OCRPostprocessPolicy = Field(default_factory=OCRPostprocessPolicy)  # type: ignore
    log: Optional[LogPolicy] = None  # ✨ logging 설정 (Optional)


class ImageTextRecognizerPolicy(BaseModel):
    """ImageTextRecognizer(EntryPoint) 전용 Policy - YAML 기반 진입점 설정
    
    translate_utils의 TranslatorPolicy와 동일한 구조:
    - source: 소스 이미지 로딩 설정 (파일 경로)
    - text_recognize: ImageTextRecognize 내부 Policy (ImageTextRecognizePolicy 포함)
    
    Attributes:
        source: 소스 이미지 파일 설정
        text_recognize: ImageTextRecognize adapter 설정 (ImageTextRecognizePolicy)
        save: 결과 이미지 저장 설정 (선택)
        meta: 메타데이터 저장 설정 (선택)
    """
    name: str = Field(default="text_recognizer", description="Section name in YAML config")
    source: ImageSourcePolicy
    text_recognize: ImageTextRecognizePolicy = Field(default_factory=ImageTextRecognizePolicy)  # type: ignore
    save: ImageSavePolicy = Field(default_factory=ImageSavePolicy)  # type: ignore
    meta: ImageMetaPolicy = Field(default_factory=ImageMetaPolicy)  # type: ignore


# ==============================================================================
# 3rd Adapter: ImageOverlay
# ==============================================================================

class OverlayItemPolicy(BaseModel):
    """Individual overlay item configuration.
    
    Compatible with OCRItem structure for seamless integration.
    OCRItem can be converted to OverlayItemPolicy via to_overlay_item() method.
    
    Attributes:
        text: Text to overlay
        polygon: Polygon coordinates for text placement (same as OCRItem.quad)
        font: Font configuration (Optional, uses ImageOverlayPolicy.font if None)
        mask_opacity: Background mask opacity (0.0=transparent, 1.0=opaque)
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
    font: Optional[FontPolicy] = Field(
        None, 
        description="Font configuration (uses global font if None)"
    )
    mask_opacity: float = Field(
        1.0,
        ge=0.0,
        le=1.0,
        description="Background mask opacity (0.0=transparent, 1.0=opaque)"
    )
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
    """ImageOverlay(Adapter) 전용 Policy - 순수 오버레이 로직 설정
    
    source를 받지 않습니다. EntryPoint(ImageOverlayer)에서 이미지를 로드한 후
    Image 객체와 OverlayItem 리스트를 받아서 오버레이를 수행합니다.
    
    Attributes:
        items: 오버레이 아이템 리스트
        font: 전역 폰트 설정 (개별 아이템이 font 미설정 시 사용)
        mask_opacity: 전역 마스킹 투명도 (개별 아이템이 mask_opacity 미설정 시 사용)
        background_opacity: 배경 투명도
        log: 로깅 설정 (Optional, EntryPoint에서 주입 가능)
    """
    name: str = Field(default="overlay", description="Section name in YAML config")
    items: List[OverlayItemPolicy] = Field(
        default_factory=list,
        description="Overlay item configurations"
    )
    font: Optional[FontPolicy] = Field(
        None,
        description="Global font configuration (used if item.font is None)"
    )
    mask_opacity: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Global mask opacity (0.0=transparent, 1.0=opaque)"
    )
    background_opacity: float = Field(
        1.0, 
        ge=0.0, 
        le=1.0, 
        description="Overall layer opacity (0.0=transparent, 1.0=opaque)"
    )
    log: Optional[LogPolicy] = None  # ✨ logging 설정 (Optional)


class ImageOverlayerPolicy(BaseModel):
    """ImageOverlayer(EntryPoint) 전용 Policy - YAML 기반 진입점 설정
    
    translate_utils의 TranslatorPolicy와 동일한 구조:
    - source: 소스 이미지 로딩 설정 (파일 경로)
    - overlay: ImageOverlay 내부 Policy (ImageOverlayPolicy 포함)
    
    Attributes:
        source: 소스 이미지 파일 설정
        overlay: ImageOverlay adapter 설정 (ImageOverlayPolicy)
        save: 결과 이미지 저장 설정 (선택)
        meta: 메타데이터 저장 설정 (선택)
    """
    name: str = Field(default="overlayer", description="Section name in YAML config")
    source: ImageSourcePolicy
    overlay: ImageOverlayPolicy = Field(default_factory=ImageOverlayPolicy)  # type: ignore
    save: ImageSavePolicy = Field(default_factory=ImageSavePolicy)  # type: ignore
    meta: ImageMetaPolicy = Field(default_factory=ImageMetaPolicy)  # type: ignore


