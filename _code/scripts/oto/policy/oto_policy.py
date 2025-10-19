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
    ImageLoadPolicy,
    ImageTextRecognizePolicy,
    ImageOverlayPolicy,
)
from translate_utils.core.policy import TranslatePolicy
from logs_utils.core.policy import LogPolicy

class OTOPolicy(BaseModel):
    """OTO Pipeline 통합 정책 (Adapter용).
    
    OTO는 Adapter이므로 source 없는 Adapter Policy만 사용합니다.
    4개 Adapter(ImageLoad, ImageTextRecognize, Translate, ImageOverlay)의 정책을 통합합니다.
    
    Attributes:
        name: Policy 이름 (ConfigLikeLoader용)
        image_load: ImageLoad 정책 (이미지 처리)
        text_recognize: ImageTextRecognize 정책 (OCR 실행)
        translate: Translate 정책 (번역 실행)
        overlay: ImageOverlay 정책 (오버레이 렌더링)
        log: OTO 파이프라인 공통 로그 정책
    
    Example:
        >>> # From YAML
        >>> oto = ConfigLoader('oto.yaml')
        >>> policy = oto.as_model(OTOPolicy)
        
        >>> # Runtime override
        >>> policy = OTOPolicy(
        ...     text_recognize={"provider": {"langs": ["ch", "en"]}},
        ...     translate={"provider": {"provider": "deepl"}},
        ... )
    """
    name: str = "oto"
    image_load: ImageLoadPolicy = Field(
        default_factory=ImageLoadPolicy,  # type: ignore
        description="ImageLoad 정책 (Adapter - source 없음)"
    )
    text_recognize: ImageTextRecognizePolicy = Field(
        default_factory=ImageTextRecognizePolicy,  # type: ignore
        description="ImageTextRecognize 정책 (Adapter - source 없음)"
    )
    translate: TranslatePolicy = Field(
        default_factory=TranslatePolicy,  # type: ignore
        description="Translate 정책 (Adapter - source 없음)"
    )
    overlay: ImageOverlayPolicy = Field(
        default_factory=ImageOverlayPolicy,  # type: ignore
        description="ImageOverlay 정책 (Adapter - source 없음)"
    )
    log: LogPolicy = Field(
        default_factory=LogPolicy,  # type: ignore
        description="OTO 파이프라인 공통 로그 정책"
    )
