# -*- coding: utf-8 -*-
# cfg_utils_v2/service/override_processor.py

"""OverrideProcessor: Override 소스 처리.

설계 철학:
1. override_sources는 기존 모듈의 정책값 확정을 위해 존재
2. 기존 키만 덮어쓰기 (새 키 생성 안 함)
3. Section 존재 여부 확인 (override_requires_base 정책)

SRP 준수:
- Override Section 검증 (base_sections 확인)
- 기존 키 필터링 (새 키 제거)
- 안전한 Override 처리
"""

from __future__ import annotations
from typing import Optional, Set

from modules.keypath_utils import KeyPathState, KeyPathDict


class OverrideProcessor:
    """Override 소스 처리기.
    
    핵심 원칙:
    1. override_requires_base=True (기본값):
       - Section이 base_sections에 없으면 에러
       - 오타 방지, 명시적 의도 확인
    
    2. 기존 키만 덮어쓰기:
       - BaseModel 구조 보존
       - 새 키는 무시 (에러 아님, 조용히 필터링)
       - Pydantic validation 통과 보장
    
    사용 예시:
        >>> # ✅ 올바른 사용 (Section이 base에 존재)
        >>> processor = OverrideProcessor(base_sections={"image"}, require_base=True)
        >>> state = processor.process(state, override_kpd, section="image")
        
        >>> # ❌ 에러 발생 (Section이 base에 없음)
        >>> processor = OverrideProcessor(base_sections={"image"}, require_base=True)
        >>> state = processor.process(state, override_kpd, section="ocr")
        >>> # ValueError: Override section 'ocr' does not exist in base_sections
    """
    
    def __init__(self, base_sections: Set[str], require_base: bool = True):
        """초기화.
        
        Args:
            base_sections: BaseModel에 정의된 sections (base_sources에서 생성)
            require_base: override section이 base_sections에 존재해야 하는지 여부
                - True (기본값): Section이 base에 없으면 에러
                - False: Section이 base에 없어도 병합 허용
        """
        self.base_sections = base_sections
        self.require_base = require_base
    
    def process(
        self,
        state: KeyPathState,
        override_kpd: KeyPathDict,
        section: Optional[str]
    ) -> KeyPathState:
        """Override 소스 처리.
        
        처리 단계:
        1. Section 검증 (require_base 정책)
        2. 기존 키 추출 (state에서 현재 존재하는 키)
        3. 기존 키만 필터링 (새 키 제거)
        4. 안전한 Override (shallow merge)
        
        Args:
            state: 현재 KeyPathState (base_sources 포함)
            override_kpd: Override할 KeyPathDict
            section: Override할 Section (None이면 root)
        
        Returns:
            업데이트된 KeyPathState
        
        Raises:
            ValueError: section이 base_sections에 없고 require_base=True인 경우
        
        Examples:
            >>> # ✅ 기존 키 덮어쓰기
            >>> # state: {"image": {"max_width": 1024, "format": "jpg"}}
            >>> # override_kpd: {"image": {"max_width": 2048}}
            >>> # 결과: {"image": {"max_width": 2048, "format": "jpg"}}
            
            >>> # ⚠️ 새 키는 무시됨
            >>> # state: {"image": {"max_width": 1024}}
            >>> # override_kpd: {"image": {"new_field": "value"}}
            >>> # 결과: {"image": {"max_width": 1024}}  (new_field 무시)
        """
        # 1. Section 검증 (require_base 정책)
        if self.require_base and section:
            if section not in self.base_sections:
                raise ValueError(
                    f"Override section '{section}' does not exist in base_sections: {sorted(self.base_sections)}. "
                    f"Add the section to base_sources first, or set override_requires_base=False in policy. "
                    f"Note: override_sources can only modify existing keys, not create new sections."
                )
        
        # 2. 기존 키 추출
        current_data = state.to_dict()
        existing_keys = self._get_existing_keys(current_data, section)
        
        # 3. 기존 키만 필터링 (새 키 제거)
        filtered_kpd = self._filter_existing_keys(override_kpd, existing_keys, section)
        
        # 4. 안전한 Override (shallow merge)
        if filtered_kpd.data:  # 필터링 후 데이터가 있을 때만 병합
            state.merge(filtered_kpd.data, deep=False)
        
        return state
    
    def _get_existing_keys(
        self,
        current_data: dict,
        section: Optional[str]
    ) -> Set[str]:
        """현재 state에서 존재하는 키 추출.
        
        Args:
            current_data: 현재 state의 dict
            section: Section 이름 (None이면 root)
        
        Returns:
            존재하는 키 집합 (KeyPath 형식)
        """
        existing_keys = set()
        
        if section:
            # Section이 있는 경우: "image.max_width" 형식
            section_data = current_data.get(section, {})
            if isinstance(section_data, dict):
                for key in section_data.keys():
                    existing_keys.add(f"{section}.{key}")
        else:
            # Section 없는 경우: root 레벨 키
            for key, value in current_data.items():
                if isinstance(value, dict):
                    # 중첩된 키도 추출
                    for subkey in value.keys():
                        existing_keys.add(f"{key}.{subkey}")
                else:
                    existing_keys.add(key)
        
        return existing_keys
    
    def _filter_existing_keys(
        self,
        override_kpd: KeyPathDict,
        existing_keys: Set[str],
        section: Optional[str]
    ) -> KeyPathDict:
        """기존 키만 필터링 (새 키 제거).
        
        Args:
            override_kpd: Override할 KeyPathDict
            existing_keys: 존재하는 키 집합
            section: Section 이름
        
        Returns:
            필터링된 KeyPathDict (기존 키만 포함)
        """
        filtered_data = {}
        
        if section:
            # Section이 있는 경우
            section_data = override_kpd.data.get(section, {})
            if isinstance(section_data, dict):
                filtered_section = {}
                for key, value in section_data.items():
                    keypath = f"{section}.{key}"
                    if keypath in existing_keys:
                        filtered_section[key] = value
                
                if filtered_section:
                    filtered_data[section] = filtered_section
        else:
            # Section 없는 경우
            for key, value in override_kpd.data.items():
                if isinstance(value, dict):
                    # 중첩된 dict 처리
                    filtered_sub = {}
                    for subkey, subvalue in value.items():
                        keypath = f"{key}.{subkey}"
                        if keypath in existing_keys:
                            filtered_sub[subkey] = subvalue
                    
                    if filtered_sub:
                        filtered_data[key] = filtered_sub
                else:
                    # 단일 값
                    if key in existing_keys:
                        filtered_data[key] = value
        
        return KeyPathDict(data=filtered_data)
