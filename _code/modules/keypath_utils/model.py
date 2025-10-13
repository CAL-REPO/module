# -*- coding: utf-8 -*-
# keypath_utils/model.py
# 데이터 클래스만 정의 (KeyPathDict, KeyPathState)

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Optional, Dict
from data_utils.types import KeyPath
from .policy import KeyPathStatePolicy
from .accessor import KeyPathAccessor
from data_utils.dict_ops import DictOps


@dataclass
class KeyPathDict:
    data: Dict[str, Any] = field(default_factory=dict)

    def override(self, path: KeyPath, value: Any) -> KeyPathDict:
        KeyPathAccessor(self.data).set(path, value)
        return self

    def merge(self, patch: Mapping[str, Any], *, deep: bool = True, inplace: bool = True) -> KeyPathDict:
        if deep:
            DictOps.deep_update(self.data, dict(patch), inplace=inplace)
        else:
            self.data.update(patch)
        return self

    def rekey(self, mapping_or_func, *, deep: bool = True) -> KeyPathDict:
        updated = DictOps.rekey(self.data, mapping_or_func, deep=deep)
        self.data.clear()
        self.data.update(updated)
        return self


@dataclass
class KeyPathState:
    name: str = ""
    store: KeyPathDict = field(default_factory=KeyPathDict)
    policy: KeyPathStatePolicy = field(default_factory=lambda: KeyPathStatePolicy()) # type: ignore

    def rename(self, name: str) -> KeyPathState:
        self.name = name
        return self

    def get(self, path: KeyPath, default: Any = None) -> Any:
        return KeyPathAccessor(self.store.data).get(path, default)

    def exists(self, path: KeyPath) -> bool:
        return KeyPathAccessor(self.store.data).exists(path)

    def set(self, path: KeyPath, value: Any) -> KeyPathState:
        KeyPathAccessor(self.store.data).set(path, value)
        return self

    def delete(self, path: KeyPath, *, ignore_missing: bool = True) -> KeyPathState:
        KeyPathAccessor(self.store.data).delete(path, ignore_missing=ignore_missing)
        return self

    def ensure(self, path: KeyPath, default_factory: Callable[[], Any] = dict) -> Any:
        return KeyPathAccessor(self.store.data).ensure(path, default_factory)

    def override(self, path: KeyPath, value: Any) -> KeyPathState:
        if value is not None or self.policy.allow_override:
            self.set(path, value)
        return self

    def merge(self, patch: Dict[str, Any], *, path: Optional[KeyPath] = None, deep: Optional[bool] = None) -> KeyPathState:
        deep = self.policy.deep_merge if deep is None else deep
        if path:
            target = self.ensure(path, dict)
            DictOps.deep_update(target, patch, inplace=True)
        else:
            self.store.merge(patch, deep=deep)
        return self

    def to_dict(self, *, copy: bool = True) -> Dict[str, Any]:
        return dict(self.store.data) if copy else self.store.data
