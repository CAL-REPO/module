# -*- coding: utf-8 -*-
# filename: cfg_utils/__init__.py
# description: 통합 설정 로딩 및 정규화 유틸리티 패키지 (ConfigLoader 중심 계층)
from __future__ import annotations

"""
cfg_utils — 구성(config) 데이터 로딩 · 병합 · 정규화 패키지
==========================================================
구성 파일(YAML), Pydantic 모델, dict, 런타임 인자 등 다양한 입력을 통합하여
일관된 설정 객체로 변환하는 상위 계층 유틸리티 모듈.

구조 개요
----------
- ConfigLoader: 설정 데이터 로드 및 병합, Pydantic 모델 변환
- ConfigNormalizer: 구성 데이터 후처리 (reference/drop)
- ConfigPolicy: 동작 정책(Pydantic 기반)
- YamlParser: YAML 텍스트 파서 (env/include 처리 포함)

의존 관계
----------
cfg_utils  →  yaml_utils, data_utils, unify_utils
(하위 계층을 직접 포함하되, 그 반대 의존은 없음)

예시
-----
>>> from cfg_utils import ConfigLoader, ConfigPolicy
>>> from pydantic import BaseModel

>>> class Settings(BaseModel):
...     name: str
...     port: int = 8080

>>> loader = ConfigLoader("config.yaml", policy=ConfigPolicy(resolve_reference=True))
>>> settings = loader.as_model(Settings)
>>> print(settings)
Settings(name='demo', port=8080)
"""

__version__ = "0.2.0"

# 주요 클래스 import
from .policy import ConfigPolicy
from .normalizer import ConfigNormalizer
from .loader import ConfigLoader

# 외부 의존 명시 (unify_utils.ReferenceResolver 등)
from unify_utils import ReferenceResolver

__all__ = [
    # Core API
    "ConfigLoader",
    "ConfigNormalizer",
    "ConfigPolicy",

    # External dependency re-export (편의성)
    "ReferenceResolver",
]
