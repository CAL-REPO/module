# -*- coding: utf-8 -*-
"""cfg_utils_v2.service.normalizer
===================================

KeyPathDict 정규화 처리기.

책임:
- 키 정규화 (소문자 변환, 공백 제거 등)
- 빈 값 제거 (None, "", [], {} 등)
- 변수 해결 ($ref: 참조, ${VAR} 환경 변수 등)
"""

from __future__ import annotations

from typing import Any, Dict, Literal

from modules.keypath_utils import KeyPathDict

from ..core.policy import NormalizePolicy


class Normalizer:
    """정규화 처리기 (정책 기반).
    
    NormalizePolicy를 기반으로 KeyPathDict를 정규화합니다.
    
    정규화 단계:
    - extract: Source에서 데이터 추출 직후
    - merge: ConfigLoader에서 병합 직후 (선택적)
    - final: 최종 export 직전
    
    Examples:
        >>> policy = NormalizePolicy(
        ...     normalize_keys=True,
        ...     drop_blanks=True,
        ...     resolve_vars=True
        ... )
        >>> normalizer = Normalizer(policy)
        >>> kpd = KeyPathDict(data={"Max_Width": 1024, "format": ""})
        >>> result = normalizer.normalize(kpd, stage="extract")
        >>> result.data
        {"max_width": 1024}  # 키 정규화 + 빈 값 제거
    """
    
    def __init__(self, policy: NormalizePolicy):
        """초기화.
        
        Args:
            policy: NormalizePolicy 인스턴스
        """
        self.policy = policy
    
    def normalize(
        self,
        kpd: KeyPathDict,
        stage: Literal["extract", "merge", "final"] = "extract"
    ) -> KeyPathDict:
        """KeyPathDict 정규화.
        
        정규화 순서:
        1. 키 정규화 (normalize_keys=True)
        2. 빈 값 제거 (drop_blanks=True)
        3. 변수 해결 (resolve_vars=True, final 단계만)
        
        Args:
            kpd: KeyPathDict
            stage: 정규화 단계
                - "extract": Source 추출 직후
                - "merge": ConfigLoader 병합 직후
                - "final": 최종 export 직전
        
        Returns:
            정규화된 KeyPathDict
        
        Examples:
            >>> kpd = KeyPathDict(data={"Max_Width": 1024, "empty": ""})
            >>> normalizer = Normalizer(
            ...     NormalizePolicy(normalize_keys=True, drop_blanks=True)
            ... )
            >>> result = normalizer.normalize(kpd, stage="extract")
            >>> result.data
            {"max_width": 1024}
        """
        data = kpd.data
        
        # 1. 키 정규화
        if self.policy.normalize_keys:
            data = self._normalize_keys(data)
        
        # 2. 빈 값 제거
        if self.policy.drop_blanks:
            data = self._drop_blanks(data)
        
        # 3. 변수 해결 (final 단계만)
        if self.policy.resolve_vars and stage == "final":
            resolved_kpd = KeyPathDict(data=data)
            data = resolved_kpd.resolve_all().data
        
        return KeyPathDict(data=data)
    
    def _normalize_keys(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """키 정규화 (재귀).
        
        정규화 규칙:
        - 소문자 변환 (Max_Width → max_width)
        - 앞뒤 공백 제거 (" key " → "key")
        - 연속 공백 단일 공백으로 변환 ("key  name" → "key name")
        
        Args:
            data: 원본 dict
        
        Returns:
            정규화된 dict
        
        Examples:
            >>> normalizer = Normalizer(NormalizePolicy(normalize_keys=True))
            >>> normalizer._normalize_keys({"Max_Width": 1024})
            {"max_width": 1024}
        """
        normalized = {}
        for key, value in data.items():
            # 키 정규화: 소문자 + 공백 정리
            normalized_key = key.lower().strip()
            normalized_key = " ".join(normalized_key.split())  # 연속 공백 제거
            
            # 값이 dict면 재귀
            if isinstance(value, dict):
                normalized[normalized_key] = self._normalize_keys(value)
            else:
                normalized[normalized_key] = value
        
        return normalized
    
    def _drop_blanks(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """빈 값 제거 (재귀).
        
        제거 대상:
        - None
        - 빈 문자열 ("")
        - 빈 리스트 ([])
        - 빈 dict ({})
        - 중첩 dict가 빈 경우
        
        Note: 0, False는 유효한 값이므로 유지
        
        Args:
            data: 원본 dict
        
        Returns:
            빈 값이 제거된 dict
        
        Examples:
            >>> normalizer = Normalizer(NormalizePolicy(drop_blanks=True))
            >>> normalizer._drop_blanks({"width": 1024, "empty": "", "none": None})
            {"width": 1024}
            
            >>> normalizer._drop_blanks({"debug": False, "count": 0})
            {"debug": False, "count": 0}  # 0, False는 유지
        """
        cleaned = {}
        for key, value in data.items():
            # dict면 재귀 처리
            if isinstance(value, dict):
                nested = self._drop_blanks(value)
                if nested:  # 빈 dict 제거
                    cleaned[key] = nested
            # 빈 값 제거 (0, False는 유지)
            elif value is not None and value != "" and value != [] and value != {}:
                cleaned[key] = value
        
        return cleaned

