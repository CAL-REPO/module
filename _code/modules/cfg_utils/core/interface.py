# -*- coding: utf-8 -*-
"""cfg_utils_v2.core.interface
================================

Configuration 소스 추상 인터페이스.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING, Literal

from modules.keypath_utils import KeyPathDict

if TYPE_CHECKING:
    from ..core.policy import BaseModelSourcePolicy, DictSourcePolicy, YamlSourcePolicy


class SourceBase(ABC):
    """Configuration 소스 추상화 (Policy 기반).
    
    모든 configuration 소스는 이 인터페이스를 구현합니다.
    
    핵심 원칙:
    - Policy만 받음 (src, section, normalizer, merge 모두 Policy에 있음)
    - extract() 메서드는 항상 KeyPathDict 반환
    - Section 처리는 extract() 내부에서 수행
    - 정규화는 Source 자체에서 수행 (extract 단계)
    
    설계 철학:
    - Source = Policy Executor (Policy를 실행하는 주체)
    - Policy = Data + Configuration (데이터와 설정의 결합)
    - 각 Source는 자신의 Policy 타입만 받음
    """
    
    @abstractmethod
    def extract(self) -> KeyPathDict:
        """데이터 추출 및 KeyPathDict 변환.
        
        Policy의 src에서 데이터를 추출하고 KeyPathDict로 변환합니다.
        
        Returns:
            KeyPathDict 인스턴스
        
        Examples:
            >>> from cfg_utils_v2.core.policy import DictSourcePolicy
            >>> policy = DictSourcePolicy(
            ...     src=({"max_width": 1024}, "image")
            ... )
            >>> source = DictSource(policy)
            >>> kpd = source.extract()
            >>> kpd.data
            {'image': {'max_width': 1024}}
        """
        ...
    
    def _apply_section(self, data: dict, section: str | None) -> dict:
        """Section 처리 (wrap).
        
        Args:
            data: 원본 데이터
            section: Section 이름
        
        Returns:
            Section으로 wrap된 데이터 (section이 없으면 그대로 반환)
        
        Examples:
            >>> self._apply_section({"max_width": 1024}, "image")
            {'image': {'max_width': 1024}}
            
            >>> self._apply_section({"max_width": 1024}, None)
            {'max_width': 1024}
        """
        if section:
            return {section: data}
        return data
    
    def _normalize(
        self,
        kpd: KeyPathDict,
        normalizer_policy: Any,
        stage: Literal["extract", "merge", "final"] = "extract"
    ) -> KeyPathDict:
        """정규화 (Policy 기반).
        
        Policy의 normalizer로 정규화를 수행합니다.
        
        Args:
            kpd: KeyPathDict
            normalizer_policy: NormalizePolicy 인스턴스
            stage: 정규화 단계 ("extract", "merge", "final")
        
        Returns:
            정규화된 KeyPathDict
        
        Examples:
            >>> from cfg_utils_v2.core.policy import NormalizePolicy
            >>> normalizer = NormalizePolicy(drop_blanks=True)
            >>> kpd = KeyPathDict(data={"width": 1024, "empty": ""})
            >>> result = self._normalize(kpd, normalizer, stage="extract")
            >>> result.data
            {"width": 1024}  # empty 제거됨
        """
        if normalizer_policy is None:
            return kpd
        
        from ..service.normalizer import Normalizer
        normalizer = Normalizer(policy=normalizer_policy)
        return normalizer.normalize(kpd, stage=stage)
