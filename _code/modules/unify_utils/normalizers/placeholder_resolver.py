# -*- coding: utf-8 -*-
# unify_utils/normalizers/placeholder_resolver.py
# description: 문자열 내 환경 변수(${VAR:default}) 및 {{VAR}} 치환 Resolver

from __future__ import annotations
import os
import re
from typing import Any, Mapping
from unify_utils.core.resolver_base import ResolverBase


class PlaceholderResolver(ResolverBase):
    """
    ✅ PlaceholderResolver
    - ${ENV:default} 형식 → OS 환경 변수 기반 치환
    - {{VAR}} 형식 → 사용자 context 기반 치환

    예시:
        >>> resolver = PlaceholderResolver(context={"HOST": "localhost"})
        >>> resolver.apply("http://{{HOST}}:${PORT:8000}")
        'http://localhost:8000'
    """

    ENV_PATTERN = re.compile(r"\$\{([^}^{]+)\}")
    VAR_PATTERN = re.compile(r"\{\{([^{}]+)\}\}")

    def __init__(
        self,
        context: Mapping[str, Any] | None = None,
        *,
        recursive: bool = True,
        strict: bool = False,
    ):
        super().__init__(recursive=recursive, strict=strict)
        self.context = dict(context or {})

    # ------------------------------------------------------------------
    # Core Resolution
    # ------------------------------------------------------------------
    def _resolve_single(self, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        text = self._resolve_env(value)
        text = self._resolve_context(text)
        return text

    # ------------------------------------------------------------------
    # ${VAR[:default]} → 환경 변수 치환
    # ------------------------------------------------------------------
    @classmethod
    def _resolve_env(cls, text: str) -> str:
        def replacer(match: re.Match) -> str:
            expr = match.group(1)
            if ":" in expr:
                var, default = expr.split(":", 1)
            else:
                var, default = expr, ""
            return os.getenv(var, default)
        return cls.ENV_PATTERN.sub(replacer, text)

    # ------------------------------------------------------------------
    # {{VAR}} → context dict 치환
    # ------------------------------------------------------------------
    def _resolve_context(self, text: str) -> str:
        def replacer(match: re.Match) -> str:
            key = match.group(1).strip()
            if key in self.context:
                return str(self.context[key])
            if self.strict:
                raise KeyError(f"[PlaceholderResolver] Missing key: {key}")
            return match.group(0)
        return self.VAR_PATTERN.sub(replacer, text)
