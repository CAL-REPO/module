# -*- coding: utf-8 -*-
"""cfg_utils_v2.core.policy - 정책 모델 정의"""

from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel, Field
from modules.keypath_utils.core.policy import KeyPathNormalizePolicy, KeyPathStatePolicy
from modules.structured_io.formats.yaml_io import YamlParser
from modules.structured_io.core.policy import BaseParserPolicy


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
# 7. BaseModelSourcePolicy - 모든 Source의 기본 정책
# ============================================================
class SourceBasePolicy(BaseModel):
    """모든 Source의 기본 정책 (normalizer, merge)
    
    모든 소스의 공통 기반 정책입니다.
    SourcePolicy가 이를 상속받습니다.
    """
    normalizer: Optional[NormalizePolicy] = Field(
        None,
        description="정규화 정책 (None이면 정규화 비활성화)"
    )
    merge: Optional[MergePolicy] = Field(
        None,
        description="병합 정책 (None이면 기본값: deep=False, overwrite=True)"
    )

# ============================================================
# 5. BaseModelBehaviorPolicy - BaseModel 동작 정책
# ============================================================
class BaseModelSourcePolicy(SourceBasePolicy):
    """BaseModel 소스 동작 정책
    
    BaseModel 처리 시 section 유무에 따른 동작을 제어합니다.
    - section 없음: auto_create_section=True면 생성, False면 에러
    - section 있음: override=True면 기존 섹션 덮어쓰기, False면 병합
    """
    pass
# ============================================================
# 6. DictBehaviorPolicy - Dict 동작 정책
# ============================================================
class DictSourcePolicy(SourceBasePolicy):
    """Dict 소스 동작 정책
    
    Dict 처리 시 section 유무에 따른 동작을 제어합니다.
    - section 없음: require_section=True면 에러, False면 root에 병합
    - section 있음: 항상 normalizing 후 override
    """
    section: Optional[str] = Field(
        None,
        description="Dict 소스 섹션 (None이면 기본값 사용)"
    )
    pass

# ============================================================
# 6. SourcePolicy - 개별 Source 정책
# ============================================================
class YamlSourcePolicy(SourceBasePolicy):
    """개별 Source 정책 (SourceBasePolicy 상속)
    
    상속받은 필드:
    - normalizer: 소스별 normalizer 정책
    - merge: 소스별 merge 정책
    
    추가 필드:
    - yaml_parser: YAML 소스 전용 parser 정책
    - basemodel_behavior: BaseModel 동작 정책
    - dict_behavior: Dict 동작 정책
    
    소스 타입별 처리:
    - YAML: yaml_parser + normalizer + merge
    - Dict: dict_behavior + normalizer + merge (yaml_parser 무시)
    - BaseModel: basemodel_behavior + normalizer + merge (yaml_parser 무시)
    """
    yaml_parser: Optional[YamlParser] = Field(
        None,
        description="YAML 파서 정책 (None이면 전역 yaml_parser 사용, YAML 소스에만 적용)"
    )

# ============================================================
# 7. ConfigLoaderPolicy - ConfigLoader 전역 정책
# ============================================================
class ConfigLoaderPolicy(SourceBase):
    """ConfigLoader 정책 (SourcePolicy 상속)
    
    상속받은 필드 (SourceBasePolicy):
    - normalizer: 전역 normalizer 정책
    - merge: 전역 merge 정책
    
    상속받은 필드 (SourcePolicy):
    - yaml_parser: 전역 YAML parser 정책
    
    추가 필드:
    - keypath: KeyPath 동작 정책
    - log: 로깅 정책
    """
    base_model: Optional[BaseModelSourcePolicy] = Field(
        default_factory=lambda: BaseModelSourcePolicy(
            normalizer=NormalizePolicy(normalize_keys=True, drop_blanks=False, resolve_vars=False),
            merge=MergePolicy(deep=False, overwrite=False)
        ),
        description="BaseModel 소스 동작 정책 (None이면 기본값 사용)"
    )
    dict: Optional[DictSourcePolicy] = Field(
        default_factory=lambda: DictSourcePolicy(
            section=None,
            normalizer=NormalizePolicy(normalize_keys=True, drop_blanks=False, resolve_vars=False),
            merge=MergePolicy(deep=False, overwrite=True)
        ),
        description="Dict 소스 동작 정책 (None이면 기본값 사용)"
    )   

    yaml: Optional[YamlSourcePolicy] = Field(
        default_factory=lambda: YamlSourcePolicy(
            yaml_parser=YamlParser(safe_mode=True, encoding="utf-8"),
            normalizer=NormalizePolicy(normalize_keys=True, drop_blanks=False, resolve_vars=True),
            merge=MergePolicy(deep=True, overwrite=True)
        ),
        description="YAML 소스 정책 (None이면 기본값 사용)"
    )

    keypath: Optional[KeyPathStatePolicy] = Field(
        default_factory=lambda: KeyPathNormalizePolicy(separator="__", override_requires_base=True),
        description="KeyPath 동작 정책 (None이면 기본값: separator='__', override_requires_base=True)"
    )
    log: Optional[Any] = Field(
        None,
        description="로깅 정책 (logs_utils.LogPolicy, None이면 로깅 비활성화)"
    )
