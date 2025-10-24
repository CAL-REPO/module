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
    
    Note:
        - Column 필터링은 xl_utils의 column_alias로 처리 (cas, download, translation)
        - Filter Policy 제거됨 (중복 제거)
    
    Attributes:
        name: Policy 이름
        paths: 이미지 경로 정책
        log: 통합 로그 정책
    """
    name: str = "xloto"
    paths: XlOtoPathsPolicy = Field(
        default_factory=XlOtoPathsPolicy,  # type: ignore
        description="이미지 경로 정책"
    )
    log: LogPolicy = Field(
        default_factory=LogPolicy,
        description="XLOTO 통합 로그 정책"
    )
