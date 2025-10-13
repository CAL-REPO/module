# -*- coding: utf-8 -*-
# keypath_utils/accessor.py
# 경로 기반 dict 접근 유틸리티 클래스

from __future__ import annotations
from typing import Any, Callable, Dict
from data_utils.types import KeyPath
from unify_utils.normalizers.keypath_normalizer import KeyPathNormalizer, KeyPathNormalizePolicy

_keypath_norm = KeyPathNormalizer(KeyPathNormalizePolicy()) # pyright: ignore[reportCallIssue]

class KeyPathAccessor:
    def __init__(self, data: Dict[str, Any]):
        self._data = data

    def get(self, path: KeyPath, default: Any = None) -> Any:
        cur = self._data
        for k in _keypath_norm.apply(path):
            if not isinstance(cur, dict) or k not in cur:
                return default
            cur = cur[k]
        return cur

    def exists(self, path: KeyPath) -> bool:
        sentinel = object()
        return self.get(path, sentinel) is not sentinel

    def set(self, path: KeyPath, value: Any) -> None:
        keys = _keypath_norm.apply(path)
        cur = self._data
        for k in keys[:-1]:
            if k not in cur or not isinstance(cur[k], dict):
                cur[k] = {}
            cur = cur[k]
        cur[keys[-1]] = value

    def delete(self, path: KeyPath, ignore_missing: bool = True) -> None:
        keys = _keypath_norm.apply(path)
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
        keys = _keypath_norm.apply(path)
        cur = self._data
        for k in keys[:-1]:
            if k not in cur or not isinstance(cur[k], dict):
                cur[k] = {}
            cur = cur[k]
        last = keys[-1]
        if last not in cur or not isinstance(cur[last], type(default_factory())):
            cur[last] = default_factory()
        return cur[last]
