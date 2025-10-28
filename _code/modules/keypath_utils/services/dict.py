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

    def merge_array(
        self,
        patch: Mapping[str, Any],
        key: str = "items",
        strategy: str = "update",
        inplace: bool = True
    ) -> KeyPathDict:
        """배열 요소 병합 (Array Element Merge)
        
        일반 merge()는 배열 전체를 교체하지만, 이 메서드는 배열의 각 요소를
        개별적으로 병합합니다. Runtime Override에서 배열 일부 필드만 수정할 때 유용합니다.
        
        Args:
            patch: 병합할 dict (배열 포함)
            key: 병합할 배열 필드명 (default: "items")
            strategy: 병합 전략
                - "update": 기존 요소 업데이트 + 새 요소 추가 (default)
                  * 인덱스가 존재하면 dict.update()로 병합
                  * 인덱스가 없으면 append
                - "append": 모든 요소 추가 (extend)
                - "replace": 전체 교체 (일반 merge와 동일)
            inplace: 원본 수정 여부
        
        Returns:
            Self for chaining
        
        Examples:
            >>> # Update strategy (default) - 부분 필드 수정
            >>> model = KeyPathDict({"items": [{"kind": "image", "dir": "/old"}]})
            >>> model.merge_array({"items": [{"dir": "/new"}]})
            >>> model.data
            {'items': [{'kind': 'image', 'dir': '/new'}]}
            
            >>> # Append strategy - 요소 추가
            >>> model = KeyPathDict({"items": [{"id": 1}]})
            >>> model.merge_array({"items": [{"id": 2}]}, strategy="append")
            >>> model.data
            {'items': [{'id': 1}, {'id': 2}]}
            
            >>> # Replace strategy - 전체 교체
            >>> model = KeyPathDict({"items": [{"id": 1}]})
            >>> model.merge_array({"items": [{"id": 2}]}, strategy="replace")
            >>> model.data
            {'items': [{'id': 2}]}
            
            >>> # Multiple fields in nested dict
            >>> model = KeyPathDict({
            ...     "items": [{"kind": "image", "dir": "/old", "fso_name": {"prefix": "OLD"}}]
            ... })
            >>> model.merge_array({"items": [{"dir": "/new"}]})
            >>> model.data
            {'items': [{'kind': 'image', 'dir': '/new', 'fso_name': {'prefix': 'OLD'}}]}
        
        Use Case (Runtime Override):
            >>> # sync_crawl.py에서 items[0]__dir_path override
            >>> nested_override = {"items": [{"dir_path": "/custom/path"}]}
            >>> merged_kp.merge_array(nested_override, key="items", strategy="update")
            >>> # items[0]의 dir_path만 수정, 나머지 필드(kind, source 등)는 유지
        """
        if key not in patch:
            return self
        
        patch_array = patch[key]
        if not isinstance(patch_array, list):
            return self
        
        # Ensure key exists in self.data
        if key not in self.data:
            self.data[key] = []
        
        if strategy == "update":
            # Update existing + append new
            for idx, patch_item in enumerate(patch_array):
                if idx < len(self.data[key]):
                    # Update existing element
                    if isinstance(self.data[key][idx], dict) and isinstance(patch_item, dict):
                        self.data[key][idx].update(patch_item)
                    else:
                        self.data[key][idx] = patch_item
                else:
                    # Append new element
                    self.data[key].append(patch_item)
        
        elif strategy == "append":
            # Append all elements
            self.data[key].extend(patch_array)
        
        elif strategy == "replace":
            # Replace entire array
            self.data[key] = patch_array.copy() if inplace else patch_array
        
        else:
            raise ValueError(f"Unknown merge_array strategy: {strategy}. Use 'update', 'append', or 'replace'.")
        
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
        - ${key__path:default}: KeyPath 중첩 참조
        - {{placeholder}}: Context 변수 (self.data 기반)
        - ${ENV:default}: 환경 변수
        
        Args:
            context: 해석에 사용할 컨텍스트 dict (None이면 self.data 사용)
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
            
            >>> # Placeholder 참조 (self-reference)
            >>> model = KeyPathDict({
            ...     "base_path": "/app",
            ...     "config_dir": "{{base_path}}/config"
            ... })
            >>> model.resolve_all()
            >>> model.data
            {'base_path': '/app', 'config_dir': '/app/config'}

            >>> # 재귀 참조
            >>> model = KeyPathDict({
            ...     "config": {"base": "https://api.com"},
            ...     "path": "${config__base}/v1",
            ...     "url": "${path}/users"
            ... })
            >>> model.resolve_all()
            >>> model.data['url']
            'https://api.com/v1/users'
        """
        from modules.keypath_utils.services.resolver import KeyPathVarsResolver
        from modules.keypath_utils.core.policy import KeyPathResolverPolicy
        
        # context가 None이면 self.data 사용 (self-reference 지원)
        if context is None:
            context = self.data
        
        policy = KeyPathResolverPolicy(
            enable_env=False,  # ❌ 환경 변수: ${} 패턴이 KeyPath와 겹침
            enable_context=True,  # ✅ Context 변수: {{placeholder}}
            context=context,  # self.data를 context로 사용
            keypath_sep="__",  # 프로젝트 표준
            recursive=recursive,
            strict=strict
        )
        
        # Multi-pass resolution (재귀 참조 해결)
        # Pass 1: 첫 번째 해석
        resolver = KeyPathVarsResolver(data=self.data, policy=policy)
        self.data = resolver.apply(self.data)
        
        # Pass 2: 두 번째 해석 (context 업데이트하여 재귀 참조 해결)
        policy.context = self.data  # 1차 resolve된 데이터를 context로 업데이트
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
    
    @staticmethod
    def to_nested_dict(
        keypath_dict: Mapping[str, Any],
        *,
        normalizer: Optional[Any] = None,
        accept_dot: bool = True,
    ) -> Dict[str, Any]:
        """Convert KeyPath-style flat dict to nested dict (with array index support).
        
        Transforms flat dict with KeyPath keys (e.g., "a__b__c") 
        into nested dict structure (e.g., {"a": {"b": {"c": value}}}).
        
        ✅ Array Index Support (v2.0):
        - items[0]__dir_path → {"items": [{"dir_path": ...}]}
        - items[0]__fso_name__prefix → {"items": [{"fso_name": {"prefix": ...}}]}
        - items__0__dir_path → {"items": {"0": {"dir_path": ...}}} (legacy, dict)
        
        This is a convenience method that internally uses apply_overrides().
        
        Args:
            keypath_dict: Flat dict with KeyPath-style keys ("a__b__c" or "items[0]__field").
                Example: {"a__b": 1, "items[0]__dir_path": "/test"}
            normalizer: Optional KeyPathNormalizer for custom separators.
            accept_dot: Allow "." fallback when normalizer is provided.
        
        Returns:
            Nested dict with hierarchical structure.
            Example: {"a": {"b": 1}, "items": [{"dir_path": "/test"}]}
        
        Examples:
            >>> # Basic usage
            >>> KeyPathDict.to_nested_dict({"a__b": 1, "x__y__z": 2})
            {'a': {'b': 1}, 'x': {'y': {'z': 2}}}
            
            >>> # Array index support (NEW!)
            >>> KeyPathDict.to_nested_dict({"items[0]__dir_path": "/test"})
            {'items': [{'dir_path': '/test'}]}
            
            >>> # Multiple array elements
            >>> KeyPathDict.to_nested_dict({
            ...     "items[0]__dir_path": "/test1",
            ...     "items[1]__dir_path": "/test2"
            ... })
            {'items': [{'dir_path': '/test1'}, {'dir_path': '/test2'}]}
            
            >>> # Nested array fields
            >>> KeyPathDict.to_nested_dict({"items[0]__fso_name__prefix": "CUSTOM"})
            {'items': [{'fso_name': {'prefix': 'CUSTOM'}}]}
            
            >>> # In ConfigLikeLoader
            >>> override_dict = KeyPathDict.to_nested_dict(overrides)
            >>> policy.model_copy(update=override_dict)
            
            >>> # Single-level keys
            >>> KeyPathDict.to_nested_dict({"a": 1, "b": 2})
            {'a': 1, 'b': 2}
        
        See Also:
            - apply_overrides(): Instance method for in-place application
            - KeyPathAccessor: Low-level KeyPath access
        """
        import re
        
        # ✅ Phase 1: Array index preprocessing
        # items[0]__dir_path → nested dict with list
        result = {}
        separator = "__"
        
        for key, value in keypath_dict.items():
            key_str = str(key)
            
            # Detect [N] pattern in any segment
            # items[0]__dir_path → ["items", 0, "dir_path"]
            parts = []
            for segment in key_str.split(separator):
                array_match = re.match(r'^(\w+)\[(\d+)\]$', segment)
                if array_match:
                    field_name = array_match.group(1)
                    idx = int(array_match.group(2))
                    parts.append((field_name, idx))  # Tuple = array access
                else:
                    parts.append(segment)  # String = dict key
            
            # Build nested structure
            current = result
            for i, part in enumerate(parts[:-1]):
                if isinstance(part, tuple):
                    # Array access: (field_name, idx)
                    field_name, idx = part
                    
                    # Ensure field exists as list
                    if field_name not in current:
                        current[field_name] = []
                    
                    # Ensure list has enough elements
                    while len(current[field_name]) <= idx:
                        current[field_name].append({})
                    
                    current = current[field_name][idx]
                else:
                    # Dict key
                    if part not in current:
                        # Check if next part is array access
                        next_part = parts[i + 1]
                        if isinstance(next_part, tuple):
                            current[part] = []
                        else:
                            current[part] = {}
                    current = current[part]
            
            # Set final value
            final_key = parts[-1]
            if isinstance(final_key, tuple):
                # Should not happen (array access can't be final)
                field_name, idx = final_key
                if field_name not in current:
                    current[field_name] = []
                while len(current[field_name]) <= idx:
                    current[field_name].append(None)
                current[field_name][idx] = value
            else:
                current[final_key] = value
        
        return result
    
    @staticmethod
    def from_nested_dict(
        nested_dict: Mapping[str, Any],
        separator: str = "__",
        *,
        array_bracket: bool = False,
        parent: str = ""
    ) -> Dict[str, Any]:
        """Convert nested dict to flat KeyPath dict.
        
        Transforms nested dict structure into flat dict with KeyPath keys.
        This is the reverse operation of to_nested_dict().
        
        Transformation rules:
        1. Nested dict: Recursively flatten
           {"product": {"title": "..."}} → {"product__title": "..."}
        
        2. List[dict]: Split into field arrays (Extractor pattern)
           {"options": [{"url": "a", "name": "Red"}, {"url": "b", "name": "Blue"}]}
           → {"options__url": ["a", "b"], "options__name": ["Red", "Blue"]}
        
        3. List[primitive]: Keep as-is
           {"images": ["url1", "url2"]} → {"images": ["url1", "url2"]}
        
        4. Primitive: Keep as-is
           {"title": "..."} → {"title": "..."}
        
        Args:
            nested_dict: Nested dict to flatten
            separator: KeyPath separator (default "__")
            array_bracket: Use [*] notation for arrays (default False)
            parent: Parent KeyPath (internal, for recursion)
        
        Returns:
            Flat KeyPath dict
        
        Examples:
            >>> # Basic nested dict
            >>> KeyPathDict.from_nested_dict({"a": {"b": 1}})
            {'a__b': 1}
            
            >>> # List[dict] → field arrays (Extractor pattern)
            >>> KeyPathDict.from_nested_dict({
            ...     "options": [{"url": "a.jpg", "name": "Red"}, {"url": "b.jpg", "name": "Blue"}]
            ... })
            {'options__url': ['a.jpg', 'b.jpg'], 'options__name': ['Red', 'Blue']}
            
            >>> # Mixed structure (like Aliexpress JS result)
            >>> KeyPathDict.from_nested_dict({
            ...     "product": {"title": "iPhone", "price": "$999"},
            ...     "images": ["img1.jpg", "img2.jpg"],
            ...     "optionsItems": [{"url": "opt1.jpg", "name": "Red"}]
            ... })
            {
                'product__title': 'iPhone',
                'product__price': '$999',
                'images': ['img1.jpg', 'img2.jpg'],
                'optionsItems__url': ['opt1.jpg'],
                'optionsItems__name': ['Red']
            }
            
            >>> # List[primitive] kept as-is
            >>> KeyPathDict.from_nested_dict({"tags": ["new", "hot"]})
            {'tags': ['new', 'hot']}
        
        See Also:
            - to_nested_dict(): Reverse operation (Flat → Nested)
            - Extractor._flatten_to_keypath(): Similar logic in crawl_utils
        """
        result = {}
        
        def flatten(data: Any, path: str = "") -> None:
            """Recursive flatten helper."""
            if isinstance(data, dict):
                # Nested dict: recurse into each key
                for key, value in data.items():
                    new_path = f"{path}{separator}{key}" if path else key
                    flatten(value, new_path)
            
            elif isinstance(data, list) and data:
                # Check if list of dicts (need to split into field arrays)
                if isinstance(data[0], dict):
                    # List[dict] → field arrays
                    # Extract all unique fields across all items
                    all_fields = set()
                    for item in data:
                        if isinstance(item, dict):
                            all_fields.update(item.keys())
                    
                    # Create array for each field
                    for field in sorted(all_fields):  # sorted for deterministic order
                        field_path = f"{path}{separator}{field}"
                        field_values = []
                        for item in data:
                            if isinstance(item, dict):
                                field_values.append(item.get(field))
                            else:
                                field_values.append(None)
                        result[field_path] = field_values
                else:
                    # List[primitive]: keep as-is
                    result[path] = data
            
            else:
                # Primitive value or empty list: keep as-is
                result[path] = data
        
        flatten(nested_dict)
        return result
