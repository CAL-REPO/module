# -*- coding: utf-8 -*-
"""XLOTO Policy - Excel + OTO Pipeline Integration.

책임:
1. Excel 설정 (XlController)
2. OTO 파이프라인 설정 (Oto Adapter)
3. 통합 로그 정책
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Dict, List, Optional

from logs_utils.core.policy import LogPolicy


class XlOtoFilterPolicy(BaseModel):
    """DataFrame 필터링 정책.
    
    download=날짜, translation≠날짜인 행을 필터링합니다.
    
    Attributes:
        cas_column: CAS No 컬럼 별칭
        download_column: Download 컬럼 별칭
        translation_column: Translation 컬럼 별칭
    """
    cas_column: str = "cas"
    download_column: str = "download"
    translation_column: str = "translation"


class XlOtoPathsPolicy(BaseModel):
    """이미지 경로 정책.
    
    Attributes:
        public_img_dir: 공용 이미지 디렉토리
        origin_dirname: 원본 이미지 폴더명
        translated_dirname: 번역 이미지 폴더명
    """
    public_img_dir: str = Field(
        "${public_dir}/01.IMAGE",
        description="공용 이미지 디렉토리"
    )
    origin_dirname: str = "original"
    translated_dirname: str = "translated"


class XlOtoPolicy(BaseModel):
    """XLOTO Pipeline 통합 정책.
    
    Excel에서 CAS No 추출 → 이미지 처리 (OTO) → Excel 업데이트
    
    Attributes:
        name: Policy 이름
        filter: DataFrame 필터링 정책
        paths: 이미지 경로 정책
        log: 통합 로그 정책
    """
    name: str = "xloto"
    filter: XlOtoFilterPolicy = Field(
        default_factory=XlOtoFilterPolicy,  # type: ignore
        description="DataFrame 필터링 정책"
    )
    paths: XlOtoPathsPolicy = Field(
        default_factory=XlOtoPathsPolicy,  # type: ignore
        description="이미지 경로 정책"
    )
    log: LogPolicy = Field(
        default_factory=LogPolicy,
        description="XLOTO 통합 로그 정책"
    )
