# -*- coding: utf-8 -*-
"""Section Extractor Service - Policy.name 기반 섹션 추출.

복합 모듈(Composite Adapter)에서 ConfigLoader 병합 결과를 
각 개별 모듈 cfg_like로 분리하는 유틸리티.

책임:
1. Policy.name 기반 섹션 추출 (하드코딩 제거)
2. 우선순위 적용 (개별 cfg_like > 통합 cfg_like > None)
3. 타입 안전성 보장

Example:
    >>> from cfg_utils.services.section_extractor import SectionExtractor
    >>> 
    >>> # ConfigLoader 병합 결과
    >>> merged_config = {
    ...     "image_load": {...},
    ...     "image_text_recognize": {...},
    ...     "translate": {...},
    ... }
    >>> 
    >>> # 개별 cfg_like 우선
    >>> cfg = SectionExtractor.extract(
    ...     merged_config=merged_config,
    ...     individual_cfg={"custom": "config"},  # 우선순위 1
    ...     policy_class=ImageLoadPolicy
    ... )
    >>> # Returns: {"custom": "config"}
    >>> 
    >>> # merged_config에서 추출
    >>> cfg = SectionExtractor.extract(
    ...     merged_config=merged_config,
    ...     individual_cfg=None,
    ...     policy_class=ImageLoadPolicy  # ImageLoadPolicy.name = "image_load"
    ... )
    >>> # Returns: {...} (merged_config["image_load"])
    >>> 
    >>> # 모두 없으면 None (Pydantic 기본값 사용)
    >>> cfg = SectionExtractor.extract(
    ...     merged_config={},
    ...     individual_cfg=None,
    ...     policy_class=ImageLoadPolicy
    ... )
    >>> # Returns: None
"""

from typing import Any, Dict, Optional, Type, Union
from pathlib import Path
from pydantic import BaseModel


