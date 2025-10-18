# -*- coding: utf-8 -*-
"""cfg_utils_v2.core.policy - 정책 모델 정의

정책 계층 구조:
1. 기본 정책 (MergePolicy, NormalizePolicy)
2. 소스 타입별 정책 (BaseModelSourcePolicy, DictSourcePolicy, YamlSourcePolicy)
3. 통합 소스 정책 (SourcePolicy) - Source 인스턴스에서 사용
4. ConfigLoader 전역 정책 (ConfigLoaderPolicy) - 소스 타입별 기본 정책 포함
"""

from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Union, List
from pydantic import BaseModel, Field
from modules.keypath_utils.core.policy import KeyPathStatePolicy
from modules.structured_io.core.policy import BaseParserPolicy

if TYPE_CHECKING:
    from modules.logs_utils.core.policy import LogPolicy
else:
    # 런타임에는 실제 import 시도, 실패 시 Any 사용
    try:
        from modules.logs_utils.core.policy import LogPolicy
    except ImportError:
        LogPolicy = Any  # type: ignore


# ============================================================
# 1. MergePolicy - KeyPathState 병합 정책
# ============================================================


# ============================================================
# 1. MergePolicy - KeyPathState 병합 정책
# ============================================================
class MergePolicy(BaseModel):
    """KeyPathState Merge 정책 (KeyPathState.merge 호출 시 사용)"""
    deep: bool = Field(False, description="Deep merge 여부 (False=shallow, True=recursive)")
    overwrite: bool = Field(True, description="기존 키 덮어쓰기 여부")


# ============================================================
# 2. NormalizePolicy - 정규화 정책
# ============================================================
class NormalizePolicy(BaseModel):
    """정규화 정책 (키 정규화, 빈 값 제거, 변수 해결)"""
    normalize_keys: bool = Field(False, description="키 정규화 (소문자 변환 등)")
    drop_blanks: bool = Field(False, description="빈 값 제거 (None, '', [], {})")
    resolve_vars: bool = Field(True, description="변수 참조 해결 ($ref: 등)")


# ============================================================
# 3. SourcePolicy - 통합 소스 정책 (단일 진입점)
# ============================================================
class SourcePolicy(BaseModel):
    """통합 소스 정책 (모든 소스 타입을 단일 진입점으로 처리)
    
    src 필드로 모든 타입의 소스를 받고, 내부에서 타입에 따라 분기 처리합니다.
    
    지원 타입:
    - BaseModel: Pydantic 모델 → model_dump()
    - dict: Python dict → copy()
    - str/Path: YAML 파일 → YamlParser
    
    src 형식:
    - 데이터만: src=ImagePolicy() 또는 src={"key": "value"}
    - 데이터+섹션: src=(ImagePolicy(), "image") 또는 src=({"key": "value"}, "section")
    
    타입별 정책:
    - BaseModel: base_model_normalizer, base_model_merge
    - Dict: dict_normalizer, dict_merge
    - YAML: yaml_parser, yaml_normalizer, yaml_merge
    
    사용 예시:
    ```python
    # BaseModel
    policy = SourcePolicy(
        src=(ImagePolicy(), "image"),
        base_model_normalizer=NormalizePolicy(drop_blanks=True),
        base_model_merge=MergePolicy(deep=False)
    )
    
    # Dict
    policy = SourcePolicy(
        src=({"max_width": 1024}, "image"),
        dict_normalizer=NormalizePolicy(drop_blanks=True)
    )
    
    # YAML
    policy = SourcePolicy(
        src=("config.yaml", "image"),
        yaml_parser=BaseParserPolicy(safe_mode=False),
        yaml_normalizer=NormalizePolicy(resolve_vars=True)
    )
    
    # Source는 하나로 통일
    source = UnifiedSource(policy)
    kpd = source.extract()  # 내부에서 타입 자동 판단
    ```
    """
    # 단일 진입점 (Any 타입 사용 - Pydantic이 dict를 BaseModel로 변환하지 않도록)
    src: Optional[Any] = Field(
        default=None,
        description="소스 데이터: BaseModel/dict/str/Path 또는 (데이터, section) 튜플"
    )
    
    # BaseModel 정책
    base_model_normalizer: Optional[NormalizePolicy] = Field(
        default_factory=lambda: NormalizePolicy(
            normalize_keys=True,
            drop_blanks=False,
            resolve_vars=False
        ),
        description="BaseModel 정규화 정책"
    )
    base_model_merge: Optional[MergePolicy] = Field(
        default_factory=lambda: MergePolicy(deep=False, overwrite=False),
        description="BaseModel 병합 정책"
    )
    
    # Dict 정책
    dict_normalizer: Optional[NormalizePolicy] = Field(
        default_factory=lambda: NormalizePolicy(
            normalize_keys=True,
            drop_blanks=False,
            resolve_vars=False
        ),
        description="Dict 정규화 정책"
    )
    dict_merge: Optional[MergePolicy] = Field(
        default_factory=lambda: MergePolicy(deep=False, overwrite=True),
        description="Dict 병합 정책"
    )
    
    # YAML 정책
    yaml_parser: Optional[BaseParserPolicy] = Field(
        default_factory=lambda: BaseParserPolicy(
            safe_mode=True,
            encoding="utf-8",
            enable_env=True,
            enable_include=True,
            enable_placeholder=True
        ),
        description="YAML 파서 정책"
    )
    yaml_normalizer: Optional[NormalizePolicy] = Field(
        default_factory=lambda: NormalizePolicy(
            normalize_keys=True,
            drop_blanks=True,     # YAML은 override 용도 (빈 값 제거)
            resolve_vars=True
        ),
        description="YAML 정규화 정책"
    )
    yaml_merge: Optional[MergePolicy] = Field(
        default_factory=lambda: MergePolicy(deep=True, overwrite=True),
        description="YAML 병합 정책"
    )


# ============================================================
# 4. ConfigLoaderPolicy - ConfigLoader 전역 정책
# ============================================================
class ConfigLoaderPolicy(BaseModel):
    """ConfigLoader 전역 정책
    
    ConfigLoader의 전역 기본 정책으로, 소스 타입별 기본 동작을 정의합니다.
    SourcePolicy의 기본값을 제공합니다.
    
    구조:
    - source: SourcePolicy 기본값 (타입별 정책 포함)
    - keypath: KeyPath 동작 정책
    - log: 로깅 정책
    
    사용 예시:
    ```python
    # 전역 정책 커스터마이징
    policy = ConfigLoaderPolicy(
        source=SourcePolicy(
            yaml_parser=BaseParserPolicy(safe_mode=False),
            yaml_normalizer=NormalizePolicy(resolve_vars=True)
        ),
        keypath=KeyPathStatePolicy(separator="__")
    )
    
    # ConfigLoader가 사용
    loader = ConfigLoader(
        policy=policy,
        base_sources=[(ImagePolicy(), "image")]
    )
    ```
    """
    source: SourcePolicy = Field(
        default_factory=lambda: SourcePolicy(),
        description="소스 정책 기본값 (타입별 정책 포함)"
    )
    keypath: Optional[KeyPathStatePolicy] = Field(
        None,
        description="KeyPath 동작 정책 (None이면 기본값 사용)"
    )
    log: Optional[LogPolicy] = Field(
        None,
        description="로깅 정책 (logs_utils.LogPolicy, None이면 로깅 비활성화)"
    )
