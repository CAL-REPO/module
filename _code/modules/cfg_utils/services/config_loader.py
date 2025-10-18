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

from pathlib import Path
from typing import Any, Dict, List, Type, Union, Optional, overload, Literal

from pydantic import BaseModel, ValidationError

from modules.data_utils.core.types import T, PathLike, PathsLike

from modules.structured_io.core.policy import BaseParserPolicy
from modules.structured_io.formats.yaml_io import YamlParser

from modules.keypath_utils import KeyPathDict

from .normalizer import ConfigNormalizer
from ..core.policy import ConfigPolicy, SourcePathPolicy
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
        
        # 4. Dict인 경우 ConfigLoader로 정규화 적용
        if isinstance(cfg_like, dict):
            # ConfigLoader 인스턴스 생성하여 정규화 적용
            loader = ConfigLoader(cfg_like, policy=temp_policy)
            
            # Model이 있으면 모델로 변환
            if model:
                return loader._as_model_internal(model, **overrides)
            
            # Model이 없으면 dict 반환
            return loader._as_dict_internal(**overrides)
        
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
            # ✅ FIX: cfg_like가 제공되면 source_paths 무시 (section wrap 방지)
            # policy의 source_paths를 제거한 복사본 생성
            if temp_policy.yaml and temp_policy.yaml.source_paths:
                yaml_policy_copy = temp_policy.yaml.model_copy(update={"source_paths": []})
                temp_policy = temp_policy.model_copy(update={"yaml": yaml_policy_copy})
            
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
    
    @staticmethod
    def load_policy_from_file(
        config_path: PathLike,
        section: str = "config_loader",
        context: dict[str, Any] | None = None
    ) -> ConfigPolicy:
        """config_loader_*.yaml 파일에서 ConfigPolicy 로드.
        
        자동으로:
        - YAML 파싱 (Placeholder/Env 치환 포함)
        - section 추출
        - source_paths 절대 경로 변환
        - ConfigPolicy 생성
        
        Args:
            config_path: config_loader_*.yaml 파일 경로
            section: YAML 내 section 이름 (기본: "config_loader")
            context: Placeholder 치환용 context ({{VAR}} 치환용)
                - None이면 PathsLoader 자동 로드 시도
        
        Returns:
            로드된 ConfigPolicy 인스턴스
        
        Raises:
            FileNotFoundError: 파일이 존재하지 않음
            KeyError: section이 YAML에 없음
            ValidationError: ConfigPolicy 검증 실패
        
        Examples:
            # ImageLoader에서 사용
            config_path = Path(__file__).parent.parent / "configs" / "config_loader_image.yaml"
            policy = ConfigLoader.load_policy_from_file(config_path)
            
            # XlLoader에서 사용
            config_path = Path(__file__).parent.parent / "configs" / "config_loader_xl.yaml"
            policy = ConfigLoader.load_policy_from_file(config_path)
            
            # Context 직접 제공
            policy = ConfigLoader.load_policy_from_file(
                config_path,
                context={"configs_dir": "/path/to/configs"}
            )
        """
        config_path = Path(config_path)
        
        # 파일 존재 확인
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        # Context 자동 로드 (PathsLoader 사용)
        if context is None:
            from modules.cfg_utils.services.paths_loader import PathsLoader
            try:
                context = PathsLoader.load()
            except FileNotFoundError:
                # paths.local.yaml이 없으면 빈 context 사용
                context = {}
        
        # YAML 파싱 (Placeholder/Env 치환 활성화)
        parser_policy = BaseParserPolicy(
            enable_placeholder=True,  # ✅ {{VAR}} 치환 활성화
            enable_env=True,          # ✅ ${VAR} 환경 변수 치환 활성화
        )
        parser = YamlParser(policy=parser_policy, context=context)
        data = parser.parse(
            config_path.read_text(encoding="utf-8"),
            base_path=config_path.parent
        )
        
        # Section 추출
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict from YAML, got {type(data)}")
        
        if section not in data:
            raise KeyError(f"Section '{section}' not found in {config_path}")
        
        config_section = data[section]
        
        # source_paths의 상대 경로를 절대 경로로 변환
        if "yaml" in config_section and "source_paths" in config_section["yaml"]:
            base_dir = config_path.parent  # config 파일이 있는 디렉토리
            
            source_paths = config_section["yaml"]["source_paths"]
            
            # source_paths가 리스트인 경우
            if isinstance(source_paths, list):
                for sp in source_paths:
                    if isinstance(sp, dict) and "path" in sp:
                        # path가 None이면 스킵
                        if sp["path"] is None:
                            continue
                        
                        sp_path = Path(sp["path"])
                        if not sp_path.is_absolute():
                            sp["path"] = str((base_dir / sp_path).resolve())
            # source_paths가 단일 dict인 경우
            elif isinstance(source_paths, dict) and "path" in source_paths:
                # path가 None이 아닐 때만 처리
                if source_paths["path"] is not None:
                    sp_path = Path(source_paths["path"])
                    if not sp_path.is_absolute():
                        source_paths["path"] = str((base_dir / sp_path).resolve())
        
        # ConfigPolicy 생성
        policy = ConfigPolicy(**config_section)
        
        # ✅ reference_context에 context 주입 (ConfigNormalizer용)
        if context:
            policy.reference_context = {**policy.reference_context, **context}
        
        return policy
    
    @classmethod
    def load_with_section(
        cls,
        cfg_like: Union[BaseModel, PathLike, PathsLike, dict[str, Any], None],
        model: Type[T],
        policy: ConfigPolicy,
        default_section: str,
        **overrides: Any
    ) -> T:
        """단일 section을 사용한 설정 로드 (단순화 버전).
        
        Args:
            cfg_like: 설정 소스 (None이면 policy.yaml.source_paths 사용)
            model: Pydantic 모델 클래스
            policy: ConfigPolicy 인스턴스
            default_section: 기본 section 이름 (source_paths에 section이 없으면 사용)
            **overrides: 런타임 오버라이드
        
        Returns:
            로드된 Pydantic 모델 인스턴스
        
        Raises:
            KeyError: section이 YAML에 없음
            ValidationError: 모델 검증 실패
        
        Examples:
            # ImageLoader
            policy = ConfigPolicy(yaml=BaseParserPolicy(source_paths=[...]))
            config = ConfigLoader.load_with_section(
                None,
                ImageLoaderPolicy,
                policy,
                default_section="image",
            )
        """
        # cfg_like가 Path/str이면 단일 파일로 처리
        if isinstance(cfg_like, (str, Path)):
            return cls._load_with_section_from_file(
                cfg_like, model, policy, default_section, **overrides
            )
        
        # cfg_like가 None: policy.yaml.source_paths 사용
        if cfg_like is None:
            return cls._load_with_section_from_policy(
                model, policy, default_section, **overrides
            )
        
        # dict, BaseModel 등은 일반 load() 사용
        return cls.load(cfg_like, model=model, policy=policy, **overrides)
    
    @classmethod
    def _load_with_section_from_file(
        cls,
        file_path: Union[str, Path],
        model: Type[T],
        policy: ConfigPolicy,
        default_section: str,
        **overrides: Any
    ) -> T:
        """파일에서 section 로드 (내부 helper)."""
        # source_paths 제거한 policy 생성
        temp_policy = cls._clear_source_paths(policy)
        
        # 로드 및 병합
        loader = cls(file_path, policy=temp_policy)
        loader._load_and_merge()
        
        # Section 추출
        section_data = loader.extract_section(default_section)
        if not section_data:
            # fallback: 전체 데이터에서 section 확인
            section_data = loader._data.data.get(default_section)
            if not section_data:
                raise KeyError(f"Section '{default_section}' not found in {file_path}")
        
        loader._data = KeyPathDict(section_data)
        return loader._as_model_internal(model, **overrides)
    
    @classmethod
    def _load_with_section_from_policy(
        cls,
        model: Type[T],
        policy: ConfigPolicy,
        default_section: str,
        **overrides: Any
    ) -> T:
        """policy.yaml.source_paths에서 section 로드 (내부 helper)."""
        from structured_io.core.base_policy import SourcePathPolicy
        
        if not policy.yaml or not policy.yaml.source_paths:
            raise TypeError("No source_paths configured in policy.yaml")
        
        # source_paths 정규화 및 default_section 적용
        source_paths = cls._apply_default_section_to_paths(
            policy.yaml.source_paths,
            default_section
        )
        
        # 새로운 policy 생성
        yaml_policy = policy.yaml.model_copy(update={"source_paths": source_paths})
        new_policy = policy.model_copy(update={"yaml": yaml_policy})
        
        # 로드 및 병합
        loader = cls(None, policy=new_policy)
        loader._load_and_merge()
        
        # Section 추출
        section_data = loader.extract_section(default_section)
        if not section_data:
            raise KeyError(f"Section '{default_section}' not found in source files")
        
        loader._data = KeyPathDict(section_data)
        return loader._as_model_internal(model, **overrides)
    
    @staticmethod
    def _clear_source_paths(policy: ConfigPolicy) -> ConfigPolicy:
        """policy에서 source_paths 제거 (section wrap 방지)."""
        if policy.yaml and policy.yaml.source_paths:
            yaml_policy_copy = policy.yaml.model_copy(update={"source_paths": []})
            return policy.model_copy(update={"yaml": yaml_policy_copy})
        return policy
    
    @staticmethod
    def _apply_default_section_to_paths(
        source_paths: Union[SourcePathPolicy, List[SourcePathPolicy]],
        default_section: str
    ) -> List[SourcePathPolicy]:
        """source_paths의 section이 None이면 default_section 적용."""
        # 리스트로 정규화
        if not isinstance(source_paths, list):
            source_paths = [source_paths]
        
        # section이 None이면 default_section 적용
        new_source_paths = []
        for sp in source_paths:
            if isinstance(sp, SourcePathPolicy):
                new_section = sp.section if sp.section is not None else default_section
                new_source_paths.append(SourcePathPolicy(path=sp.path, section=new_section))
            else:
                new_source_paths.append(sp)
        
        return new_source_paths
    
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
        """Load and merge config sources with section wrapping.
        
        ✅ IMPROVED:
        - Section 추출하지 않고 section 이름으로 wrap하여 병합
        - Section 구조 유지로 키 충돌 방지
        - 병합 후 필요할 때 extract_section()으로 추출
        """
        deep = self.policy.merge_mode == "deep"
        has_source = False  # 유효한 소스가 있는지 추적

        # 1) Merge sources defined in policy.yaml.source_paths (if yaml policy exists)
        if self.policy.yaml and hasattr(self.policy.yaml, 'source_paths') and self.policy.yaml.source_paths:
            for src_cfg in self._normalize_source_paths(self.policy.yaml.source_paths):
                src_path = Path(src_cfg.path)
                
                # YAML 파일 로드
                data = load_source(src_path, self.parser)
                
                # ✅ FIX: Section wrap (키 충돌 방지)
                if src_cfg.section and isinstance(data, dict):
                    # Section 추출 후 section 이름으로 다시 감싸기
                    section_data = data.get(src_cfg.section, {})
                    if section_data:  # Section 데이터가 있으면
                        wrapped = {src_cfg.section: section_data}
                        self._data.merge(wrapped, deep=deep)
                        has_source = True
                else:
                    # Section 없으면 원본 그대로 병합
                    if data:
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
        source_paths: Union[SourcePathPolicy, List[SourcePathPolicy], str, Path, dict, List[Union[str, Path, dict]]]
    ) -> List[SourcePathPolicy]:
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
        
        normalized: List[SourcePathPolicy] = []
        
        for item in source_paths:  # type: ignore
            if type(item).__name__ == 'SourcePathConfig':
                # 이미 SourcePathConfig
                normalized.append(item)  # type: ignore
            elif isinstance(item, dict):
                # Dict를 SourcePathConfig로 변환
                if 'path' in item:
                    normalized.append(SourcePathPolicy(**item))
                else:
                    raise ValueError(f"Dict source must have 'path' key: {item}")
            elif isinstance(item, (str, Path)):
                # 단순 경로: section=None
                normalized.append(SourcePathPolicy(path=str(item), section=None))
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
    
    # ==========================================================================
    # Section Extraction (Public API)
    # ==========================================================================
    
    def extract_section(self, section: str) -> dict[str, Any]:
        """병합된 데이터에서 특정 section 추출.
        
        Section wrap된 데이터에서 특정 section만 추출합니다.
        Section이 없으면 빈 dict를 반환합니다.
        
        Args:
            section: 추출할 section 이름 (예: "image", "ocr", "overlay", "translate")
            
        Returns:
            Section 데이터 (없으면 빈 dict)
            
        Examples:
            >>> # config_loader_oto.yaml 로드 (4개 section 병합)
            >>> policy = ConfigLoader.load_policy_from_file("configs/loader/config_loader_oto.yaml")
            >>> policy.reference_context = PathsLoader.load()
            >>> loader = ConfigLoader(cfg_like=None, policy=policy)
            >>> 
            >>> # 각 section 추출
            >>> image_config = loader.extract_section("image")
            >>> ocr_config = loader.extract_section("ocr")
            >>> 
            >>> # 사용
            >>> print(image_config["source"]["path"])
            >>> print(ocr_config["provider"]["provider"])
        """
        return self._data.data.get(section, {})
    
    def extract_sections(self, sections: list[str]) -> dict[str, dict[str, Any]]:
        """여러 section을 한 번에 추출.
        
        Args:
            sections: 추출할 section 이름 리스트
            
        Returns:
            {section_name: section_data, ...}
            
        Examples:
            >>> loader = ConfigLoader(cfg_like=None, policy=policy)
            >>> configs = loader.extract_sections(["image", "ocr", "overlay", "translate"])
            >>> 
            >>> # 각 section 접근
            >>> print(configs["image"]["source"]["path"])
            >>> print(configs["ocr"]["provider"]["provider"])
        """
        return {
            section: self.extract_section(section)
            for section in sections
        }

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
