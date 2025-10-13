# -*- coding: utf-8 -*-
# unify_utils/core/resolver_base.py
# description: Resolver 계열 공통 추상 클래스 (Placeholder, Reference 등)

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Callable, Mapping, MutableMapping, cast


class ResolverBase(ABC):
    """데이터 구조 내 참조(Reference, Placeholder 등)를 해석하기 위한 추상 기반 클래스.

    특징:
    - recursive: dict/list/tuple 구조를 재귀적으로 탐색
    - strict: 해석 실패 시 예외 전파 여부 제어
    - apply() 메서드를 통해 전체 데이터 구조 해석 수행
    """

    def __init__(self, *, recursive: bool = True, strict: bool = False):
        self.recursive = recursive
        self.strict = strict

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def apply(self, value: Any) -> Any:
        """입력 데이터 전체에 대해 해석 수행."""
        try:
            if self.recursive:
                return self._recursive_resolve(value, self._resolve_single)
            return self._resolve_single(value)
        except Exception:
            if self.strict:
                raise
            return value

    __call__ = apply

    # ------------------------------------------------------------------
    # Abstract Interface
    # ------------------------------------------------------------------
    @abstractmethod
    def _resolve_single(self, value: Any) -> Any:
        """단일 값(문자열 등)에 대한 실제 해석 로직 구현."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------
    def _recursive_resolve(self, value: Any, fn: Callable[[Any], Any]) -> Any:
        """컨테이너 타입에 대해 재귀적으로 해석을 적용."""
        # dict
        if isinstance(value, Mapping):
            out = cast(MutableMapping[Any, Any], type(value)())
            for k, v in value.items():
                out[k] = self._recursive_resolve(v, fn)
            return out

        # list / tuple
        if isinstance(value, (list, tuple)):
            seq = [self._recursive_resolve(v, fn) for v in value]
            return type(value)(seq)

        # leaf node
        return fn(value)
