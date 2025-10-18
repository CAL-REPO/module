"""cfg_utils.core.base_service_loader
====================================

Base abstract class for all module EntryPoint services.

Responsibilities:
 - Standardize configuration loading pattern across all modules
 - Provide common _load_config() and _load_default_policy() implementations
 - Support section-based loading via ConfigLoader.load_with_section()
 - Allow subclasses to customize behavior via abstract methods

This reduces code duplication and ensures consistent behavior across:
 - ImageLoader
 - XlLoader
 - CrawlLoader
 - TranslatorLoader
 - etc.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Generic, Optional, TypeVar, Union

from pydantic import BaseModel

from modules.data_utils.core.types import PathLike
from modules.path_utils import resolve
from modules.structured_io.core.base_policy import SourcePathPolicy

from ..services.config_loader import ConfigLoader, ConfigPolicy


T = TypeVar('T', bound=BaseModel)


class BaseServiceLoader(ABC, Generic[T]):
    """서비스 로더 베이스 클래스.
    
    모든 모듈 EntryPoint가 상속하여 Configuration Load 패턴 통일.
    
    Subclass Requirements:
        - _get_policy_model(): Policy 모델 클래스 반환 (필수)
        - _get_config_loader_path(): config_loader_*.yaml 경로 반환 (필수)
        - _get_default_section(): 기본 section 이름 반환 (선택, 기본: None)
    
    Usage:
        >>> class ImageLoader(BaseServiceLoader[ImageLoaderPolicy]):
        ...     def _get_policy_model(self) -> type[ImageLoaderPolicy]:
        ...         return ImageLoaderPolicy
        ...     
        ...     def _get_config_loader_path(self) -> Path:
        ...         return Path(__file__).parent.parent / "configs" / "config_loader_image.yaml"
        ...     
        ...     def _get_default_section(self) -> str:
        ...         return "image"
        ...     
        ...     def __init__(self, cfg_like=None, *, policy=None, **overrides):
        ...         super().__init__(cfg_like, policy=policy, **overrides)
        ...         # 모듈별 추가 초기화...
    
    Attributes:
        policy: 로드된 Policy 인스턴스 (타입: T)
    """
    
    policy: T
    
    def __init__(
        self,
        cfg_like: Union[BaseModel, PathLike, dict, None] = None,
        *,
        policy: Optional[ConfigPolicy] = None,
        config_loader_path: Optional[PathLike] = None,
        **overrides: Any
    ):
        """BaseServiceLoader 초기화.
        
        Args:
            cfg_like: 설정 소스 (BaseModel, YAML 경로, dict, 또는 None)
                - None: policy.yaml.source_paths 사용 (fallback 지원)
            policy: ConfigPolicy 인스턴스 (None이면 config_loader_*.yaml 로드)
            config_loader_path: config_loader_*.yaml 경로 override (선택)
            **overrides: 런타임 오버라이드 (KeyPath 형식)
        """
        self.policy = self._load_config(
            cfg_like, 
            policy=policy, 
            config_loader_path=config_loader_path,
            **overrides
        )
    
    # ==========================================================================
    # Configuration Loading (공통 로직)
    # ==========================================================================
    
    def _load_config(
        self,
        cfg_like: Union[BaseModel, PathLike, dict, None],
        *,
        policy: Optional[ConfigPolicy] = None,
        config_loader_path: Optional[PathLike] = None,
        **overrides: Any
    ) -> T:
        """Configuration 로드 (통합 로직).
        
        Subclass는 이 메서드를 오버라이드할 필요 없음.
        대신 _get_* 메서드들을 구현하여 동작 커스터마이징.
        
        Args:
            cfg_like: 설정 소스
            policy: ConfigPolicy 인스턴스
            config_loader_path: config_loader_*.yaml 경로 override
            **overrides: 런타임 오버라이드
        
        Returns:
            로드된 Policy 인스턴스 (타입: T)
        """
        if policy is None:
            policy = self._load_default_policy(config_loader_path=config_loader_path)
        
        # if cfg_like is None:
        #     # cfg_like=None: policy.yaml.source_paths 사용
        #     default_section = self._get_default_section()
        #     if default_section is not None:
        #         return ConfigLoader.load_with_section(
        #             cfg_like=None,
        #             model=self._get_policy_model(),
        #             policy=policy,
        #             default_section=default_section,
        #             **overrides
        #         )
        
        # cfg_like가 Path이고 default_section이 있으면 section 처리
        if isinstance(cfg_like, (str, Path)):
            default_section = self._get_default_section()
            if default_section is not None:
                return ConfigLoader.load_with_section(
                    cfg_like=cfg_like,
                    model=self._get_policy_model(),
                    policy=policy,
                    default_section=default_section,
                    **overrides
                )
        
        # cfg_like 제공 시 일반 로드 (dict, BaseModel 등)
        return ConfigLoader.load(
            cfg_like, # pyright: ignore[reportArgumentType]
            model=self._get_policy_model(),
            policy=policy,
            **overrides
        ) # type: ignore
    
    def _load_default_policy(
        self, 
        config_loader_path: Optional[PathLike] = None
    ) -> ConfigPolicy:
        """기본 ConfigPolicy 로드.
        
        Subclass는 이 메서드를 오버라이드할 필요 없음.
        대신 _get_config_loader_path()와 _get_reference_context()를 구현.
        
        마지막 안전 장치:
            1. config_loader_*.yaml이 없거나 None일 경우
            2. source_paths가 None이거나 파일이 존재하지 않을 경우
            3. _get_config_path()가 구현되어 있으면 해당 경로를 source_paths에 추가
        
        Args:
            config_loader_path: config_loader_*.yaml 경로 override (선택)
        
        Returns:
            로드된 ConfigPolicy 인스턴스
        """
        # config_loader_path가 제공되면 우선 사용, 아니면 _get_config_loader_path() 호출
        if config_loader_path is not None:
            config_path = Path(config_loader_path)
        else:
            config_path = self._get_config_loader_path()
        
        # reference_context 준비 (PathsLoader 등)
        ref_context = self._get_reference_context()
        
        try:
            # load_policy_from_file에 context 전달 (Placeholder 치환용)
            policy = ConfigLoader.load_policy_from_file(config_path, context=ref_context)
        except Exception as e:
            # validation 실패 시 fallback 시도
            policy = self._create_fallback_policy(ref_context)
            if policy is None:
                # fallback도 실패하면 원래 예외 발생
                raise
        
        # reference_context 추가 주입 (ConfigNormalizer용)
        if ref_context:
            # load_policy_from_file에서 이미 주입되었지만, 명시적으로 병합
            policy.reference_context = {**policy.reference_context, **ref_context}
        
        # 마지막 안전 장치: source_paths 검증 및 fallback
        self._apply_config_path_fallback(policy)
        
        return policy
    
    def _create_fallback_policy(self, ref_context: dict[str, Any]) -> Optional[ConfigPolicy]:
        """Fallback ConfigPolicy 생성.
        
        config_loader_*.yaml 로드 실패 시 _get_config_path()를 사용하여
        최소한의 ConfigPolicy 생성.
        
        Args:
            ref_context: reference context
        
        Returns:
            Fallback ConfigPolicy 또는 None (_get_config_path()가 없으면)
        """
        config_path = self._get_config_path()
        
        # _get_config_path()가 없으면 fallback 불가
        if config_path is None:
            return None
        
        from modules.structured_io.core.base_policy import BaseParserPolicy
        
        # 최소한의 ConfigPolicy 생성
        default_section = self._get_default_section()
        fallback_source = SourcePathPolicy(
            path=str(config_path),
            section=default_section
        )
        
        yaml_policy = BaseParserPolicy(source_paths=[fallback_source])
        
        # ConfigPolicy 생성 (yaml을 dict로 변환하여 전달)
        policy = ConfigPolicy(yaml=yaml_policy.model_dump())
        
        # reference_context 주입
        if ref_context:
            policy.reference_context = {**policy.reference_context, **ref_context}
        
        return policy
    
    def _apply_config_path_fallback(self, policy: ConfigPolicy) -> None:
        """마지막 안전 장치: source_paths 검증 및 _get_config_path() fallback.
        
        검증 조건:
            1. policy.yaml이 None
            2. source_paths가 None이거나 빈 리스트
            3. source_paths의 모든 경로가 존재하지 않음
            4. source_paths의 모든 path가 None
        
        Fallback:
            - _get_config_path()가 구현되어 있으면 해당 경로를 source_paths에 추가
            - _get_default_section()이 있으면 section도 함께 설정
        
        Args:
            policy: 검증할 ConfigPolicy 인스턴스 (in-place 수정)
        """
        config_path = self._get_config_path()
        
        # _get_config_path()가 구현되지 않았으면 안전 장치 비활성화
        if config_path is None:
            return
        
        # source_paths 검증
        needs_fallback = False
        
        # Case 1: policy.yaml이 None
        if policy.yaml is None:
            needs_fallback = True
        elif not policy.yaml.source_paths:
            # Case 2: source_paths가 None이거나 빈 리스트
            needs_fallback = True
        else:
            # Case 3 & 4: 모든 경로가 None이거나 존재하지 않음
            valid_paths = []
            for source in policy.yaml.source_paths:
                # SourcePathConfig 인스턴스인지 확인 (클래스 이름으로 비교)
                # isinstance()가 False일 수 있음 (import 경로 차이)
                if not (isinstance(source, SourcePathPolicy) or type(source).__name__ == 'SourcePathConfig'):
                    continue
                
                # path 속성이 있는지 확인
                if not hasattr(source, 'path'):
                    continue
                
                if source.path is not None:
                    try:
                        resolved_path = resolve(source.path)
                        if resolved_path.exists():
                            valid_paths.append(source)
                    except (ValueError, OSError):
                        # 경로 해석 실패 시 무시
                        pass
            
            # 유효한 경로가 하나도 없으면 fallback 필요
            if not valid_paths:
                needs_fallback = True
        
        # Fallback 적용
        if needs_fallback:
            from modules.structured_io.core.base_policy import BaseParserPolicy
            
            default_section = self._get_default_section()
            fallback_source = SourcePathPolicy(
                path=str(config_path),
                section=default_section
            )
            
            # policy.yaml이 None이면 생성
            if policy.yaml is None:
                policy.yaml = BaseParserPolicy()
            
            # source_paths 덮어쓰기 (마지막 안전 장치)
            # Pydantic validation을 위해 dict로 변환
            policy.yaml.source_paths = [fallback_source.model_dump()] # type: ignore
    
    # ==========================================================================
    # Abstract Methods (Subclass에서 구현)
    # ==========================================================================
    
    @abstractmethod
    def _get_policy_model(self) -> type[T]:
        """Policy 모델 클래스 반환.
        
        Returns:
            Pydantic 모델 클래스 (예: ImageLoaderPolicy, XlLoaderPolicy)
        
        Example:
            >>> def _get_policy_model(self) -> type[ImageLoaderPolicy]:
            ...     return ImageLoaderPolicy
        """
        pass
    
    @abstractmethod
    def _get_config_loader_path(self) -> Path:
        """config_loader_*.yaml 파일 경로 반환.
        
        Returns:
            config_loader_*.yaml 절대 경로
        
        Example:
            >>> def _get_config_loader_path(self) -> Path:
            ...     return Path(__file__).parent.parent / "configs" / "config_loader_image.yaml"
        """
        pass
    
    # ==========================================================================
    # Optional Override Methods (Subclass에서 선택적으로 구현)
    # ==========================================================================
    
    def _get_default_section(self) -> Optional[str]:
        """기본 section 이름 반환 (선택 사항).
        
        Returns:
            기본 section 이름, 또는 None (section 미사용)
            - "image": ImageLoader의 기본 section
            - "excel": XlLoader의 기본 section
            - None: section 미사용 (root에서 로드)
        
        Notes:
            - config_loader.yaml의 source_paths에서 section이 None이면 이 값 사용
            - section이 명시되면 그 값이 우선
        
        Example:
            >>> def _get_default_section(self) -> str:
            ...     return "image"  # ImageLoader는 "image" section 사용
        """
        return None
    
    def _get_reference_context(self) -> dict[str, Any]:
        """Reference 해석용 추가 context 반환.
        
        Returns:
            reference_context에 추가할 dict (기본: 빈 dict)
            - PathsLoader.load()로 paths.local.yaml 주입 가능
        
        Example:
            >>> def _get_reference_context(self) -> dict[str, Any]:
            ...     from modules.cfg_utils.services.paths_loader import PathsLoader
            ...     return PathsLoader.load()
        """
        return {}
    
    def _get_config_path(self) -> Optional[Path]:
        """마지막 안전 장치용 기본 설정 파일 경로 반환 (선택 사항).
        
        Returns:
            기본 설정 파일 경로, 또는 None (안전 장치 미사용)
            - ImageLoader: image.yaml
            - XlLoader: excel.yaml
            - None: 안전 장치 미사용
        
        Notes:
            - config_loader_*.yaml의 source_paths가 None이거나 파일이 없을 때 사용
            - _get_default_section()과 함께 마지막 안전 장치 구성
            - source_paths 검증 실패 시에만 fallback으로 사용
        
        Example:
            >>> def _get_config_path(self) -> Path:
            ...     return Path(__file__).parent.parent / "configs" / "image.yaml"
        """
        return None
