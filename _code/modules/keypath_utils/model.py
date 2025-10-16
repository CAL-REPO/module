# -*- coding: utf-8 -*-
# keypath_utils/model.py
# 데이터 클래스만 정의 (KeyPathDict, KeyPathState)

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Optional, Dict
from data_utils.core.types import KeyPath
from .policy import KeyPathStatePolicy
from .accessor import KeyPathAccessor
from data_utils.services.dict_ops import DictOps


@dataclass
class KeyPathDict:
    data: Dict[str, Any] = field(default_factory=dict)
    # Separator for keypath segments (default dot)
    key_separator: str = field(default='.')

    def override(self, path: KeyPath, value: Any) -> KeyPathDict:
        # Override using KeyPathAccessor
        KeyPathAccessor(self.data).set(path, value)
        return self

    def merge(self, patch: Mapping[str, Any], *, deep: bool = True, inplace: bool = True) -> KeyPathDict:
        # Merge patch into data; deep merge or shallow update
        if deep:
            DictOps.deep_update(self.data, dict(patch), inplace=inplace)
        else:
            self.data.update(patch)
        return self

    def apply_overrides(
        self,
        overrides: Dict[str, Any],
        *,
        normalizer: Optional[Any] = None,
        accept_dot: bool = True
    ) -> KeyPathDict:
        """Apply overrides using KeyPathNormalizer for path interpretation.
        
        오버라이드 해석 책임을 normalizer로 위임하여 SRP 준수:
        - normalizer: KeyPath 문자열 해석기 (없으면 기본 "." 구분자 사용)
        - accept_dot: normalizer 실패 시 "." 구분자로 fallback 허용
        
        Args:
            overrides: Dict of key-value pairs to apply
            normalizer: Optional KeyPathNormalizer instance (from unify_utils)
            accept_dot: If True, fallback to "." separator when normalizer fails
        
        Returns:
            Self for chaining
        
        Examples:
            >>> # 기본 구분자 "."
            >>> kpd = KeyPathDict({"a": {"b": 1}})
            >>> kpd.apply_overrides({"a.b": 2})
            >>> kpd.data
            {'a': {'b': 2}}
            
            >>> # 커스텀 구분자 "__" (normalizer 사용)
            >>> from unify_utils.normalizers.normalizer_keypath import KeyPathNormalizer
            >>> from unify_utils.core.policy import KeyPathNormalizePolicy
            >>> norm = KeyPathNormalizer(KeyPathNormalizePolicy(sep="__"))
            >>> kpd.apply_overrides({"a__b": 3}, normalizer=norm)
            
            >>> # 리터럴 키 (리스트/튜플 경로 권장)
            >>> kpd.apply_overrides({("a.b", "c"): 1})  # a.b → c
        """
        # normalizer가 없으면 기본 "." 구분자로 간단 처리
        if normalizer is None:
            # 기본 동작: "." 구분자 기반 split
            for key, value in overrides.items():
                if isinstance(key, (list, tuple)):
                    # 리스트/튜플 경로는 리터럴 처리
                    KeyPathAccessor(self.data).set([str(k) for k in key], value)
                else:
                    key_str = str(key)
                    if "." in key_str:
                        # "." 기반 split
                        parts = [p for p in key_str.split(".") if p]
                        if parts:
                            KeyPathAccessor(self.data).set(parts, value)
                        else:
                            self.data[key_str] = value
                    else:
                        # 구분자 없음 → 리터럴 키
                        self.data[key_str] = value
            return self
        
        # normalizer 사용 (SRP 준수: 해석 책임 위임)
        acc = KeyPathAccessor(self.data)
        
        for key, value in overrides.items():
            # 1) 리스트/튜플 경로는 리터럴로 처리 (권장)
            if isinstance(key, (list, tuple)):
                acc.set([str(k) for k in key], value)
                continue
            
            # 2) 문자열 키는 normalizer로 해석
            key_str = str(key)
            parts = normalizer.apply(key_str)
            
            # 3) normalizer가 빈 결과 반환 && accept_dot이면 "." fallback
            if not parts and accept_dot and "." in key_str:
                parts = [p for p in key_str.split(".") if p]
            
            if parts:
                acc.set(parts, value)
            else:
                # 4) 파싱 실패 시 리터럴 키로 설정
                self.data[key_str] = value
        
        return self

    def rekey(self, mapping_or_func: Any, *, deep: bool = True) -> KeyPathDict:
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
