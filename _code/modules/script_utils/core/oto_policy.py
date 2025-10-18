# -*- coding: utf-8 -*-
"""OTO Pipeline Policy - Complete configuration model.

책임:
1. OTO 파이프라인 전체 정책 정의
2. 각 서비스(ImageLoader, OCR, Translator, Overlay) 정책 통합
3. Pydantic 검증 및 기본값 설정
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from image_utils.core.policy import (
    ImageLoaderPolicy,
    ImageOCRPolicy,
    ImageOverlayPolicy,
)
from translate_utils.core.policy import TranslatePolicy
from logs_utils.core.policy import LogPolicy

class OTOPolicy(BaseModel):
    """OTO Pipeline 통합 정책.
    
    4개 서비스(ImageLoader, OCR, Translator, Overlay)의 정책을 통합 관리합니다.
    
    Attributes:
        image: ImageLoader 정책 (이미지 로드 및 전처리)
        ocr: ImageTextRecognizer 정책 (OCR 실행)
        translate: Translator 정책 (번역 실행)
        overlay: ImageOverlayer 정책 (오버레이 렌더링)
        log: OTO 파이프라인 공통 로그 정책
    
    Example:
        >>> # From YAML
        >>> oto = ConfigLoader('oto.yaml')
        >>> policy = oto.as_model(OTOPolicy)
        
        >>> # Runtime override
        >>> policy = OTOPolicy(
        ...     image=ImageLoaderPolicy(source={"path": "test.jpg"}),
        ...     ocr=ImageOCRPolicy(provider={"langs": ["ch", "en"]}),
        ... )
    """
    image: ImageLoaderPolicy = Field(
        default_factory=ImageLoaderPolicy,  # type: ignore
        description="ImageLoader 정책"
    )
    ocr: ImageOCRPolicy = Field(
        default_factory=ImageOCRPolicy,  # type: ignore
        description="ImageTextRecognizer 정책"
    )
    translate: TranslatePolicy = Field(
        default_factory=TranslatePolicy,  # type: ignore
        description="Translator 정책"
    )
    overlay: ImageOverlayPolicy = Field(
        default_factory=ImageOverlayPolicy,  # type: ignore
        description="ImageOverlayer 정책"
    )
    log: LogPolicy = Field(
        default_factory=LogPolicy,  # type: ignore
        description="OTO 파이프라인 공통 로그 정책"
    )
