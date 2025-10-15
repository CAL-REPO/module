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
from typing import Any, Dict, Iterable, List, Sequence, Type, Union, Optional, overload

from pydantic import BaseModel, ValidationError

from modules.data_utils.core.types import T, PathLike, PathsLike
from modules.data_utils.services.dict_ops import DictOps

from modules.structured_io.core.base_policy import BaseParserPolicy, SourcePathConfig
from modules.structured_io.formats.yaml_io import YamlParser

from keypath_utils import KeyPathDict, KeyPathState

from .normalizer import ConfigNormalizer
from ..core.policy import ConfigPolicy



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
        cfg_like: Union[BaseModel, PathLike, PathsLike, dict, None],
        *,
        model: Type[T],
        policy_overrides: Optional[Dict[str, Any]] = None,
        **overrides: Any
    ) -> T: ...
    
    @overload
    @staticmethod
    def load(
        cfg_like: Union[BaseModel, PathLike, PathsLike, dict, None],
        *,
        model: None = None,
        policy_overrides: Optional[Dict[str, Any]] = None,
        **overrides: Any
    ) -> dict: ...
    
    @staticmethod
    def load(
        cfg_like: Union[BaseModel, PathLike, PathsLike, dict, None],
        *,
        model: Optional[Type[T]] = None,
        policy_overrides: Optional[Dict[str, Any]] = None,
        **overrides: Any
    ) -> Union[dict, T]:
        """설정을 로드하여 dict 또는 Pydantic 모델로 반환.
        
        Args:
            cfg_like: 설정 소스 (BaseModel/Path/list[Path]/dict/None)
            model: Pydantic 모델 클래스 (있으면 모델 반환, 없으면 dict 반환)
            policy_overrides: ConfigPolicy 필드 개별 오버라이드
            **overrides: 최종 데이터 오버라이드 (deep merge)
        
        Returns:
            model이 있으면 Pydantic 모델 인스턴스, 없으면 dict
        
        Examples:
            Dict 반환: config = ConfigLoader.load("config.yaml")
            Pydantic 모델: policy = ConfigLoader.load("config.yaml", model=MyPolicy)
            여러 YAML 병합: config = ConfigLoader.load(["base.yaml", "prod.yaml"])
            Policy override: config = ConfigLoader.load("cfg.yaml", policy_overrides={"yaml.source_paths": [...]})
            Data override: config = ConfigLoader.load("cfg.yaml", image__max_width=1024)
        
        Notes:
            - ConfigPolicy는 config_loader.yaml에서 자동 로드됩니다.
            - policy_overrides로 개별 필드만 변경 가능합니다.
            - 전체 ConfigPolicy를 교체하려면 ConfigLoader 인스턴스를 직접 생성하세요.
        """
        # 1. 이미 모델 인스턴스인 경우
        if model and isinstance(cfg_like, model):
            if not overrides:
                return cfg_like
            # Overrides 적용
            config_dict = cfg_like.model_dump()
            temp = KeyPathDict(config_dict)
            temp.merge(overrides, deep=True)
            return model(**temp.data)
        
        # 2. None인 경우 처리
        if cfg_like is None:
            # policy_overrides에 yaml.source_paths가 있으면 ConfigLoader 생성
            if policy_overrides and "yaml.source_paths" in policy_overrides:
                loader = ConfigLoader._create_loader({}, policy_overrides=policy_overrides)  # type: ignore
                if model:
                    return loader._as_model_internal(model, section=None, **overrides)
                return loader._as_dict_internal(section=None, **overrides)
            # yaml.source_paths도 없으면 빈 dict로 처리
            cfg_like = {}
        
        # 3. Dict인 경우 직접 처리
        if isinstance(cfg_like, dict):
            # None 값 필터링 (Pydantic 기본값 사용 위해)
            cfg_like = DictOps.drop_none(cfg_like, deep=True)
            
            if overrides:
                temp = KeyPathDict(copy.deepcopy(cfg_like))
                temp.merge(overrides, deep=True)
                cfg_like = temp.data
            
            # Model이 있으면 변환, 없으면 dict 반환
            if model:
                return model(**cfg_like)
            return cfg_like
        
        # 4. List인 경우 여러 파일 병합
        if isinstance(cfg_like, (list, tuple)) and not isinstance(cfg_like, (str, bytes)):
            # 각 파일을 순서대로 로드하고 병합
            merged_dict = {}
            for cfg_path in cfg_like:
                # 각 파일을 dict로 로드 (재귀 호출, policy_overrides 전파)
                loaded = ConfigLoader.load(cfg_path, policy_overrides=policy_overrides)
                # Deep merge
                temp = KeyPathDict(merged_dict)
                temp.merge(loaded, deep=True)
                merged_dict = temp.data
            
            # Overrides 적용
            if overrides:
                temp = KeyPathDict(merged_dict)
                temp.merge(overrides, deep=True)
                merged_dict = temp.data
            
            # Model이 있으면 변환, 없으면 dict 반환
            if model:
                return model(**merged_dict)
            return merged_dict
        
        # 5. Path/str인 경우 ConfigLoader로 로드
        if isinstance(cfg_like, (str, Path)):
            loader = ConfigLoader._create_loader(cfg_like, policy_overrides=policy_overrides)
            
            # ConfigLoader 내부에서 이미 section 처리 완료
            # _as_*_internal에서는 section=None으로 전달 (재처리 방지)
            
            # Model이 있으면 모델로 변환
            if model:
                return loader._as_model_internal(model, section=None, **overrides)
            
            # Model이 없으면 dict 반환
            return loader._as_dict_internal(section=None, **overrides)
        
        # 6. 지원하지 않는 타입
        raise TypeError(f"Unsupported config type: {type(cfg_like)}")
    
    # ==========================================================================
    # Internal: 기존 로직 유지 (private)
    # ==========================================================================
    
    @staticmethod
    def _create_loader(
        cfg_like: Union[PathLike, PathsLike, dict],
        *,
        policy_overrides: Optional[Dict[str, Any]] = None
    ) -> "ConfigLoader":
        """ConfigLoader 인스턴스 생성 (내부용)"""
        return ConfigLoader(cfg_like, policy_overrides=policy_overrides)

    def __init__(
        self,
        cfg_like: Union[BaseModel, PathLike, PathsLike, dict],
        *,
        policy_overrides: Optional[Dict[str, Any]] = None
    ) -> None:
        """ConfigLoader 초기화.
        
        Override 우선순위:
        1. ConfigPolicy 기본값 (Pydantic defaults)
        2. config_loader.yaml 로드
        3. policy_overrides 파라미터
        """
        self.cfg_like = cfg_like
        
        # ConfigLoader 자신의 정책 로드 (KeyPathState 사용)
        self.policy: ConfigPolicy = self._load_loader_policy(policy_overrides=policy_overrides)
        
        # YamlParser 초기화 (사용자 데이터 파싱용)
        self.parser: YamlParser = YamlParser(policy=self.policy.yaml)
        
        self.normalizer: ConfigNormalizer = ConfigNormalizer(self.policy)
        self._data: KeyPathDict = KeyPathDict()
        self._load_and_merge()
    
    def _load_loader_policy(
        self,
        *,
        policy_overrides: Optional[Dict[str, Any]] = None
    ) -> ConfigPolicy:
        """ConfigLoader 자신의 정책을 로드 (KeyPathState 사용).
        
        Override 순서:
        1. ConfigPolicy 기본값
        2. config_loader_path에서 지정한 파일 (또는 기본 config_loader.yaml)
        3. policy_overrides 파라미터
        
        Args:
            policy_overrides: ConfigPolicy 필드 개별 오버라이드
                - config_loader_path: ConfigLoader 정책 파일 경로 지정 가능
        
        Returns:
            최종 ConfigPolicy 인스턴스
        """
        # 1. KeyPathState 초기화 (ConfigPolicy 기본값)
        policy_state = KeyPathState(
            name="config_policy",
            store=KeyPathDict(ConfigPolicy().model_dump())
        )
        
        # 2. config_loader_path 결정
        # policy_overrides에서 먼저 확인
        config_loader_path = None
        if policy_overrides and "config_loader_path" in policy_overrides:
            config_loader_path = Path(policy_overrides["config_loader_path"])
        
        # 기본 경로 사용
        if config_loader_path is None:
            config_loader_path = Path(__file__).parent.parent / "configs" / "config_loader.yaml"
        
        # 3. config_loader.yaml 병합
        if config_loader_path.exists():
            # 재귀 방지: 단순 YamlParser로 로드
            from modules.structured_io.formats.yaml_io import YamlParser
            parser = YamlParser(policy=BaseParserPolicy(
                source_paths=None,
                enable_env=False,
                enable_include=False,
                enable_placeholder=False,
                enable_reference=False,
                encoding="utf-8",
                on_error="raise",
                safe_mode=True
            ))
            text = config_loader_path.read_text(encoding="utf-8")
            parsed = parser.parse(text, base_path=config_loader_path)
            
            # "config_loader" 섹션 추출
            if isinstance(parsed, dict) and "config_loader" in parsed:
                policy_state.merge(parsed["config_loader"], deep=True)
            # 하위 호환성: config_policy
            elif isinstance(parsed, dict) and "config_policy" in parsed:
                policy_state.merge(parsed["config_policy"], deep=True)
        
        # 4. policy_overrides 병합
        if policy_overrides:
            for key, value in policy_overrides.items():
                # Pydantic BaseModel이면 dict로 변환
                if isinstance(value, BaseModel):
                    value = value.model_dump()
                elif isinstance(value, list):
                    # 리스트 내 BaseModel도 변환
                    value = [item.model_dump() if isinstance(item, BaseModel) else item for item in value]
                policy_state.override(key, value)
        
        # 5. 최종 ConfigPolicy 생성
        return ConfigPolicy(**policy_state.to_dict())

    # ------------------------------------------------------------------
    # Loading & merging helpers
    # ------------------------------------------------------------------
    def _load_and_merge(self) -> None:
        """Dispatch to the appropriate loader depending on input type."""
        deep = self.policy.merge_mode == "deep"

        # source_paths 자동 로드 (yaml.source_paths가 지정되어 있으면)
        if self.policy.yaml.source_paths:  # type: ignore
            # 1단계: source_paths를 SourcePathConfig 리스트로 정규화
            normalized_sources = self._normalize_source_paths(self.policy.yaml.source_paths)  # type: ignore
            
            # 2단계: 정규화된 소스들을 순서대로 병합
            for source_config in normalized_sources:
                self._merge_from_path(
                    Path(source_config.path),
                    deep=deep,
                    section=source_config.section
                )
        
        # cfg_like 처리
        if self.cfg_like is None:
            # source_paths만 사용하는 경우 허용
            pass
        elif isinstance(self.cfg_like, BaseModel):
            self._merge_from_base_model(self.cfg_like, deep=deep)
        elif isinstance(self.cfg_like, PathLike):
            self._merge_from_path(Path(self.cfg_like), deep=deep, section=None)
        elif isinstance(self.cfg_like, Sequence) and not isinstance(self.cfg_like, (str, bytes)):
            self._merge_from_sequence(self.cfg_like, deep=deep)
        elif isinstance(self.cfg_like, dict):
            self._merge_from_dict(self.cfg_like, deep=deep)
        else:
            raise TypeError(f"Unsupported config input: {type(self.cfg_like)!r}")

        # Final normalization step (references, placeholders, drop blanks etc.)
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
        # 이미 SourcePathConfig면 리스트로 감싸기
        # NOTE: isinstance 대신 클래스명 체크 (모듈 임포트 경로 차이 문제 회피)
        if type(source_paths).__name__ == 'SourcePathConfig':
            return [source_paths]  # type: ignore
        
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

    def _merge_from_base_model(self, model: BaseModel, *, deep: bool) -> None:
        """Merge values from a Pydantic BaseModel instance."""
        self._data.merge(model.model_dump(), deep=deep)

    def _merge_from_path(self, path: PathLike, *, deep: bool, section: Optional[str] = None) -> None:
        """Read a YAML file or parse YAML string and merge its contents.
        
        Args:
            path: Path to YAML file or raw YAML content string
            deep: Whether to deep merge
            section: Section to extract from parsed YAML. If None, merges entire content.
        """
        # Try to read as a file path first
        path_obj = Path(str(path))
        if path_obj.exists():
            text = path_obj.read_text(encoding=self.parser.policy.encoding)
        else:
            # Treat as raw YAML content string
            text = str(path)
        
        # Parse YAML content
        parsed = self.parser.parse(text, base_path=path_obj if path_obj.exists() else None)
        
        # Merge parsed data
        if isinstance(parsed, dict):
            # 섹션이 명시적으로 지정되었고 parsed에 해당 섹션이 있으면 추출
            if section and section in parsed:
                section_data = parsed[section]
                # 섹션 데이터가 None이 아닌지 확인
                if section_data is not None:
                    self._data.merge(section_data, deep=deep)
                # None이면 병합하지 않음 (빈 섹션)
            else:
                # 섹션이 없으면 전체 병합
                self._data.merge(parsed, deep=deep)
        else:
            # parsed가 dict가 아닌 경우 (scalar value)
            # 그냥 직접 병합 (섹션 없이)
            if parsed is not None:
                self._data.merge(parsed, deep=deep)

    def _merge_from_sequence(self, seq: Iterable[Union[str, Path]], *, deep: bool) -> None:
        """Merge multiple YAML files in order. Each entry may be a path or str."""
        for entry in seq:
            p = Path(entry)
            self._merge_from_path(p, deep=deep, section=None)

    def _merge_from_dict(self, data: Dict[str, Any], *, deep: bool) -> None:
        """Merge a plain dictionary into the current data."""
        self._data.merge(data, deep=deep)

    def _apply_normalization(self) -> None:
        """Run normalizer and replace internal storage with the normalized dict."""
        normalized = self.normalizer.apply(self._data.data)
        self._data = KeyPathDict(normalized)

    # ------------------------------------------------------------------
    # Overrides / small mutators
    # ------------------------------------------------------------------
    def merge_overrides(self, overrides: Dict[str, Any]) -> None:
        """Merge runtime overrides into the current data according to policy."""
        deep = self.policy.merge_mode == "deep"
        self._data.merge(overrides, deep=deep)

    def override_path(self, path: str, value: Any) -> None:
        """Directly override a single dotted key path in the data store."""
        self._data.override(path, value)

    # ------------------------------------------------------------------
    # Internal helpers (기존 as_dict, as_model을 private로 변경)
    # ------------------------------------------------------------------
    def _as_dict_internal(self, section: Optional[str] = None, **overrides: Any) -> Dict[str, Any]:
        """Return the merged configuration as a plain dict (internal use only).

        Args:
            section: Optional section key to extract from the configuration.
            **overrides: Runtime overrides to apply on top of the result.
            
        Returns:
            The configuration as a dictionary.
        """
        data = dict(self._data.data)  # shallow copy

        # Extract section if specified
        if section and section in data:
            data = data[section]
        elif section:
            # Section requested but not found - return empty dict or raise?
            # For now, return empty dict to match fallback behavior
            data = {}

        # Apply overrides if provided
        if overrides:
            deep = self.policy.merge_mode == "deep"
            temp = KeyPathDict(data)
            temp.merge(overrides, deep=deep)
            return temp.data

        return data

    def _as_model_internal(self, model: Type[T], section: Optional[str] = None, **overrides: Any) -> T:
        """Validate the merged configuration as a Pydantic model instance (internal use only).

        Section selection follows this order:
        1. explicit ``section`` argument
        2. auto-detect from the :class:`model` name ("MyPolicy" -> "mypolicy")
        3. fall back to the root mapping
        
        Args:
            model: The Pydantic model class to validate against.
            section: Optional section key to extract before validation.
            **overrides: Runtime overrides to apply before validation.
            
        Returns:
            Validated model instance.
        """
        # Get base data
        data = dict(self._data.data)
        
        # Apply section selection if explicitly provided
        if section and section in data:
            data = data[section]
        elif not section:
            # Best-effort auto-detection using model name patterns
            model_name = model.__name__.lower()
            candidates: list[str] = []
            if model_name.endswith("policy"):
                base = model_name[:-6]
                candidates.append(base)
                if base.startswith("image"):
                    candidates.append(base[5:])
            if model_name.endswith("config"):
                candidates.append(model_name[:-6])
            candidates.append(model_name)

            for key in candidates:
                if key and isinstance(data.get(key), dict):
                    data = data[key]
                    break

        # Apply overrides
        if overrides:
            # data가 dict인지 확인
            if not isinstance(data, dict):
                raise TypeError(f"Cannot apply overrides to non-dict data: {type(data)}")
            deep = self.policy.merge_mode == "deep"
            temp = KeyPathDict(data)
            temp.merge(overrides, deep=deep)
            data = temp.data

        # Ensure data is dict and keys are strings
        if not isinstance(data, dict):
            raise TypeError(f"Configuration data must be a dict, got {type(data)}")
        
        data = {str(k): v for k, v in data.items()}
        try:
            return model(**data)
        except ValidationError as exc:  # pragma: no cover - validation errors flow to caller
            raise TypeError(f"[ConfigLoader] Failed to load config as model '{model.__name__}': {exc}")

    # ------------------------------------------------------------------
    # Backward compatibility (deprecated - use load() instead)
    # ------------------------------------------------------------------

