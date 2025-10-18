# -*- coding: utf-8 -*-
# unify_utils/resolver/vars.py
# description: 변수 치환 Resolver (환경변수, Context, 단순 참조)

from __future__ import annotations
import os
import re
from typing import Any, Set
from unify_utils.core.interface import Resolver
from unify_utils.core.policy import VarsResolverPolicy


class VarsResolver(Resolver):
    """정책 기반 변수 치환 Resolver (공통 모듈)
    
    ✅ 공통 기능:
    - 환경 변수: ${ENV:default}
    - Context 변수: {{VAR}}
    - 단순 참조: ${key:default}
    
    ⚠️ 프로젝트 특정 기능 미포함:
    - KeyPath 중첩 경로 (a__b__c) → keypath_utils.KeyPathVarsResolver 사용
    
    지원 패턴:
    1. ${key:default} - 단순 dict 키 참조
    2. ${ENV:default} - 환경 변수 (enable_env=True)
    3. {{VAR}} - Context 변수 (enable_context=True)
    
    Examples:
        >>> # Case 1: 단순 참조
        >>> data = {"host": "api.com", "url": "${host}:443"}
        >>> policy = VarsResolverPolicy()
        >>> resolver = VarsResolver(data, policy)
        >>> resolver.apply(data)
        {'host': 'api.com', 'url': 'api.com:443'}
        
        >>> # Case 2: 환경 변수 + Context
        >>> data = {"url": "http://{{HOST}}:${PORT:8000}"}
        >>> policy = VarsResolverPolicy(
        ...     enable_env=True,
        ...     enable_context=True,
        ...     context={"HOST": "localhost"}
        ... )
        >>> resolver = VarsResolver(data, policy)
        >>> resolver.apply(data)
        {'url': 'http://localhost:8000'}
        
        >>> # ⚠️ 중첩 경로는 미지원
        >>> data = {"db": {"host": "localhost"}, "url": "${db__host}"}
        >>> resolver = VarsResolver(data, VarsResolverPolicy())
        >>> resolver.apply(data)
        {'db': {'host': 'localhost'}, 'url': '${db__host}'}  # 해석 안됨
    
    Note:
        중첩 경로 필요 시 keypath_utils.KeyPathVarsResolver 사용
    """
    
    # 패턴 상수
    ENV_PATTERN = re.compile(r"\$\{([^}^{]+)\}")
    VAR_PATTERN = re.compile(r"\{\{([^{}]+)\}\}")
    REF_PATTERN = re.compile(r"\$\{([a-zA-Z0-9_]+)(?::([^}]*))?\}")  # 단순 키만
    
    def __init__(self, data: dict, policy: VarsResolverPolicy):
        """
        Args:
            data: 참조 소스 데이터
            policy: VarsResolverPolicy 정책
        """
        super().__init__(recursive=policy.recursive, strict=policy.strict)
        self.data = data
        self.policy = policy
        self._resolving: Set[str] = set()  # 순환 참조 감지
    
    # ------------------------------------------------------------------
    # Core Resolution (Abstract 구현)
    # ------------------------------------------------------------------
    def _apply_single(self, value: Any) -> Any:
        """단일 값에 대한 해석 (Abstract 인터페이스 구현)"""
        
        if not isinstance(value, str):
            return value
        
        text = value
        
        # 순서: env → context → reference
        if self.policy.enable_env:
            text = self._resolve_env(text)
        
        if self.policy.enable_context:
            text = self._resolve_context(text)
        
        # 내부 참조 해석
        text = self._resolve_reference(text)
        
        return text
    
    # ------------------------------------------------------------------
    # 1. 환경 변수 해석: ${ENV:default}
    # ------------------------------------------------------------------
    def _resolve_env(self, text: str) -> str:
        """환경 변수 치환"""
        def replacer(match: re.Match) -> str:
            expr = match.group(1)
            if ":" in expr:
                var, default = expr.split(":", 1)
            else:
                var, default = expr, ""
            return os.getenv(var, default)
        return self.ENV_PATTERN.sub(replacer, text)
    
    # ------------------------------------------------------------------
    # 2. Context 변수 해석: {{VAR}}
    # ------------------------------------------------------------------
    def _resolve_context(self, text: str) -> str:
        """Context 변수 치환"""
        def replacer(match: re.Match) -> str:
            key = match.group(1).strip()
            if key in self.policy.context:
                return str(self.policy.context[key])
            if self.strict:
                raise KeyError(f"[VarsResolver] Missing context key: {key}")
            return match.group(0)  # 원본 유지
        return self.VAR_PATTERN.sub(replacer, text)
    
    # ------------------------------------------------------------------
    # 3. 내부 참조 해석: ${key:default}
    # ------------------------------------------------------------------
    def _resolve_reference(self, text: str) -> str:
        """내부 참조 치환 (단순 키만)"""
        def replacer(match: re.Match) -> str:
            key = match.group(1)
            default = match.group(2) or ""
            
            # 순환 참조 감지
            if key in self._resolving:
                if self.strict:
                    raise ValueError(f"[VarsResolver] Circular reference: {key}")
                return default
            
            try:
                self._resolving.add(key)
                resolved = self._resolve_key(key)
                
                if resolved is None:
                    return default if default else ""
                
                return str(resolved)
            except KeyError:
                if self.strict:
                    raise KeyError(f"[VarsResolver] Missing key: {key}")
                return default
            finally:
                self._resolving.discard(key)
        
        return self.REF_PATTERN.sub(replacer, text)
    
    def _resolve_key(self, key: str) -> Any:
        """키 기반 값 탐색 (단순 키만, 중첩 불가)"""
        if key not in self.data:
            raise KeyError(f"[VarsResolver] Invalid key: {key}")
        
        resolved = self.data[key]
        
        # 재귀 치환
        if isinstance(resolved, str) and self.REF_PATTERN.search(resolved):
            return self._resolve_reference(resolved)
        
        return resolved