class SectionExtractor:
    """Policy.name 기반 섹션 추출 서비스.
    
    복합 모듈(Oto, XLOto 등)에서 ConfigLoader 병합 결과를 
    각 개별 모듈의 cfg_like로 분리하는 유틸리티.
    
    Features:
        - Policy.name 기반 자동 섹션 추출 (하드코딩 완전 제거)
        - 우선순위 적용 (개별 > 통합 > None)
        - 타입 안전성 보장
        - Policy name 캐싱으로 성능 최적화
    
    Attributes:
        _policy_name_cache: Policy 클래스별 name 캐시 (성능 최적화)
    
    Example:
        >>> # Oto Adapter에서 사용
        >>> extracted = SectionExtractor.extract_batch(
        ...     merged_config=merged_config,
        ...     individual_cfgs={
        ...         ImageLoadPolicy: cfg_like_image_load,
        ...         TranslatePolicy: cfg_like_translate,
        ...     }
        ... )
        >>> # 추출 결과 접근 (하드코딩 없음)
        >>> cfg = extracted[SectionExtractor.get_policy_name(ImageLoadPolicy)]
    """
    
    # Policy name 캐시 (성능 최적화)
    _policy_name_cache: Dict[Type[BaseModel], str] = {}
    
    @classmethod
    def get_policy_name(cls, policy_class: Type[BaseModel]) -> str:
        """Policy 클래스에서 name 추출 (캐싱).
        
        Args:
            policy_class: Policy 클래스 (name 필드를 가진 Pydantic 모델)
        
        Returns:
            Policy.name (예: "image_load")
        
        Raises:
            AttributeError: policy_class에 name 필드가 없는 경우
        
        Example:
            >>> name = SectionExtractor.get_policy_name(ImageLoadPolicy)
            >>> # "image_load"
            >>> 
            >>> # 캐싱되므로 두 번째 호출은 빠름
            >>> name = SectionExtractor.get_policy_name(ImageLoadPolicy)
        
        Note:
            ⚠️ Policy 클래스의 name 필드는 Pydantic Field로 정의되어야 함:
            
            ```python
            class ImageLoadPolicy(BaseModel):
                name: str = Field(default="image_load")
                ...
            ```
        """
        # 캐시 확인
        if policy_class in cls._policy_name_cache:
            return cls._policy_name_cache[policy_class]
        
        # Policy 인스턴스 생성하여 name 추출
        try:
            default_instance = policy_class()
            section_name = default_instance.name  # type: ignore
            
            # 캐시 저장
            cls._policy_name_cache[policy_class] = section_name
            return section_name
            
        except AttributeError as e:
            raise AttributeError(
                f"❌ {policy_class.__name__}에 'name' 필드가 없습니다.\n"
                f"   Policy 클래스는 다음과 같이 name 필드를 정의해야 합니다:\n"
                f"   ```python\n"
                f"   class {policy_class.__name__}(BaseModel):\n"
                f"       name: str = Field(default=\"section_name\")\n"
                f"       ...\n"
                f"   ```"
            ) from e
        except Exception as e:
            # Fallback: 클래스명 소문자 (Policy 제거)
            section_name = policy_class.__name__.replace("Policy", "").lower()
            cls._policy_name_cache[policy_class] = section_name
            return section_name
    
    @staticmethod
    def extract(
        merged_config: Dict[str, Any],
        individual_cfg: Union[BaseModel, Path, str, dict, None],
        policy_class: Optional[Type[BaseModel]] = None,
        section_name: Optional[str] = None
    ) -> Union[BaseModel, Path, str, dict, None]:
        """Policy.name 또는 section_name 기반으로 section 추출 (우선순위 적용).
        
        우선순위:
        1. individual_cfg (개별 모듈 cfg_like) - 가장 높은 우선순위
        2. merged_config[section_name 또는 policy_class.name] (통합 설정의 해당 section)
        3. None (각 모듈의 Pydantic 기본값 사용)
        
        Args:
            merged_config: ConfigLoader.to_dict() 결과 (section별 병합 완료)
                예: {
                    "excel": {...},
                    "image_load": {...},
                    "translate": {...}
                }
            individual_cfg: 개별 모듈 cfg_like (우선순위 1)
                - BaseModel: Policy 인스턴스
                - Path/str: YAML 파일 경로
                - dict: 설정 딕셔너리
                - None: 통합 설정 또는 Pydantic 기본값 사용
            policy_class: Policy 클래스 (name 필드를 가진 Pydantic 모델)
                예: ImageLoadPolicy, ImageTextRecognizePolicy
                ⚠️ section_name과 함께 제공할 수 없음 (둘 중 하나만)
            section_name: 섹션명 직접 지정 (Policy 없는 경우)
                예: "excel" (XlController는 Policy 없음)
                ⚠️ policy_class와 함께 제공할 수 없음 (둘 중 하나만)
        
        Returns:
            추출된 section (BaseModel, Path, str, dict, 또는 None)
            - individual_cfg가 있으면 그대로 반환
            - merged_config[section_name]이 있으면 반환
            - 둘 다 없으면 None (각 모듈이 Pydantic 기본값 사용)
        
        Raises:
            ValueError: policy_class와 section_name이 모두 None인 경우
            ValueError: policy_class와 section_name을 동시에 제공한 경우
            TypeError: policy_class가 BaseModel이 아닌 경우
            AttributeError: policy_class에 name 필드가 없는 경우
        
        Example:
            >>> # Case 1: Policy 클래스 사용
            >>> cfg = SectionExtractor.extract(
            ...     merged_config={"image_load": {"resize": True}},
            ...     individual_cfg=None,
            ...     policy_class=ImageLoadPolicy  # name = "image_load"
            ... )
            
            >>> # Case 2: section_name 직접 지정 (Policy 없는 경우)
            >>> cfg = SectionExtractor.extract(
            ...     merged_config={"excel": {"aliases": {...}}},
            ...     individual_cfg=None,
            ...     section_name="excel"  # XlController는 Policy 없음
            ... )
            
            >>> # Case 3: individual_cfg 우선
            >>> cfg = SectionExtractor.extract(
            ...     merged_config={"image_load": {"resize": True}},
            ...     individual_cfg={"custom": True},  # ⭐ 우선순위 1
            ...     policy_class=ImageLoadPolicy
            ... )
        
        Note:
            ⚠️ policy_class와 section_name 중 정확히 하나만 제공해야 함!
        """
        # ========================================
        # 파라미터 검증
        # ========================================
        if policy_class is None and section_name is None:
            raise ValueError(
                "❌ policy_class 또는 section_name 중 하나는 필수입니다."
            )
        
        if policy_class is not None and section_name is not None:
            raise ValueError(
                "❌ policy_class와 section_name을 동시에 제공할 수 없습니다.\n"
                "   둘 중 하나만 제공하세요."
            )
        
        # ========================================
        # 타입 검증 (policy_class 사용 시)
        # ========================================
        if policy_class is not None and not issubclass(policy_class, BaseModel):
            raise TypeError(
                f"❌ policy_class는 Pydantic BaseModel이어야 합니다.\n"
                f"   받은 타입: {type(policy_class).__name__}"
            )
        
        # ========================================
        # 우선순위 1: individual_cfg (개별 모듈 cfg_like)
        # ========================================
        if individual_cfg is not None:
            return individual_cfg
        
        # ========================================
        # 우선순위 2: merged_config[section_name] (통합 설정)
        # ========================================
        
        # section_name 결정
        if section_name:
            # section_name 직접 제공 (Policy 없는 경우)
            target_section = section_name
        else:
            # policy_class에서 name 추출
            try:
                default_instance = policy_class()  # type: ignore
                target_section = default_instance.name  # type: ignore
            except AttributeError as e:
                raise AttributeError(
                    f"❌ {policy_class.__name__}에 'name' 필드가 없습니다.\n"  # type: ignore
                    f"   Policy 클래스는 다음과 같이 name 필드를 정의해야 합니다:\n"
                    f"   ```python\n"
                    f"   class {policy_class.__name__}(BaseModel):\n"  # type: ignore
                    f"       name: str = Field(default=\"section_name\")\n"
                    f"       ...\n"
                    f"   ```"
                ) from e
        
        # merged_config에서 해당 section 추출
        if target_section in merged_config:
            return merged_config[target_section]
        
        # ========================================
        # 우선순위 3: None (Pydantic 기본값)
        # ========================================
        return None
    
    @staticmethod
    def extract_batch(
        merged_config: Dict[str, Any],
        individual_cfgs: Dict[Type[BaseModel], Union[BaseModel, Path, str, dict, None]],
    ) -> Dict[str, Union[BaseModel, Path, str, dict, None]]:
        """여러 섹션을 한 번에 추출 (Policy 클래스 기반, 완전 하드코딩 제거).
        
        Args:
            merged_config: ConfigLoader.to_dict() 결과 (section별 병합 완료)
            individual_cfgs: Policy 클래스 → 개별 cfg_like 맵
                예: {
                    ImageLoadPolicy: cfg_like_image_load,
                    TranslatePolicy: cfg_like_translate,
                }
        
        Returns:
            section name → 추출된 cfg_like 맵
            예: {
                "image_load": {...},
                "translate": {...},
            }
        
        Example:
            >>> # ✅ Policy 클래스 기반 (하드코딩 제거)
            >>> result = SectionExtractor.extract_batch(
            ...     merged_config=merged_config,
            ...     individual_cfgs={
            ...         ImageLoadPolicy: None,
            ...         ImageTextRecognizePolicy: {"custom": True},
            ...         TranslatePolicy: None,
            ...         ImageOverlayPolicy: None,
            ...     }
            ... )
            >>> print(result)
            >>> # {
            >>> #     "image_load": {...},  # merged_config에서 추출
            >>> #     "image_text_recognize": {"custom": True},  # individual_cfg 우선
            >>> #     "translate": {...},
            >>> #     "image_overlay": {...}
            >>> # }
            >>> 
            >>> # ✅ get_policy_name() 헬퍼로 접근 (하드코딩 없음)
            >>> cfg = result[SectionExtractor.get_policy_name(ImageLoadPolicy)]
        
        Note:
            ⚠️ 반환값의 키는 Policy.name입니다 (Policy 클래스 아님).
            ⚠️ 순서는 individual_cfgs의 딕셔너리 삽입 순서를 따릅니다.
        """
        result = {}
        
        for policy_class, individual_cfg in individual_cfgs.items():
            # ✅ get_policy_name() 헬퍼로 name 추출 (캐싱됨)
            section_name = SectionExtractor.get_policy_name(policy_class)
            
            result[section_name] = SectionExtractor.extract(
                merged_config=merged_config,
                individual_cfg=individual_cfg,
                policy_class=policy_class
            )
        
        return result


__all__ = ['SectionExtractor']
