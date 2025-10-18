# -*- coding: utf-8 -*-
# keypath_utils/core/accessor.py
# 경로 기반 dict 접근 유틸리티 클래스

from __future__ import annotations
from typing import Any, Callable, Dict, List
from data_utils.core.types import KeyPath
from .policy import KeyPathNormalizePolicy


class KeyPathAccessor:
    """KeyPath를 사용하여 중첩된 dict에 접근하는 유틸리티 클래스.
    
    Examples:
        >>> data = {}
        >>> accessor = KeyPathAccessor(data)
        >>> accessor.set("a__b__c", 123)
        >>> accessor.get("a__b__c")
        123
        >>> accessor.exists("a__b__c")
        True
    """
    
    def __init__(self, data: Dict[str, Any]):
        self._data = data
        self._normalizer = None
    
    def _get_normalizer(self):
        """Lazy import로 순환 참조 방지"""
        if self._normalizer is None:
            from keypath_utils.services.normalizer import KeyPathNormalizer
            # KeyPathNormalizePolicy는 기본값 사용 (sep="__", collapse=True 등)
            self._normalizer = KeyPathNormalizer(KeyPathNormalizePolicy())  # type: ignore
        return self._normalizer
    
    def _normalize_path(self, path: KeyPath) -> List[str]:
        """KeyPath를 List[str]로 정규화"""
        return self._get_normalizer().apply(path)

    def get(self, path: KeyPath, default: Any = None) -> Any:
        """경로의 값을 조회합니다.
        
        Args:
            path: 조회할 경로
            default: 경로가 없을 때 반환할 기본값
            
        Returns:
            조회된 값 또는 default
        """
        cur = self._data
        for k in self._normalize_path(path):
            if not isinstance(cur, dict) or k not in cur:
                return default
            cur = cur[k]
        return cur

    def exists(self, path: KeyPath) -> bool:
        """경로가 존재하는지 확인합니다.
        
        Args:
            path: 확인할 경로
            
        Returns:
            경로 존재 여부
        """
        sentinel = object()
        return self.get(path, sentinel) is not sentinel

    def set(self, path: KeyPath, value: Any) -> None:
        """경로에 값을 설정합니다. 중간 경로가 없으면 자동 생성합니다.
        
        Args:
            path: 설정할 경로
            value: 설정할 값
        """
        keys = self._normalize_path(path)
        cur = self._data
        for k in keys[:-1]:
            if k not in cur or not isinstance(cur[k], dict):
                cur[k] = {}
            cur = cur[k]
        cur[keys[-1]] = value

    def delete(self, path: KeyPath, ignore_missing: bool = True) -> None:
        """경로의 값을 삭제합니다.
        
        Args:
            path: 삭제할 경로
            ignore_missing: 존재하지 않는 경로 무시 여부
            
        Raises:
            KeyError: ignore_missing=False이고 경로가 존재하지 않을 때
        """
        keys = self._normalize_path(path)
        cur = self._data
        for k in keys[:-1]:
            if not isinstance(cur, dict) or k not in cur:
                if ignore_missing:
                    return
                raise KeyError(k)
            cur = cur[k]
        if isinstance(cur, dict) and keys[-1] in cur:
            del cur[keys[-1]]
        elif not ignore_missing:
            raise KeyError(keys[-1])

    def ensure(self, path: KeyPath, default_factory: Callable[[], Any] = dict) -> Any:
        """경로를 확보합니다. 경로가 없으면 생성합니다.
        
        Args:
            path: 확보할 경로
            default_factory: 경로가 없을 때 생성할 값의 팩토리 함수
            
        Returns:
            경로의 값
        """
        keys = self._normalize_path(path)
        cur = self._data
        for k in keys[:-1]:
            if k not in cur or not isinstance(cur[k], dict):
                cur[k] = {}
            cur = cur[k]
        last = keys[-1]
        if last not in cur or not isinstance(cur[last], type(default_factory())):
            cur[last] = default_factory()
        return cur[last]

