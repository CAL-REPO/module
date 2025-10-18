# -*- coding: utf-8 -*-
"""cfg_utils_v2.core.interface
================================

Configuration 소스 추상 인터페이스.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional, TYPE_CHECKING, Literal

from modules.keypath_utils import KeyPathDict

if TYPE_CHECKING:
    from ..core.policy import SourcePolicy


class SourceBase(ABC):
    """Configuration 소스 추상화 (SourcePolicy 기반).
    
    모든 configuration 소스는 이 인터페이스를 구현합니다.
    
    핵심 원칙:
    - extract() 메서드는 항상 KeyPathDict 반환
    - Section 처리는 extract() 내부에서 수행
    - SourcePolicy로 정책 통합 관리 (normalizer, merge, yaml_parser)
    - 정규화는 Source 자체에서 수행 (extract 단계)
    
    설계 철학:
    - Source = Data + SourcePolicy (데이터와 정책의 결합)
    - Policy Cascade: ConfigLoader 전역 정책 → Source 개별 정책
    - 소스 타입별 자동 처리: YAML→parser, Dict→normalizer만
    """
    
    def __init__(
        self,
        src(data: Union[Any,)
        policy: Optional["SourcePolicy"] = None,  # SourcePolicy (통합 정책)
    ):
        """ConfigSource 초기화.
        
        Args:
            data: 원본 데이터
            section: Section 이름 (지정 시 해당 section으로 wrap)
            policy: SourcePolicy 인스턴스 (normalizer, merge, yaml_parser 포함)
                - None이면 기본 정책 사용
        """
        self.raw_data = data
        self.section = section
        self.policy = policy
    
    @abstractmethod
    def extract(self) -> KeyPathDict:
        """데이터 추출 및 KeyPathDict 변환.
        
        Returns:
            KeyPathDict 인스턴스
        
        Examples:
            >>> source = DictSource({"max_width": 1024}, section="image")
            >>> kpd = source.extract()
            >>> kpd.data
            {'image': {'max_width': 1024}}
        """
        ...
    
    def _apply_section(self, data: dict) -> dict:
        """Section 처리 (wrap).
        
        Args:
            data: 원본 데이터
        
        Returns:
            Section으로 wrap된 데이터 (section이 없으면 그대로 반환)
        
        Examples:
            >>> self.section = "image"
            >>> self._apply_section({"max_width": 1024})
            {'image': {'max_width': 1024}}
            
            >>> self.section = None
            >>> self._apply_section({"max_width": 1024})
            {'max_width': 1024}
        """
        if self.section:
            return {self.section: data}
        return data
    
    def _normalize(
        self,
        kpd: KeyPathDict,
        stage: Literal["extract", "merge", "final"] = "extract"
    ) -> KeyPathDict:
        """정규화 (SourcePolicy 기반).
        
        SourcePolicy의 normalizer가 있으면 정규화를 수행합니다.
        
        Args:
            kpd: KeyPathDict
            stage: 정규화 단계 ("extract", "merge", "final")
        
        Returns:
            정규화된 KeyPathDict
        
        Examples:
            >>> # policy가 None이면 그대로 반환
            >>> self.policy = None
            >>> result = self._normalize(kpd)
            >>> result is kpd
            True
            
            >>> # policy.normalizer가 있으면 정규화 수행
            >>> from cfg_utils_v2.core.policy import SourcePolicy, NormalizePolicy
            >>> self.policy = SourcePolicy(normalizer=NormalizePolicy(drop_blanks=True))
            >>> kpd = KeyPathDict(data={"width": 1024, "empty": ""})
            >>> result = self._normalize(kpd, stage="extract")
            >>> result.data
            {"width": 1024}  # empty 제거됨
        """
        if self.policy is None or self.policy.normalizer is None:
            return kpd
        
        from ..service.normalizer import Normalizer
        normalizer = Normalizer(policy=self.policy.normalizer)
        return normalizer.normalize(kpd, stage=stage)
