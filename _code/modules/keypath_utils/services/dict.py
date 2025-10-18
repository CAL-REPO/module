# -*- coding: utf-8 -*-
# keypath_utils/services/dict.py
# KeyPathDict 클래스 정의 - dict 기반 데이터 모델 with KeyPath 접근

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Dict
from data_utils.core.types import KeyPath
from modules.keypath_utils.core.accessor import KeyPathAccessor
from data_utils.services.dict_ops import DictOps
from modules.keypath_utils.services.merger import KeyPathMerger, KeyPathMergePolicy


@dataclass
class KeyPathDict:
    """KeyPath 기반 dict 접근 데이터 모델.
    
    dict 데이터를 래핑하여 KeyPath 기반 접근 및 조작을 제공합니다.
    - override: KeyPath 기반 값 덮어쓰기
    - merge: Deep/shallow merge (KeyPathMerger 사용)
    - apply_overrides: 일괄 오버라이드 적용
    - resolve_all: 참조 해석 (Placeholder + Reference)
    - drop_blanks: blank 값 제거 (BlankType 정책)
    - rekey: 키 이름 변경
    
    Examples:
        >>> from keypath_utils.services import KeyPathDict
        >>> model = KeyPathDict({"a": {"b": 1}})
        >>> model.override("a__b", 2)
        >>> model.data
        {'a': {'b': 2}}
        
        >>> # 참조 해석
        >>> model = KeyPathDict({"host": "api.com", "url": "${host}:443"})
        >>> model.resolve_all()
        >>> model.data
        {'host': 'api.com', 'url': 'api.com:443'}
    """
    
    data: Dict[str, Any] = field(default_factory=dict)
    # Separator for keypath segments (default "__" per project standard)
    key_separator: str = field(default='__')
    # Merger instance (정책 기반 merge)
    _merger: Optional[KeyPathMerger] = field(default=None, init=False, repr=False)
    
    def __post_init__(self):
        """Initialize merger with default policy."""
        if self._merger is None:
            self._merger = KeyPathMerger()

    def override(self, path: KeyPath, value: Any) -> KeyPathDict:
        """KeyPath 경로에 값 덮어쓰기.
        
        Args:
            path: 설정할 경로
            value: 설정할 값
            
        Returns:
            Self for chaining
            
        Examples:
            >>> model = KeyPathDict()
            >>> model.override("a__b__c", 123)
            >>> model.data
            {'a': {'b': {'c': 123}}}
        """
        KeyPathAccessor(self.data).set(path, value)
        return self

    def merge(
        self, 
        patch: Mapping[str, Any], 
        *, 
        deep: bool = True, 
        inplace: bool = True,
        policy: Optional[KeyPathMergePolicy] = None
    ) -> KeyPathDict:
        """Dict 병합 (KeyPathMerger 사용).
        
        Args:
            patch: 병합할 dict
            deep: Deep merge 여부 (True면 재귀 병합, False면 shallow update)
            inplace: 원본 수정 여부
            policy: 일회성 정책 오버라이드 (KeyPathMergePolicy 인스턴스)
        
        Returns:
            Self for chaining
            
        Examples:
            >>> model = KeyPathDict({"a": {"b": 1, "c": 2}})
            >>> model.merge({"a": {"b": 99}}, deep=True)
            >>> model.data
            {'a': {'b': 99, 'c': 2}}
            
            >>> model.merge({"a": {"d": 3}}, deep=False)
            >>> model.data
            {'a': {'d': 3}}  # 'a' 전체가 교체됨
            
            >>> # 커스텀 정책 사용
            >>> custom_policy = KeyPathMergePolicy(deep=True, inplace=False)
            >>> result = model.merge({"new": "data"}, policy=custom_policy)
            >>> # 원본 유지, 복사본 반환
        """
        # 정책 우선순위: policy 파라미터 > deep/inplace 파라미터
        if policy is None:
            policy = KeyPathMergePolicy(deep=deep, inplace=inplace)
        
        self.data = self._merger.merge(self.data, dict(patch), policy=policy)
        return self

    def apply_overrides(
        self,
        overrides: Dict[str, Any],
        *,
        normalizer: Optional[Any] = None,
        accept_dot: bool = True
    ) -> KeyPathDict:
        """오버라이드 일괄 적용.
        
        오버라이드 해석 책임을 normalizer로 위임하여 SRP 준수:
        - normalizer: KeyPath 문자열 해석기 (없으면 기본 "__" 구분자 사용)
        - accept_dot: normalizer 실패 시 "." 구분자로 fallback 허용
        
        Args:
            overrides: Dict of key-value pairs to apply
            normalizer: Optional KeyPathNormalizer instance (from keypath_utils)
            accept_dot: If True, fallback to "." separator when normalizer fails
        
        Returns:
            Self for chaining
        
        Examples:
            >>> # 기본 구분자 "__"
            >>> model = KeyPathDict({"a": {"b": 1}})
            >>> model.apply_overrides({"a__b": 2})
            >>> model.data
            {'a': {'b': 2}}
            
            >>> # 커스텀 구분자 (normalizer 사용)
            >>> from keypath_utils.services import KeyPathNormalizer
            >>> from keypath_utils.core import KeyPathResolverPolicy
            >>> norm = KeyPathNormalizer(KeyPathResolverPolicy(keypath_sep="__"))
            >>> model.apply_overrides({"a__b": 3}, normalizer=norm)
            
            >>> # 리터럴 키 (리스트/튜플 경로 권장)
            >>> model.apply_overrides({("a__b", "c"): 1})  # literal key "a__b" → c
        """
        # normalizer가 없으면 기본 "__" 구분자로 처리
        if normalizer is None:
            # 기본 동작: "__" 구분자 기반 split (프로젝트 표준)
            for key, value in overrides.items():
                if isinstance(key, (list, tuple)):
                    # 리스트/튜플 경로는 리터럴 처리
                    KeyPathAccessor(self.data).set([str(k) for k in key], value)
                else:
                    key_str = str(key)
                    if "__" in key_str:
                        # "__" 기반 split
                        parts = [p for p in key_str.split("__") if p]
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
        """키 이름 변경.
        
        Args:
            mapping_or_func: Dict mapping 또는 변환 함수
            deep: 재귀적으로 중첩 구조 처리
            
        Returns:
            Self for chaining
            
        Examples:
            >>> model = KeyPathDict({"old_key": 1})
            >>> model.rekey({"old_key": "new_key"})
            >>> model.data
            {'new_key': 1}
        """
        updated = DictOps.rekey(self.data, mapping_or_func, deep=deep)
        self.data.clear()
        self.data.update(updated)
        return self
    
    def resolve_all(
        self,
        *,
        context: Optional[Dict[str, Any]] = None,
        recursive: bool = True,
        strict: bool = False
    ) -> KeyPathDict:
        """데이터 내 모든 KeyPath 참조를 완전히 해석.
        
        KeyPathVarsResolver를 사용하여 내부 KeyPath 참조를 치환합니다.
        (${key__path:default} 패턴)
        
        Args:
            context: 해석에 사용할 컨텍스트 dict (사용 안 함, 향후 확장용)
            recursive: 재귀적으로 중첩 구조 처리
            strict: 해석 실패 시 예외 발생 여부
        
        Returns:
            Self for chaining
        
        Examples:
            >>> # KeyPath 참조
            >>> model = KeyPathDict({
            ...     "image": {"max_width": 1024},
            ...     "ref": "${image__max_width}"
            ... })
            >>> model.resolve_all()
            >>> model.data
            {'image': {'max_width': 1024}, 'ref': '1024'}
            
            >>> # 재귀 참조
            >>> model = KeyPathDict({
            ...     "config": {"base": "https://api.com"},
            ...     "path": "${config__base}/v1",
            ...     "url": "${path}/users"
            ... })
            >>> model.resolve_all()
            >>> model.data['url']
            'https://api.com/v1/users'
            
            >>> # 순환 참조 감지
            >>> model = KeyPathDict({"a": "${b}", "b": "${a}"})
            >>> model.resolve_all(strict=True)  # ValueError: Circular reference
        """
        from modules.keypath_utils.services.resolver import KeyPathVarsResolver
        from modules.keypath_utils.core.policy import KeyPathResolverPolicy
        
        policy = KeyPathResolverPolicy(
            enable_env=False,  # 환경 변수 비활성화
            enable_context=False,  # 컨텍스트 비활성화
            keypath_sep="__",  # 프로젝트 표준
            recursive=recursive,
            strict=strict
        )
        resolver = KeyPathVarsResolver(data=self.data, policy=policy)
        self.data = resolver.apply(self.data)
        
        return self
    
    def drop_blanks(
        self,
        *,
        types: Optional[Any] = None,
        deep: bool = True
    ) -> KeyPathDict:
        """Blank 값 제거 (BlankType 정책).
        
        Args:
            types: 제거할 blank 타입 (BlankType Flag, 기본값: STANDARD)
            deep: 재귀적으로 중첩 구조 처리
        
        Returns:
            Self for chaining
        
        Examples:
            >>> from data_utils import BlankType
            >>> model = KeyPathDict({"a": None, "b": "", "c": "ok"})
            >>> model.drop_blanks()  # STANDARD (None + 빈 문자열)
            >>> model.data
            {'c': 'ok'}
            
            >>> # None만 제거
            >>> model = KeyPathDict({"a": None, "b": "", "c": "ok"})
            >>> model.drop_blanks(types=BlankType.NONE)
            >>> model.data
            {'b': '', 'c': 'ok'}
            
            >>> # 모든 blank 제거
            >>> model = KeyPathDict({"a": None, "b": [], "c": {}, "d": "ok"})
            >>> model.drop_blanks(types=BlankType.ALL)
            >>> model.data
            {'d': 'ok'}
        """
        from data_utils.core.types import BlankType
        
        if types is None:
            types = BlankType.STANDARD
        
        self.data = DictOps.process_blanks(
            self.data,
            types=types,
            action="drop",
            deep=deep
        )
        return self
    
    def has_unresolved_placeholders(self) -> bool:
        """아직 해석되지 않은 플레이스홀더가 있는지 확인.
        
        패턴:
        - ${VAR} 또는 ${VAR:default} (ReferenceResolver 또는 PlaceholderResolver)
        - {{VAR}} (PlaceholderResolver)
        
        Returns:
            True if unresolved placeholders exist
        
        Examples:
            >>> model = KeyPathModel({"url": "${host}:443"})
            >>> model.has_unresolved_placeholders()
            True
            >>> model.resolve_all()
            >>> model.has_unresolved_placeholders()
            False  # 해석 완료 (또는 기본값으로 대체)
        """
        import re
        # ${...} 패턴 (ReferenceResolver 또는 PlaceholderResolver)
        pattern_dollar = re.compile(r"\$\{[^}]+\}")
        # {{...}} 패턴 (PlaceholderResolver)
        pattern_brace = re.compile(r"\{\{[^}]+\}\}")
        
        def check_value(value: Any) -> bool:
            """값에 미해석 패턴이 있는지 확인 (재귀)."""
            if isinstance(value, str):
                return bool(pattern_dollar.search(value) or pattern_brace.search(value))
            elif isinstance(value, dict):
                return any(check_value(v) for v in value.values())
            elif isinstance(value, list):
                return any(check_value(item) for item in value)
            return False
        
        return check_value(self.data)
