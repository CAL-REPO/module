# -*- coding: utf-8 -*-
"""Configuration 소스 구현체 - 단일 진입점."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Any

from pydantic import BaseModel

from modules.keypath_utils import KeyPathDict

from ..core.interface import SourceBase
from ..core.policy import SourcePolicy


class UnifiedSource(SourceBase):
    """통합 소스 (단일 진입점).
    
    SourcePolicy의 src 타입에 따라 자동으로 분기 처리합니다:
    - BaseModel → model_dump()
    - dict → dict.copy()
    - str/Path → YAML 파싱
    
    처리 흐름:
    1. Policy.src에서 데이터 타입 자동 감지
    2. 타입별 처리 (_extract_basemodel/_extract_dict/_extract_yaml)
    3. Section 적용
    4. 타입별 정규화 (base_model_normalizer/dict_normalizer/yaml_normalizer)
    
    Examples:
        >>> from cfg_utils_v2.core.policy import SourcePolicy, NormalizePolicy
        >>> 
        >>> # BaseModel
        >>> policy = SourcePolicy(
        ...     src=(ImagePolicy(), "image"),
        ...     base_model_normalizer=NormalizePolicy(drop_blanks=True)
        ... )
        >>> source = UnifiedSource(policy)
        >>> kpd = source.extract()
        >>> 
        >>> # Dict
        >>> policy = SourcePolicy(
        ...     src=({"max_width": 1024}, "image"),
        ...     dict_normalizer=NormalizePolicy(drop_blanks=True)
        ... )
        >>> source = UnifiedSource(policy)
        >>> kpd = source.extract()
        >>> 
        >>> # YAML
        >>> policy = SourcePolicy(
        ...     src=("config.yaml", "image"),
        ...     yaml_normalizer=NormalizePolicy(resolve_vars=True)
        ... )
        >>> source = UnifiedSource(policy)
        >>> kpd = source.extract()
    """

    def __init__(self, policy: SourcePolicy):
        """초기화.
        
        Args:
            policy: SourcePolicy 인스턴스 (타입별 정책 포함)
        """
        self.policy = policy

    def extract(self) -> KeyPathDict:
        """소스에서 KeyPathDict 추출 (타입 자동 판단).
        
        Returns:
            정규화된 KeyPathDict
        
        Raises:
            ValueError: policy.src가 None인 경우
            TypeError: src 타입이 지원되지 않는 경우
        """
        if self.policy.src is None:
            raise ValueError("SourcePolicy.src is required")
        
        # src 타입 자동 판단 및 분기
        raw_src = self.policy.src[0] if isinstance(self.policy.src, tuple) else self.policy.src
        
        # 타입 판단 순서: str/Path → dict → BaseModel
        if isinstance(raw_src, (str, Path)):
            return self._extract_yaml()
        elif isinstance(raw_src, dict):
            return self._extract_dict()
        elif isinstance(raw_src, BaseModel):
            return self._extract_basemodel()
        else:
            raise TypeError(
                f"Unsupported src type: {type(raw_src)}. "
                f"Expected BaseModel, dict, str, or Path."
            )
    
    def _extract_basemodel(self) -> KeyPathDict:
        """BaseModel 소스 처리.
        
        Returns:
            정규화된 KeyPathDict
        
        Raises:
            TypeError: src가 BaseModel이 아닌 경우
        """
        # src 파싱: BaseModel | (BaseModel, section)
        if isinstance(self.policy.src, tuple):
            raw_data, section = self.policy.src
        else:
            raw_data = self.policy.src
            section = None
        
        # 타입 검증
        if not isinstance(raw_data, BaseModel):
            raise TypeError(f"Expected BaseModel, got {type(raw_data)}")
        
        # 1. BaseModel → dict
        data = raw_data.model_dump()
        
        # 2. Section 적용
        data = self._apply_section(data, section)
        
        # 3. 정규화 (base_model_normalizer)
        kpd = KeyPathDict(data=data)
        kpd = self._normalize(kpd, self.policy.base_model_normalizer, stage="extract")
        
        return kpd
    
    def _extract_dict(self) -> KeyPathDict:
        """Dict 소스 처리.
        
        Returns:
            정규화된 KeyPathDict
        
        Raises:
            TypeError: src가 dict가 아닌 경우
        """
        # src 파싱: dict | (dict, section)
        if isinstance(self.policy.src, tuple):
            raw_data, section = self.policy.src
        else:
            raw_data = self.policy.src
            section = None
        
        # 타입 검증
        if not isinstance(raw_data, dict):
            raise TypeError(f"Expected dict, got {type(raw_data)}")
        
        # 1. dict 복사
        data = raw_data.copy()
        
        # 2. Section 적용
        data = self._apply_section(data, section)
        
        # 3. 정규화 (dict_normalizer)
        kpd = KeyPathDict(data=data)
        kpd = self._normalize(kpd, self.policy.dict_normalizer, stage="extract")
        
        return kpd
    
    def _extract_yaml(self) -> KeyPathDict:
        """YAML 소스 처리.
        
        Returns:
            정규화된 KeyPathDict
        
        Raises:
            FileNotFoundError: YAML 파일이 없는 경우
            ValueError: yaml_parser가 None인 경우
        """
        from modules.structured_io.formats.yaml_io import YamlParser
        
        # src 파싱: str/Path | (str/Path, section)
        if isinstance(self.policy.src, tuple):
            raw_path, section = self.policy.src
        else:
            raw_path = self.policy.src
            section = None
        
        # 타입 검증
        if not isinstance(raw_path, (str, Path)):
            raise TypeError(f"Expected str or Path, got {type(raw_path)}")
        
        # 경로 변환
        path = Path(raw_path)
        if not path.exists():
            raise FileNotFoundError(f"YAML file not found: {path}")
        
        # yaml_parser는 항상 존재 (기본값 있음)
        parser_policy = self.policy.yaml_parser
        if parser_policy is None:
            raise ValueError("SourcePolicy.yaml_parser is required")
        
        # 1. YAML 파싱
        parser = YamlParser(policy=parser_policy)
        text = path.read_text(encoding=parser_policy.encoding)
        data = parser.parse(text, base_path=path.parent)
        
        # 2. Section 적용
        data = self._apply_section(data, section)
        
        # 3. 정규화 (yaml_normalizer)
        kpd = KeyPathDict(data=data)
        kpd = self._normalize(kpd, self.policy.yaml_normalizer, stage="extract")
        
        return kpd


# ============================================================
# Backward Compatibility Wrappers (loader.py용)
# ============================================================
class BaseModelSource(SourceBase):
    """BaseModel 소스 (backward compatibility wrapper)"""
    
    def __init__(self, data: BaseModel, section: Optional[str] = None, policy: Any = None):
        """Deprecated: Use UnifiedSource instead"""
        from ..core.policy import NormalizePolicy
        # policy가 NormalizePolicy면 사용, 아니면 기본값
        normalizer = policy if (policy and hasattr(policy, 'normalize_keys')) else None
        self.source_policy = SourcePolicy(
            src=(data, section) if section else data,
            base_model_normalizer=normalizer
        )
        self.unified = UnifiedSource(self.source_policy)
    
    def extract(self) -> KeyPathDict:
        return self.unified.extract()


class DictSource(SourceBase):
    """Dict 소스 (backward compatibility wrapper)"""
    
    def __init__(self, data: dict, section: Optional[str] = None, policy: Any = None):
        """Deprecated: Use UnifiedSource instead"""
        from ..core.policy import NormalizePolicy
        # policy가 NormalizePolicy면 사용, 아니면 기본값
        normalizer = policy if (policy and hasattr(policy, 'normalize_keys')) else None
        self.source_policy = SourcePolicy(
            src=(data, section) if section else data,
            dict_normalizer=normalizer
        )
        self.unified = UnifiedSource(self.source_policy)
    
    def extract(self) -> KeyPathDict:
        return self.unified.extract()


class YamlFileSource(SourceBase):
    """YAML 소스 (backward compatibility wrapper)"""
    
    def __init__(self, path: str | Path, section: Optional[str] = None, policy: Any = None):
        """Deprecated: Use UnifiedSource instead"""
        from ..core.policy import NormalizePolicy
        # policy가 NormalizePolicy면 사용, 아니면 기본값
        normalizer = policy if (policy and hasattr(policy, 'normalize_keys')) else None
        self.source_policy = SourcePolicy(
            src=(path, section) if section else path,
            yaml_normalizer=normalizer
        )
        self.unified = UnifiedSource(self.source_policy)
    
    def extract(self) -> KeyPathDict:
        return self.unified.extract()

