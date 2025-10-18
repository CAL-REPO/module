# -*- coding: utf-8 -*-
# keypath_utils/services/resolver.py
# description: KeyPath 기반 중첩 경로 변수 해석 Resolver

from __future__ import annotations
import re
from typing import Any
from unify_utils.resolver.vars import VarsResolver
from modules.keypath_utils.core.policy import KeyPathResolverPolicy
from modules.keypath_utils.core.accessor import KeyPathAccessor


class KeyPathVarsResolver(VarsResolver):
    """KeyPath 기반 중첩 경로 변수 해석 Resolver (프로젝트 특정)
    
    ✅ VarsResolver 확장:
    - 공통 기능: 환경변수, Context, 단순 참조 (상속)
    - 추가 기능: KeyPath 중첩 경로 (a__b__c)
    
    특징:
    - KeyPathAccessor를 사용한 중첩 경로 탐색
    - `${key__path:default}` 구문 지원
    - 구분자: `__` (프로젝트 표준)
    
    지원 패턴:
    1. ${key__path:default} - KeyPath 중첩 참조
    2. ${ENV:default} - 환경 변수 (enable_env=True)
    3. {{VAR}} - Context 변수 (enable_context=True)
    
    Examples:
        >>> # Case 1: KeyPath 중첩 참조
        >>> data = {"db": {"host": "localhost"}, "url": "${db__host}:5432"}
        >>> policy = KeyPathResolverPolicy()
        >>> resolver = KeyPathVarsResolver(data, policy)
        >>> resolver.apply(data)
        {'db': {'host': 'localhost'}, 'url': 'localhost:5432'}
        
        >>> # Case 2: 환경 변수 + Context + KeyPath
        >>> data = {
        ...     "db": {"host": "prod-db"},
        ...     "url": "http://{{HOST}}:${PORT:5432}/${db__host}"
        ... }
        >>> policy = KeyPathResolverPolicy(
        ...     enable_env=True,
        ...     enable_context=True,
        ...     context={"HOST": "api.com"}
        ... )
        >>> resolver = KeyPathVarsResolver(data, policy)
        >>> resolver.apply(data)
        {'db': {'host': 'prod-db'}, 'url': 'http://api.com:5432/prod-db'}
        
        >>> # Case 3: 재귀 참조
        >>> data = {
        ...     "config": {"base": "https://api.com"},
        ...     "path": "${config__base}/v1",
        ...     "url": "${path}/users"
        ... }
        >>> resolver = KeyPathVarsResolver(data, KeyPathResolverPolicy())
        >>> result = resolver.apply(data)
        >>> result["url"]
        'https://api.com/v1/users'
    
    Note:
        - 공통 기능만 필요하면 unify_utils.VarsResolver 사용
        - 중첩 경로가 필요하면 KeyPathVarsResolver 사용
    """

    # KeyPath 패턴: ${key__path:default}
    # __ 구분자를 포함한 KeyPath 패턴 (a-zA-Z0-9_)
    KEYPATH_PATTERN = re.compile(r"\$\{([a-zA-Z0-9_]+(?:__[a-zA-Z0-9_]+)*)(?::([^}]*))?\}")

    def __init__(
        self,
        data: dict,
        policy: KeyPathResolverPolicy,
    ):
        """
        Args:
            data: 참조 소스 데이터
            policy: KeyPathResolverPolicy 정책
        """
        super().__init__(data, policy)
        # KeyPathAccessor 추가 (기본 구분자 "__" 사용)
        self.accessor = KeyPathAccessor(data)
        # 정책 타입 명시
        self.policy: KeyPathResolverPolicy = policy

    # ------------------------------------------------------------------
    # Override: KeyPath 패턴으로 교체
    # ------------------------------------------------------------------
    def _resolve_reference(self, text: str) -> str:
        """내부 참조 치환 (KeyPath 중첩 경로 지원)
        
        ✅ 상위 클래스의 _resolve_reference를 Override하여 KeyPath 지원 추가.
        """
        def replacer(match: re.Match) -> str:
            key = match.group(1)
            default = match.group(2) or ""
            
            # 순환 참조 감지
            if key in self._resolving:
                if self.strict:
                    raise ValueError(f"[KeyPathVarsResolver] Circular reference: {key}")
                return default
            
            try:
                self._resolving.add(key)
                resolved = self._resolve_key(key)
                
                if resolved is None:
                    return default if default else ""
                
                return str(resolved)
            except KeyError:
                if self.strict:
                    raise KeyError(f"[KeyPathVarsResolver] Missing keypath: {key}")
                return default
            finally:
                self._resolving.discard(key)
        
        return self.KEYPATH_PATTERN.sub(replacer, text)

    def _resolve_key(self, key: str) -> Any:
        """KeyPath 기반 값 탐색 (중첩 경로 지원)
        
        ✅ 상위 클래스의 _resolve_key를 Override하여 KeyPath Accessor 사용.
        
        Args:
            key: KeyPath 문자열 (예: "db__host" 또는 "simple_key")
        
        Returns:
            참조된 값
        
        Raises:
            KeyError: 경로가 존재하지 않는 경우
        
        Examples:
            >>> data = {"db": {"host": "localhost"}}
            >>> resolver = KeyPathVarsResolver(data, KeyPathResolverPolicy())
            >>> resolver._resolve_key("db__host")
            'localhost'
            
            >>> # 단순 키도 지원
            >>> data = {"simple": "value"}
            >>> resolver._resolve_key("simple")
            'value'
        """
        # KeyPathAccessor.get() 사용 (sentinel 패턴)
        sentinel = object()
        resolved = self.accessor.get(key, sentinel)
        
        if resolved is sentinel:
            # 경로가 존재하지 않음
            raise KeyError(f"[KeyPathVarsResolver] Invalid keypath: {key!r}")
        
        # 재귀 치환: 참조된 값이 또 다른 ${} 패턴 포함 시
        if isinstance(resolved, str) and self.KEYPATH_PATTERN.search(resolved):
            return self._resolve_reference(resolved)
        
        return resolved
