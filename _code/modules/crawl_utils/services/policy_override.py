# -*- coding: utf-8 -*-
"""
Policy Override Processor - Policy 필드에 KeyPath override 적용

책임:
1. 긴 KeyPath를 Policy 모델에 적용
2. 배열 인덱스 처리 (items__0__dir_path → items[0].dir_path)
3. Pydantic model_copy(update={...}) 활용

설계 원칙:
- Policy 전용 (JS Data override 불필요)
- Nested dict 변환 후 Pydantic 적용
- 깔끔한 API (apply 메서드 하나)

Examples:
    >>> from crawl_utils.services.policy_override import PolicyOverrideProcessor
    >>> from crawl_utils.core.policy import SyncCrawlPolicy
    >>> 
    >>> policy = SyncCrawlPolicy(**yaml_config)
    >>> 
    >>> overrides = {
    ...     "items__0__dir_path": "/custom/path",
    ...     "items__0__fso_name__prefix": "TEST",
    ...     "scroll__max_scrolls": 10
    ... }
    >>> 
    >>> processor = PolicyOverrideProcessor()
    >>> updated_policy = processor.apply(policy, overrides)
    >>> 
    >>> # 결과 확인
    >>> assert updated_policy.items[0].dir_path == Path("/custom/path")
    >>> assert updated_policy.items[0].fso_name.prefix == "TEST"
    >>> assert updated_policy.scroll.max_scrolls == 10
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import re

from pydantic import BaseModel
from keypath_utils.services import KeyPathDict


class PolicyOverrideProcessor:
    """Policy 필드에 KeyPath override 적용.
    
    긴 KeyPath (sync_crawl__items__0__dir_path)를 Policy 모델에 적용하는 전용 모듈.
    
    Features:
    1. 배열 인덱스 자동 처리 (items__0, items__1 등)
    2. 중첩 필드 지원 (items__0__fso_name__prefix)
    3. Pydantic 호환 (model_copy 사용)
    
    Architecture:
    - KeyPath → Nested dict 변환 (KeyPathDict.to_nested_dict)
    - 배열 인덱스 처리 (items__0 → items[0])
    - Pydantic model_copy(update={...})
    
    Examples:
        >>> processor = PolicyOverrideProcessor()
        >>> 
        >>> # 단순 필드 override
        >>> overrides = {"scroll__max_scrolls": 10}
        >>> updated = processor.apply(policy, overrides)
        >>> 
        >>> # 배열 인덱스 override
        >>> overrides = {
        ...     "items__0__dir_path": "/custom/path",
        ...     "items__1__fso_name__prefix": "TEST2"
        ... }
        >>> updated = processor.apply(policy, overrides)
        >>> 
        >>> # 중첩 필드 override
        >>> overrides = {
        ...     "items__0__fso_name__prefix": "CAPEA",
        ...     "items__0__fso_name__name": "custom_name",
        ...     "items__0__fso_ops__overwrite": True
        ... }
        >>> updated = processor.apply(policy, overrides)
    """
    
    # 배열 인덱스 패턴 (items__0, items__1 등)
    ARRAY_INDEX_PATTERN = re.compile(r"^(.+)__(\d+)(__.*)?$")
    
    def apply(
        self,
        policy: BaseModel,
        overrides: Dict[str, Any]
    ) -> BaseModel:
        """Policy에 KeyPath override 적용.
        
        Args:
            policy: 원본 Policy 모델 (SyncCrawlPolicy 등)
            overrides: Flat KeyPath dict
                예: {"items__0__dir_path": "/path", "scroll__max_scrolls": 10}
        
        Returns:
            업데이트된 Policy (새 인스턴스, 원본 유지)
        
        Process:
            1. 배열 인덱스 추출 및 그룹화
            2. Nested dict 변환 (KeyPathDict.to_nested_dict)
            3. 배열 필드 재구성
            4. Pydantic model_copy(update={...})
        
        Example:
            >>> overrides = {
            ...     "items__0__dir_path": "/custom/path",
            ...     "items__0__fso_name__prefix": "TEST",
            ...     "items__1__dir_path": "/another/path",
            ...     "scroll__max_scrolls": 10
            ... }
            >>> 
            >>> updated_policy = processor.apply(policy, overrides)
            >>> 
            >>> # items[0] 검증
            >>> assert updated_policy.items[0].dir_path == Path("/custom/path")
            >>> assert updated_policy.items[0].fso_name.prefix == "TEST"
            >>> 
            >>> # items[1] 검증
            >>> assert updated_policy.items[1].dir_path == Path("/another/path")
            >>> 
            >>> # 일반 필드 검증
            >>> assert updated_policy.scroll.max_scrolls == 10
        """
        if not overrides:
            return policy
        
        # 1. 배열 인덱스가 있는 override와 없는 override 분리
        array_overrides: Dict[str, Dict[int, Dict[str, Any]]] = {}  # field → {index → {subfield → value}}
        simple_overrides: Dict[str, Any] = {}
        
        for key, value in overrides.items():
            match = self.ARRAY_INDEX_PATTERN.match(key)
            if match:
                # 배열 인덱스 패턴: items__0__dir_path
                field = match.group(1)  # "items"
                index = int(match.group(2))  # 0
                rest = match.group(3)  # "__dir_path"
                
                if field not in array_overrides:
                    array_overrides[field] = {}
                if index not in array_overrides[field]:
                    array_overrides[field][index] = {}
                
                if rest:
                    # 하위 필드 있음 (dir_path, fso_name__prefix 등)
                    subkey = rest[2:]  # "__" 제거
                    array_overrides[field][index][subkey] = value
                else:
                    # 하위 필드 없음 (items__0 자체)
                    array_overrides[field][index] = value
            else:
                # 단순 KeyPath: scroll__max_scrolls
                simple_overrides[key] = value
        
        # 2. 단순 override 처리 (KeyPathDict.to_nested_dict 사용)
        update_dict = {}
        if simple_overrides:
            update_dict = KeyPathDict.to_nested_dict(simple_overrides)
        
        # 3. 배열 override 처리
        for field, indices_dict in array_overrides.items():
            # 기존 배열 가져오기 (없으면 빈 리스트)
            current_array = getattr(policy, field, [])
            if not isinstance(current_array, list):
                current_array = []
            
            # 배열 복사 (원본 유지)
            new_array = [item.model_copy() if isinstance(item, BaseModel) else item for item in current_array]
            
            # 인덱스별 업데이트
            for index, override_data in indices_dict.items():
                # 배열 크기 확장 (필요시)
                while len(new_array) <= index:
                    # 기존 배열의 첫 요소를 템플릿으로 사용 (없으면 None)
                    if current_array:
                        template = current_array[0]
                        if isinstance(template, BaseModel):
                            new_array.append(template.model_copy())
                        else:
                            new_array.append(None)
                    else:
                        new_array.append(None)
                
                # 해당 인덱스 업데이트
                if isinstance(override_data, dict):
                    # 중첩 필드 override (dir_path, fso_name__prefix 등)
                    item = new_array[index]
                    if isinstance(item, BaseModel):
                        # Pydantic 모델: to_nested_dict → model_copy
                        nested_update = KeyPathDict.to_nested_dict(override_data)
                        
                        # Path 타입 변환
                        if "dir_path" in nested_update and isinstance(nested_update["dir_path"], str):
                            nested_update["dir_path"] = Path(nested_update["dir_path"])
                        
                        new_array[index] = item.model_copy(update=nested_update)
                    else:
                        # dict: 직접 업데이트
                        if item is None:
                            item = {}
                        nested_update = KeyPathDict.to_nested_dict(override_data)
                        
                        # Path 타입 변환
                        if "dir_path" in nested_update and isinstance(nested_update["dir_path"], str):
                            nested_update["dir_path"] = Path(nested_update["dir_path"])
                        
                        new_array[index] = {**item, **nested_update}
                else:
                    # 전체 교체
                    new_array[index] = override_data
            
            # update_dict에 추가
            update_dict[field] = new_array
        
        # 4. 단순 override의 Path 타입 변환 (재귀 처리)
        def convert_paths(data: Any) -> Any:
            """재귀적으로 path 문자열을 Path 객체로 변환"""
            if isinstance(data, dict):
                result = {}
                for k, v in data.items():
                    if k == "dir_path" and isinstance(v, str):
                        result[k] = Path(v)
                    elif isinstance(v, dict):
                        result[k] = convert_paths(v)
                    else:
                        result[k] = v
                return result
            else:
                return data
        
        update_dict = convert_paths(update_dict)
        
        # 5. Pydantic model_copy 적용
        try:
            return policy.model_copy(update=update_dict)
        except Exception as e:
            # Fallback: 원본 반환 + 로그
            import logging
            logging.warning(f"PolicyOverrideProcessor: model_copy failed - {e}")
            logging.debug(f"update_dict: {update_dict}")
            return policy
    
    def validate_override_keys(
        self,
        policy: BaseModel,
        overrides: Dict[str, Any]
    ) -> List[str]:
        """Override 키 검증 (선택적).
        
        Args:
            policy: Policy 모델
            overrides: Override dict
        
        Returns:
            유효하지 않은 키 리스트 (빈 리스트면 모두 유효)
        
        Example:
            >>> invalid_keys = processor.validate_override_keys(policy, overrides)
            >>> if invalid_keys:
            ...     print(f"Invalid keys: {invalid_keys}")
        """
        invalid = []
        
        for key in overrides.keys():
            # 배열 인덱스 제거
            match = self.ARRAY_INDEX_PATTERN.match(key)
            if match:
                field = match.group(1)
                rest = match.group(3)
                check_key = f"{field}{rest}" if rest else field
            else:
                check_key = key
            
            # KeyPath를 리스트로 변환
            parts = check_key.split("__")
            
            # Policy 모델에 필드 존재 여부 확인 (재귀)
            current = policy
            valid = True
            for part in parts:
                if isinstance(current, BaseModel):
                    if part not in current.model_fields:
                        valid = False
                        break
                    current = getattr(current, part, None)
                elif isinstance(current, dict):
                    if part not in current:
                        valid = False
                        break
                    current = current.get(part)
                else:
                    valid = False
                    break
            
            if not valid:
                invalid.append(key)
        
        return invalid


__all__ = ["PolicyOverrideProcessor"]
