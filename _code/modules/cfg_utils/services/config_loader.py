"""cfg_utils.services.config_loader
===================================

Small, readable implementation of the project's configuration loader.

Responsibilities:
 - Accept a variety of configuration inputs (BaseModel, YAML path, list of
   YAML paths, or dict).
 - Merge inputs according to a :class:`ConfigPolicy` (deep vs shallow merge).
 - Normalize the resulting mapping using :class:`ConfigNormalizer`.
 - Provide a single :meth:`load` method to return a plain dict or a validated Pydantic model.

The implementation below splits responsibilities into small helper methods
to improve readability and make future testing simpler.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Dict, List, Type, Union, Optional, overload, Literal

from pydantic import BaseModel, ValidationError

from modules.data_utils.core.types import T, PathLike, PathsLike

from modules.structured_io.core.base_policy import BaseParserPolicy, SourcePathConfig
from modules.structured_io.formats.yaml_io import YamlParser

from modules.keypath_utils import KeyPathDict, KeyPathState

from .normalizer import ConfigNormalizer
from ..core.policy import ConfigPolicy
from modules.cfg_utils.services.merger import MergerFactory
from modules.cfg_utils.services.helpers import (
    apply_overrides,
    merge_sequence,
    load_source,
)



class ConfigLoader:
    """Load and merge configuration into normalized dicts or Pydantic models.

    Example usage::

        # Return dict
        cfg_dict = ConfigLoader.load("cfg.yaml")
        
        # Return Pydantic model
        config = ConfigLoader.load("cfg.yaml", model=MyPolicy)
        
        # With overrides
        config = ConfigLoader.load("cfg.yaml", model=MyPolicy, key="value")
    """
    
    # ==========================================================================
    # Public API: load() - 유일한 진입점
    # ==========================================================================
    
    @overload
    @staticmethod
    def load(
            cfg_like: Union[BaseModel, PathLike, PathsLike, dict[str, Any]],
        *,
        model: Type[T],
        policy: Optional[ConfigPolicy] = None,
        drop_blanks: Optional[bool] = None,
        resolve_reference: Optional[bool] = None,
        merge_mode: Optional[Literal["deep", "shallow"]] = None,
        **overrides: Any
    ) -> T: ...
    
    @overload
    @staticmethod
    def load(
            cfg_like: Union[BaseModel, PathLike, PathsLike, dict[str, Any]],
        *,
        model: None = None,
        policy: Optional[ConfigPolicy] = None,
        drop_blanks: Optional[bool] = None,
        resolve_reference: Optional[bool] = None,
        merge_mode: Optional[Literal["deep", "shallow"]] = None,
        **overrides: Any
    ) -> dict: ...
    
    @staticmethod
    def load(
            cfg_like: Union[BaseModel, PathLike, PathsLike, dict[str, Any]],
        *,
        model: Optional[Type[T]] = None,
        policy: Optional[ConfigPolicy] = None,
        drop_blanks: Optional[bool] = None,
        resolve_reference: Optional[bool] = None,
        merge_mode: Optional[Literal["deep", "shallow"]] = None,
        **overrides: Any
    ) -> Union[dict[str, Any], T]:
        """설정을 로드하여 dict 또는 Pydantic 모델로 반환.
        
        Args:
            cfg_like: 설정 소스 (BaseModel/Path/list[Path]/dict)
            model: Pydantic 모델 클래스 (있으면 모델 반환, 없으면 dict 반환)
            policy: ConfigPolicy 객체 (전체 Policy 교체 시)
            drop_blanks: 공백 값 제거 여부 (기본: True)
            resolve_reference: Reference 해석 여부 (기본: True)
            merge_mode: 병합 모드 - "deep" 또는 "shallow" (기본: "deep")
            **overrides: 최종 데이터 오버라이드 (deep merge)
        
        Returns:
            model이 있으면 Pydantic 모델 인스턴스, 없으면 dict
        
        Raises:
            TypeError: cfg_like가 None인 경우
        
        Examples:
            # 기본 사용
            config = ConfigLoader.load("config.yaml", model=MyPolicy)
            
            # 개별 파라미터로 Policy 오버라이드
            config = ConfigLoader.load(
                "config.yaml",
                model=MyPolicy,
                drop_blanks=False,
                merge_mode="shallow"
            )
            
            # Policy 객체 전달
            policy = ConfigPolicy(drop_blanks=False)
            config = ConfigLoader.load("config.yaml", policy=policy)
            
            # 여러 YAML 병합
            config = ConfigLoader.load(["base.yaml", "prod.yaml"], model=MyPolicy)
            
            # 데이터 오버라이드
            config = ConfigLoader.load("config.yaml", image__max_width=1024)
        
        Notes:
            - 파라미터 우선순위: 개별 파라미터 > policy > ConfigPolicy 기본값
            - None 케이스는 load_from_source_paths() 또는 load_from_policy() 사용
        """
        # 🔴 None 케이스 금지
        if cfg_like is None:
            raise TypeError(
                "cfg_like cannot be None. "
                "Use ConfigLoader.load_from_source_paths() or load_from_policy() instead."
            )
        
        # 1. Policy 생성 (우선순위: 개별 파라미터 > policy > 기본값)
        if policy is not None:
            temp_policy = policy
        else:
            temp_policy = ConfigPolicy()
        
        # 2. 개별 파라미터로 오버라이드 (policy보다 우선)
        if drop_blanks is not None:
            temp_policy = temp_policy.model_copy(update={"drop_blanks": drop_blanks})
        if resolve_reference is not None:
            temp_policy = temp_policy.model_copy(update={"resolve_reference": resolve_reference})
        if merge_mode is not None:
            temp_policy = temp_policy.model_copy(update={"merge_mode": merge_mode})
        
        # 3. 이미 모델 인스턴스인 경우
        if model and isinstance(cfg_like, model):
            if not overrides:
                return cfg_like
            # Overrides 적용 (dot notation 지원)
            config_dict = cfg_like.model_dump()
            config_dict = apply_overrides(config_dict, overrides, policy=temp_policy)
            return model(**config_dict)
        
        # 4. Dict인 경우 직접 처리
        if isinstance(cfg_like, dict):     
            if overrides:
                cfg_like = apply_overrides(copy.deepcopy(cfg_like), overrides, policy=temp_policy)
            
            # Model이 있으면 변환, 없으면 dict 반환
            if model:
                return model(**cfg_like)
            return cfg_like
        
        # 5. List인 경우 여러 파일 병합 (항상 deep merge)
        if isinstance(cfg_like, (list, tuple)) and not isinstance(cfg_like, (str, bytes)):
            # temp_policy에서 yaml policy 가져오기
            yaml_policy = temp_policy.yaml if temp_policy.yaml else BaseParserPolicy()
            temp_parser = YamlParser(policy=yaml_policy)
            
            # helpers.merge_sequence 호출 (separator 제거)
            merged_dict = merge_sequence(cfg_like, temp_parser, deep=True)
            
            # Overrides 적용
            if overrides:
                merged_dict = apply_overrides(merged_dict, overrides, policy=temp_policy)
            
            # 결과 모델/딕셔너리 반환
            return model(**merged_dict) if model else merged_dict
        
        # 6. Path/str인 경우 ConfigLoader로 로드
        if isinstance(cfg_like, (str, Path)):
            loader = ConfigLoader(cfg_like, policy=temp_policy)
            
            # Model이 있으면 모델로 변환
            if model:
                return loader._as_model_internal(model, **overrides)
            
            # Model이 없으면 dict 반환
            return loader._as_dict_internal(**overrides)
        
        # 6. 지원하지 않는 타입
        raise TypeError(f"Unsupported config type: {type(cfg_like)}")
    
    @staticmethod
    def load_from_source_paths(
        source_paths: List[PathLike],
        *,
        model: Optional[Type[T]] = None,
        **overrides: Any
    ) -> Union[dict, T]:
        """source_paths에서 직접 로드 (cfg_like=None 케이스 대체).
        
        Args:
            source_paths: 로드할 YAML 파일 경로 리스트
            model: Pydantic 모델 클래스
            **overrides: 최종 데이터 오버라이드
        
        Returns:
            model이 있으면 Pydantic 모델, 없으면 dict
        
        Examples:
            # ✅ 명시적
            config = ConfigLoader.load_from_source_paths(
                ["base.yaml", "prod.yaml"],
                model=MyPolicy
            )
        """
        # source_paths를 list로 변환하여 load() 호출
        return ConfigLoader.load(source_paths, model=model, **overrides)
    
    @staticmethod
    def load_from_policy(
        policy: ConfigPolicy,
        *,
        model: Optional[Type[T]] = None,
        **overrides: Any
    ) -> Union[dict, T]:
        """Policy 객체에서 직접 로드.
        
        Args:
            policy: ConfigPolicy 인스턴스
            model: Pydantic 모델 클래스
            **overrides: 최종 데이터 오버라이드
        
        Returns:
            model이 있으면 Pydantic 모델, 없으면 dict
        
        Examples:
            # ✅ 명시적
            policy = ConfigPolicy(
                yaml=BaseParserPolicy(source_paths=["config.yaml"])
            )
            config = ConfigLoader.load_from_policy(policy, model=MyPolicy)
        """
        # 빈 dict에 policy 적용
        loader = ConfigLoader({}, policy=policy)
        
        if model:
            return loader._as_model_internal(model, **overrides)
        return loader._as_dict_internal(**overrides)
    
    # ==========================================================================
    # Internal: 기존 로직 유지 (private)
    # ==========================================================================
    
    def __init__(
        self,
        cfg_like: Optional[Union[BaseModel, PathLike, PathsLike, dict]] = None,
        *,
        policy: Optional[ConfigPolicy] = None
    ) -> None:
        """ConfigLoader 초기화.
        
        Override 우선순위:
        1. ConfigPolicy 기본값 (Pydantic defaults)
        2. config_loader.yaml 로드
        3. policy 파라미터
        
        Args:
            cfg_like: 설정 소스 (None이면 policy.yaml.source_paths만 사용)
            policy: ConfigPolicy 객체
        """
        self.cfg_like = cfg_like
        
        # policy 저장
        self.policy: ConfigPolicy = policy if policy else self._load_loader_policy()
        
        # YamlParser 초기화 (사용자 데이터 파싱용, policy.reference_context 사용)
        self.parser: YamlParser = YamlParser(policy=self.policy.yaml, context=self.policy.reference_context)
        
        # ConfigNormalizer 초기화 (policy.reference_context 사용)
        self.normalizer: ConfigNormalizer = ConfigNormalizer(self.policy)
        
        self._data: KeyPathDict = KeyPathDict()
        self._load_and_merge()
    
    def _load_loader_policy(self) -> ConfigPolicy:
        """ConfigLoader 자신의 정책을 로드 (config_loader.yaml에서).
        
        Returns:
            최종 ConfigPolicy 인스턴스
        """
        # 기본 Policy 생성
        base_policy = ConfigPolicy()
        
        # 기본 경로
        config_loader_path = Path(__file__).parent.parent / "configs" / "config_loader.yaml"
        
        # config_loader.yaml이 있으면 로드하여 병합
        if config_loader_path.exists():
            try:
                # 단순 YamlParser로 로드
                parser = YamlParser(policy=BaseParserPolicy())
                text = config_loader_path.read_text(encoding="utf-8")
                parsed = parser.parse(text)
                
                # "config_loader" 섹션 추출
                if isinstance(parsed, dict) and "config_loader" in parsed:
                    config_data = parsed["config_loader"]
                    # ConfigPolicy로 변환
                    return ConfigPolicy(**config_data)
            except Exception:
                # 파일 로드 실패 시 기본값 사용
                pass
        
        return base_policy

    # ------------------------------------------------------------------
    # Loading & merging helpers
    # ------------------------------------------------------------------
    def _load_and_merge(self) -> None:
        """Load and merge config sources via MergerFactory.
        
        ✅ IMPROVED: 중복 제거 - load_source 직접 사용으로 PathMerger와 중복 제거
        """
        deep = self.policy.merge_mode == "deep"
        has_source = False  # 유효한 소스가 있는지 추적

        # 1) Merge sources defined in policy.yaml.source_paths (if yaml policy exists)
        if self.policy.yaml and hasattr(self.policy.yaml, 'source_paths') and self.policy.yaml.source_paths:
            for src_cfg in self._normalize_source_paths(self.policy.yaml.source_paths):
                src_path = Path(src_cfg.path)
                
                # ✅ FIX: load_source 직접 사용 (PathMerger와 중복 제거)
                data = load_source(src_path, self.parser)
                if src_cfg.section and isinstance(data, dict):
                    data = data.get(src_cfg.section, {})
                
                if data:  # 데이터가 있으면 소스로 인정
                    self._data.merge(data, deep=deep)
                    has_source = True

        # 2) Merge cfg_like input if provided
        if self.cfg_like is not None:
            merger = MergerFactory.get(self.cfg_like, self)
            merger.merge(self.cfg_like, self._data, deep)
            has_source = True

        # 3) 유효한 소스가 없으면 경고 로그 (빈 dict 반환)
        if not has_source:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                "No valid configuration source provided. "
                "Returning empty dict. "
                "Consider providing cfg_like parameter or setting policy.yaml.source_paths."
            )

        # 4) Final normalization step (references, placeholders, drop blanks, etc.)
        self._apply_normalization()

    def _normalize_source_paths(
        self,
        source_paths: Union[SourcePathConfig, List[SourcePathConfig], str, Path, dict, List[Union[str, Path, dict]]]
    ) -> List[SourcePathConfig]:
        """source_paths를 SourcePathConfig 리스트로 정규화.
        
        지원하는 입력:
        - SourcePathConfig: 단일 소스 (그대로 사용)
        - List[SourcePathConfig]: 복수 소스 (그대로 사용)
        - 편의 변환 (자동으로 SourcePathConfig로 변환):
          * 단일 문자열/Path: "file.yaml" → SourcePathConfig(path="file.yaml", section=None)
          * Dict: {"path": "file.yaml", "section": "app"} → SourcePathConfig(...)
          * List[str/Path/dict]: 각 항목을 SourcePathConfig로 변환
        
        Returns:
            SourcePathConfig 리스트
        """
        # ✅ FIX: isinstance로 타입 체크 (타입 안정성 향상)
        # SourcePathConfig 타입 체크 (isinstance 대신 type name 비교)
        if type(source_paths).__name__ == 'SourcePathConfig':
            return [source_paths]
        
        # List[SourcePathConfig]는 그대로 사용
        if isinstance(source_paths, list):
            # 리스트는 그대로 진행
            pass
        # 단일 경로/dict를 list로 변환
        elif isinstance(source_paths, (str, Path)):
            source_paths = [source_paths]
        elif isinstance(source_paths, dict):
            # Pure dict만 변환
            source_paths = [source_paths]
        else:
            raise TypeError(f"Unsupported source_paths type: {type(source_paths)}")
        
        normalized: List[SourcePathConfig] = []
        
        for item in source_paths:  # type: ignore
            if type(item).__name__ == 'SourcePathConfig':
                # 이미 SourcePathConfig
                normalized.append(item)  # type: ignore
            elif isinstance(item, dict):
                # Dict를 SourcePathConfig로 변환
                if 'path' in item:
                    normalized.append(SourcePathConfig(**item))
                else:
                    raise ValueError(f"Dict source must have 'path' key: {item}")
            elif isinstance(item, (str, Path)):
                # 단순 경로: section=None
                normalized.append(SourcePathConfig(path=str(item), section=None))
            else:
                raise TypeError(f"Unsupported source_paths item type: {type(item)}")
        
        return normalized

    # ✅ REMOVED: _merge_from_* 메서드들을 제거하여 중복 제거
    # - _merge_from_base_model → ModelMerger와 중복
    # - _merge_from_path → PathMerger와 중복 (load_source 직접 사용으로 대체)
    # - _merge_from_sequence → helpers.merge_sequence로 대체
    # - _merge_from_dict → DictMerger로 처리
    # 모든 병합은 MergerFactory를 통해 처리됩니다.

    def _apply_normalization(self) -> None:
        """Run normalizer and replace internal storage with the normalized dict."""
        normalized = self.normalizer.apply(self._data.data)
        self._data = KeyPathDict(normalized)

    # ------------------------------------------------------------------
    # Internal helpers (기존 as_dict, as_model을 private로 변경)
    # ------------------------------------------------------------------
    def _as_dict_internal(self, **overrides: Any) -> Dict[str, Any]:
        """Return the merged configuration as a plain dict (internal use only).

        Args:
            **overrides: Runtime overrides to apply on top of the result.
            
        Returns:
            The configuration as a dictionary.
        """
        data = dict(self._data.data)

        # Apply runtime overrides (policy.keypath 사용)
        if overrides:
            return apply_overrides(data, overrides, policy=self.policy)

        return data

    def _as_model_internal(self, model: Type[T], **overrides: Any) -> T:
        """Validate the merged configuration as a Pydantic model instance (internal use only).
        
        Args:
            model: The Pydantic model class to validate against.
            **overrides: Runtime overrides to apply before validation.
            
        Returns:
            Validated model instance.
        """
        # Get base data (section already extracted during merge)
        data = dict(self._data.data)
        
        # Apply runtime overrides (policy.keypath 사용)
        if overrides:
            data = apply_overrides(data, overrides, policy=self.policy)
        
        # Ensure keys are strings
        data = {str(k): v for k, v in data.items()}
        try:
            return model(**data)
        except ValidationError as exc:  # pragma: no cover - validation errors flow to caller
            raise TypeError(f"[ConfigLoader] Failed to load config as model '{model.__name__}': {exc}")

    # ------------------------------------------------------------------
    # Backward compatibility (deprecated - use load() instead)
    # ------------------------------------------------------------------

