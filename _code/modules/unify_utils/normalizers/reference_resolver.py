# -*- coding: utf-8 -*-
# unify_utils/normalizers/reference_resolver.py
# description: unify_utils.normalizers — 내부 참조(${key.path:default}) 문자열 치환기
from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from ..core.base import NormalizerBase
from ..core.policy import KeyPathNormalizePolicy
from .keypath_normalizer import KeyPathNormalizer


class ReferenceResolver(NormalizerBase):
    """문자열 내 ${key.path[:default]} 참조를 해석하여 값으로 치환하는 정규화기

    특징
    ------
    - dict/list 구조 전체 재귀 순회
    - `${key}` 또는 `${key:default}` 구문 지원
    - KeyPath (a.b.c) 스타일 내부 참조 지원
    - NormalizerBase 상속 구조로 strict/recursive/compose 지원
    """

    PATTERN = re.compile(r"\$\{([a-zA-Z0-9_.]+)(?::([^}]*))?\}")

    def __init__(self, data: dict, *, keypath_policy: KeyPathNormalizePolicy | None = None, **kwargs):
        super().__init__(**kwargs)
        self.data = data
        self.keypath_normalizer = KeyPathNormalizer(keypath_policy or KeyPathNormalizePolicy()) # pyright: ignore[reportCallIssue]

    # ------------------------------------------------------------------
    # Core
    # ------------------------------------------------------------------
    def _apply_single(self, value: Any) -> Any:
        if isinstance(value, str):
            return self._resolve_placeholders(value)
        return value

    def _resolve_placeholders(self, value: str) -> str:
        def replacer(match: re.Match) -> str:
            keypath, default = match.group(1), match.group(2) or ""
            try:
                return str(self._resolve_keypath(keypath))
            except KeyError:
                if self.strict:
                    raise KeyError(f"Missing keypath: {keypath}")
                return default

        return self.PATTERN.sub(replacer, value)
    
    def _resolve_keypath(self, path: str | list[str]) -> Any:
        keys = self.keypath_normalizer.apply(path)
        ref = self.data
        for key in keys:
            if isinstance(ref, dict) and key in ref:
                ref = ref[key]
            else:
                if self.strict:
                    raise KeyError(f"Invalid keypath: {'.'.join(keys)}")
                return None
        return ref
