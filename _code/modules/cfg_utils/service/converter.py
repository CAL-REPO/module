# -*- coding: utf-8 -*-
"""cfg_utils_v2.service.state_converter
========================================

KeyPathState와 다른 데이터 형식 간 변환 유틸리티.

책임:
- BaseModel → KeyPathState 변환
- Dict → KeyPathState 변환  
- KeyPathState → Dict 변환
- KeyPathState → BaseModel 변환
- Section 이름 관리
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Type, Union

from pydantic import BaseModel

from modules.data_utils.core.types import T
from modules.keypath_utils import KeyPathState

class StateConverter:
    """KeyPathState 변환 유틸리티."""
    
    @staticmethod
    def to_keypath_state(
        source: Union[BaseModel, Dict[str, Any]],
        section: Optional[str] = None,
        name: Optional[str] = None
    ) -> KeyPathState:
        """BaseModel 또는 Dict를 KeyPathState로 변환.
        
        Args:
            source: BaseModel 인스턴스 또는 Dict
            section: Section 이름 (지정 시 해당 section으로 wrap)
            name: State 이름 (없으면 section 사용)
        
        Returns:
            KeyPathState 인스턴스
        
        Examples:
            >>> # BaseModel → KeyPathState
            >>> policy = ImagePolicy(max_width=1024)
            >>> state = StateConverter.to_keypath_state(policy, section="image")
            >>> state.get("image__max_width")
            1024
            
            >>> # Dict → KeyPathState (section 없음)
            >>> data = {"max_width": 1024}
            >>> state = StateConverter.to_keypath_state(data)
            >>> state.get("max_width")
            1024
            
            >>> # Dict → KeyPathState (section 지정)
            >>> state = StateConverter.to_keypath_state(data, section="image")
            >>> state.get("image__max_width")
            1024
        """
        # BaseModel → dict
        if isinstance(source, BaseModel):
            data = source.model_dump()
        elif isinstance(source, dict):
            data = source.copy()
        else:
            raise TypeError(
                f"Expected BaseModel or dict, got {type(source)}"
            )
        
        # Section 처리: section이 지정되면 wrap
        if section:
            data = {section: data}
        
        # KeyPathState 생성
        state = KeyPathState(
            name=name or section or "",
            store=data  # Dict[str, Any]
        )
        
        return state
    
    @staticmethod
    def to_dict(
        state: KeyPathState,
        section: Optional[str] = None
    ) -> Dict[str, Any]:
        """KeyPathState를 Dict로 변환.
        
        Args:
            state: KeyPathState 인스턴스
            section: 추출할 section (없으면 전체 반환)
        
        Returns:
            Dict
        
        Examples:
            >>> state = KeyPathState()
            >>> state.set("image__max_width", 1024)
            >>> StateConverter.to_dict(state)
            {'image': {'max_width': 1024}}
            
            >>> StateConverter.to_dict(state, section="image")
            {'max_width': 1024}
        """
        data = state.to_dict(copy=True)
        
        # Section 추출
        if section and section in data:
            return data[section]
        
        return data
    
    @staticmethod
    def to_model(
        state: KeyPathState,
        model_class: Type[T],
        section: Optional[str] = None
    ) -> T:
        """KeyPathState를 BaseModel 인스턴스로 변환.
        
        Args:
            state: KeyPathState 인스턴스
            model_class: BaseModel 클래스
            section: 추출할 section (없으면 전체 사용)
        
        Returns:
            BaseModel 인스턴스
        
        Examples:
            >>> state = KeyPathState()
            >>> state.set("image__max_width", 1024)
            >>> policy = StateConverter.to_model(
            ...     state,
            ...     ImagePolicy,
            ...     section="image"
            ... )
            >>> policy.max_width
            1024
        """
        data = StateConverter.to_dict(state, section=section)
        return model_class(**data)