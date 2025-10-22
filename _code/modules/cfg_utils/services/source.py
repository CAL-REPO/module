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
        # src가 (data, section) tuple인 경우와 data만 있는 경우를 구분
        if isinstance(self.policy.src, tuple) and len(self.policy.src) == 2:
            # (data, section) 형태인지 확인
            first, second = self.policy.src
            # second가 str이면 (data, section) 형태
            if isinstance(second, str):
                raw_src = first
            else:
                # tuple이지만 (data, section) 아님 - 데이터 자체가 tuple
                raw_src = self.policy.src
        else:
            raw_src = self.policy.src
        
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
        
        # 경로 해석 (placeholder가 있으면 context로 해석)
        str_path = str(raw_path)
        
        if '{{' in str_path or '${' in str_path:
            # Context 준비: env section 전체를 flatten
            context = self.policy.context or {}
            
            # env.CASHOP_PATHS.configs_oto_dir → env__CASHOP_PATHS__configs_oto_dir로 flatten
            flattened_context = {}
            for key, value in context.items():
                if isinstance(value, dict):
                    # 중첩 dict를 flatten (env__CASHOP_PATHS__base_path 형태로)
                    for subkey, subvalue in value.items():
                        if isinstance(subvalue, dict):
                            for subsubkey, subsubvalue in subvalue.items():
                                flattened_context[f"{key}__{subkey}__{subsubkey}"] = subsubvalue
                        else:
                            flattened_context[f"{key}__{subkey}"] = subvalue
                else:
                    flattened_context[key] = value
            
            # 최상위 키도 context에 추가 ({{configs_oto_dir}} 같은 self-reference용)
            if "CASHOP_PATHS" in context and isinstance(context["CASHOP_PATHS"], dict):
                flattened_context.update(context["CASHOP_PATHS"])
            
            # KeyPathDict로 해석
            temp_kpd = KeyPathDict(data={"_path": str_path})
            resolved_kpd = temp_kpd.resolve_all(context=flattened_context, recursive=True, strict=False)
            str_path = resolved_kpd.data["_path"]
        
        # 경로 변환
        path = Path(str_path)
        if not path.exists():
            raise FileNotFoundError(f"YAML file not found: {path}")
        
        # yaml_parser는 항상 존재 (기본값 있음)
        parser_policy = self.policy.yaml_parser
        if parser_policy is None:
            raise ValueError("SourcePolicy.yaml_parser is required")
        
        # 1. YAML 파싱 (context 전달)
        context = self.policy.context or {}
        parser = YamlParser(policy=parser_policy, context=context)
        text = path.read_text(encoding=parser_policy.encoding)
        data = parser.parse(text, base_path=path.parent)
        
        # 2. Section 처리 및 검증
        if section:
            yaml_keys = list(data.keys())
            
            if section in data:
                # Case 1: Section이 YAML에 존재 → 해당 section만 추출 후 wrap
                data = {section: data[section]}
            
            else:
                # Case 2: Section이 YAML에 없음
                
                # 2-1: YAML이 Flat 구조인지 확인 (최상위 키가 없는 경우)
                # 모든 값이 dict가 아니면 Flat 구조로 판단
                is_flat_structure = any(not isinstance(data[k], dict) for k in yaml_keys)
                
                if is_flat_structure:
                    # Flat 구조 → section으로 wrap
                    data = {section: data}
                
                elif len(yaml_keys) == 1:
                    # 2-2: 최상위 키가 1개이고 Section과 불일치 → Raise!
                    yaml_top_key = yaml_keys[0]
                    raise ValueError(
                        f"Section mismatch in YAML file '{path.name}': "
                        f"YAML top-level key is '{yaml_top_key}', "
                        f"but section='{section}' was specified. "
                        f"\n\nOptions to fix:"
                        f"\n  1. Change YAML top-level key from '{yaml_top_key}' to '{section}'"
                        f"\n  2. Change section parameter to '{yaml_top_key}'"
                        f"\n  3. Use src=(path, '{yaml_top_key}') in ConfigLoader"
                    )
                
                else:
                    # 2-3: 최상위 키가 여러 개 → section이 없음 → Raise!
                    raise ValueError(
                        f"Section '{section}' not found in YAML file '{path.name}'. "
                        f"Available top-level keys: {yaml_keys}. "
                        f"\n\nOptions to fix:"
                        f"\n  1. Add '{section}:' section to YAML file"
                        f"\n  2. Use one of the existing sections: {yaml_keys}"
                    )
        
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
        
        # policy가 SourcePolicy면 그대로 사용 (우선순위 높음)
        if policy and isinstance(policy, SourcePolicy):
            self.source_policy = policy
        else:
            # policy가 NormalizePolicy면 사용, 아니면 기본값
            normalizer = policy if (policy and hasattr(policy, 'normalize_keys')) else None
            self.source_policy = SourcePolicy(
                src=(path, section) if section else path,
                yaml_normalizer=normalizer
            )
        self.unified = UnifiedSource(self.source_policy)
    
    def extract(self) -> KeyPathDict:
        return self.unified.extract()

