# -*- coding: utf-8 -*-
# unify_utils/core/base.py

# description: unify_utils.core — 공통 NormalizerBase 추상 클래스 (재귀 처리/스트릭트 모드/체이닝 지원)
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Mapping, MutableMapping, cast


class NormalizerBase(ABC):
    """정규화기들의 공통 기반 클래스.

    특징
    -------
    - **recursive**: dict/list/tuple 내부 구조를 재귀적으로 순회하며 정규화 수행
    - **strict**: 하위 클래스에서 오류 발생 시 예외 전파를 선택적으로 허용
    - **compose()**: 여러 Normalizer를 순서대로 결합한 합성 정규화기 반환
    - **__call__** 별칭 제공 (함수 형태로도 사용 가능)

    하위 클래스 구현 지침
    ---------------------
    - `_apply_single(value)` 를 구현해 한 번의 단일 값 정규화를 정의합니다.
      Base는 이 함수를 이용해 재귀 순회와 체이닝을 제공합니다.
    - `_apply_single` 는 **비-컨테이너 타입**(str, int, float, None 등)에만 집중하고,
      컨테이너 타입(dict/list/tuple) 처리는 Base에 맡깁니다.
    """

    def __init__(self, *, recursive: bool = False, strict: bool = False):
        self.recursive = bool(recursive)
        self.strict = bool(strict)

    # -----------------------------
    # Public API
    # -----------------------------
    def apply(self, value: Any) -> Any:
        """값을 정규화하여 반환합니다.

        하위 클래스에서 `_apply_single`만 구현하면 되며,
        Base가 컨테이너 순회 및 예외 처리, 재귀 적용을 담당합니다.
        """
        try:
            if self.recursive:
                return self._recursive_apply(value, self._apply_single)
            return self._apply_single(value)
        except Exception:
            if self.strict:
                raise
            return value

    # 함수처럼 호출 가능하도록 별칭 제공
    __call__ = apply

    def compose(self, *others: "NormalizerBase") -> "NormalizerBase":
        """여러 Normalizer를 순서대로 적용하는 합성 정규화기 생성.

        예시
        ----
        >>> normalizer = n1.compose(n2, n3)
        >>> out = normalizer.apply(value)  # n1 -> n2 -> n3 순서로 적용
        """
        parent = self

        class _Composed(NormalizerBase):
            def __init__(self):
                # 합성기 자체의 설정은 가장 앞선 parent를 따른다.
                super().__init__(recursive=parent.recursive, strict=parent.strict)

            def _apply_single(self, v: Any) -> Any:
                # parent → others 순차 적용. parent/others 각각이 재귀 설정을 갖고 있으므로
                # 개별 정규화기의 apply를 호출하여 일관된 동작을 유지한다.
                result = parent.apply(v)
                for n in others:
                    result = n.apply(result)
                return result

        return _Composed()

    # -----------------------------
    # Hooks for subclasses
    # -----------------------------
    @abstractmethod
    def _apply_single(self, value: Any) -> Any:
        """비-컨테이너 단일 값에 대한 정규화 로직을 구현합니다.

        컨테이너(dict/list/tuple) 에 대한 처리는 Base가 담당합니다.
        구현체는 예외를 던져도 되며(strict=True에서 상위에서 전파),
        strict=False인 경우 Base가 원본 값을 반환합니다.
        """
        raise NotImplementedError

    # -----------------------------
    # Internal helpers
    # -----------------------------
    def _recursive_apply(self, value: Any, fn: Callable[[Any], Any]) -> Any:
        """컨테이너 타입에 대해 재귀적으로 정규화를 적용합니다.

        - dict: values에만 적용(키는 유지). 키 정규화가 필요하면 별도 Normalizer에서 처리 권장.
        - list/tuple: 동일 타입을 유지하여 반환(list는 list, tuple은 tuple)
        - 그 외: 단일 값 처리
        """
        # dict
        if isinstance(value, Mapping):
            out = cast(MutableMapping[Any, Any], type(value)())  # 원래의 dict subclass 유지 시도
            for k, v in value.items():
                out[k] = self._recursive_apply(v, fn)
            return out

        # list / tuple
        if isinstance(value, (list, tuple)):
            seq = [self._recursive_apply(v, fn) for v in value]
            return type(value)(seq) if isinstance(value, tuple) else seq

        # leaf
        return fn(value)
