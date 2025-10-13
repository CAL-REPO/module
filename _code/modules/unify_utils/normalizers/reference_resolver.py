# -*- coding: utf-8 -*-
# unify_utils/normalizers/reference_resolver.py
# description: unify_utils.normalizers — 내부 참조(${key.path[:default]}) 해석 Resolver

from __future__ import annotations
import re
from typing import Any
from unify_utils.core.resolver_base import ResolverBase
from unify_utils.core.base import KeyPathNormalizePolicy
from unify_utils.normalizers.keypath_normalizer import KeyPathNormalizer


class ReferenceResolver(ResolverBase):
    """데이터 내부 참조를 해석하는 Resolver.
    
    특징:
    - dict/list 구조 전체 재귀 순회
    - `${key.path}` 또는 `${key.path:default}` 구문 지원
    - KeyPath 스타일 내부 참조 (예: a.b.c)
    - strict 모드 및 recursive 적용
    """

    PATTERN = re.compile(r"\$\{([a-zA-Z0-9_.]+)(?::([^}]*))?\}")

    def __init__(
        self,
        data: dict,
        *,
        keypath_policy: KeyPathNormalizePolicy | None = None,
        recursive: bool = True,
        strict: bool = False,
    ):
        super().__init__(recursive=recursive, strict=strict)
        self.data = data
        self.keypath_normalizer = KeyPathNormalizer(keypath_policy or KeyPathNormalizePolicy()) # pyright: ignore[reportCallIssue]

    # ------------------------------------------------------------------
    # Core Resolution
    # ------------------------------------------------------------------
    def _resolve_single(self, value: Any) -> Any:
        if isinstance(value, str):
            return self._resolve_placeholders(value)
        return value

    # ------------------------------------------------------------------
    # 문자열 내 ${a.b[:default]} 패턴 해석
    # ------------------------------------------------------------------
    def _resolve_placeholders(self, value: str) -> str:
        def replacer(match: re.Match) -> str:
            keypath, default = match.group(1), match.group(2) or ""
            try:
                resolved = self._resolve_keypath(keypath)
                return str(resolved)
            except KeyError:
                if self.strict:
                    raise KeyError(f"[ReferenceResolver] Missing keypath: {keypath}")
                return default
        return self.PATTERN.sub(replacer, value)

    # ------------------------------------------------------------------
    # KeyPath 기반 탐색 로직
    # ------------------------------------------------------------------
    def _resolve_keypath(self, path: str | list[str]) -> Any:
        keys = self.keypath_normalizer.apply(path)
        ref = self.data
        for key in keys:
            if isinstance(ref, dict) and key in ref:
                ref = ref[key]
            else:
                if self.strict:
                    raise KeyError(f"[ReferenceResolver] Invalid keypath: {'.'.join(keys)}")
                return None
        return ref
