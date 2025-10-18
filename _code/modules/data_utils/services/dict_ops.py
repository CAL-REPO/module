# -*- coding: utf-8 -*-
"""
data_utils.services.dict_ops
---------------------------
Dictionary manipulation utilities for deep update, merge, and key remapping.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Mapping, Union
import copy
from boltons.iterutils import remap
from data_utils.core.types import BlankType


class DictOps:
    """Dictionary manipulation utilities based on :func:`boltons.iterutils.remap`.

    Provides static methods for recursively merging dictionaries and remapping
    keys according to a mapping or callable.
    """

    # ------------------------------------------------------------------
    # Deep Update / Merge
    # ------------------------------------------------------------------
    @staticmethod
    def deep_update(base: Dict[str, Any], patch: Dict[str, Any], *, inplace: bool = True) -> Dict[str, Any]:
        """Recursively merge ``patch`` into ``base``.

        Iterates over the top-level keys in ``patch`` and merges them into ``base``.
        Nested dictionaries are merged recursively. Non-dictionary values will 
        overwrite existing values.

        Args:
            base: The destination dictionary to merge into.
            patch: The source dictionary whose values should be merged into ``base``.
            inplace: If ``True``, modifies ``base`` in place. If ``False``, a deep
                copy of ``base`` is merged and returned.

        Returns:
            The merged dictionary.
        """
        target = base if inplace else copy.deepcopy(base)

        # Iterate over top-level keys in patch
        for key, value in patch.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                # Both are dicts: recursively merge
                DictOps.deep_update(target[key], value, inplace=True)
            else:
                # Overwrite with deep copy
                target[key] = copy.deepcopy(value)

        return target

    # ------------------------------------------------------------------
    # Blank Value Handling (Unified)
    # ------------------------------------------------------------------
    @staticmethod
    def process_blanks(
        data: Dict[str, Any],
        *,
        types: BlankType = BlankType.STANDARD,
        action: str = "drop",
        deep: bool = True
    ) -> Dict[str, Any]:
        """Blank 값 처리 (통합 메서드)
        
        Args:
            data: 처리할 딕셔너리
            types: 처리할 blank 타입 (BlankType 플래그)
            action: 처리 방식
                - "drop": blank 키-값 쌍 제거
                - "to_none": blank 값을 None으로 변환
            deep: 재귀적 처리 여부
        
        Returns:
            처리된 딕셔너리
        
        Examples:
            >>> # None만 제거
            >>> DictOps.process_blanks(data, types=BlankType.NONE)
            {'a': 1, 'c': 3}
            
            >>> # None + 빈 문자열 제거
            >>> DictOps.process_blanks(data, types=BlankType.BASIC)
            {'a': 1}
            
            >>> # 모든 blank 제거
            >>> DictOps.process_blanks(data, types=BlankType.ALL)
            {'a': 1}
            
            >>> # 빈 문자열을 None으로 변환
            >>> DictOps.process_blanks(
            ...     data, 
            ...     types=BlankType.EMPTY_STRINGS, 
            ...     action="to_none"
            ... )
            {'a': 1, 'b': None, 'c': '  '}
        """
        def is_blank(value: Any) -> bool:
            """값이 blank인지 확인"""
            # None 체크
            if BlankType.NONE in types and value is None:
                return True
            
            # 문자열 체크
            if isinstance(value, str):
                if BlankType.EMPTY_STR in types and value == "":
                    return True
                if BlankType.WHITESPACE in types and not value.strip():
                    return True
            
            # 컨테이너 체크
            if BlankType.EMPTY_LIST in types and isinstance(value, list) and len(value) == 0:
                return True
            
            if BlankType.EMPTY_DICT in types and isinstance(value, dict) and len(value) == 0:
                return True
            
            if BlankType.EMPTY_TUPLE in types and isinstance(value, tuple) and len(value) == 0:
                return True
            
            if BlankType.EMPTY_SET in types and isinstance(value, set) and len(value) == 0:
                return True
            
            return False
        
        def visit(path, key, value):
            if is_blank(value):
                if action == "drop":
                    return False  # 키-값 쌍 제거
                elif action == "to_none":
                    return key, None  # 값을 None으로 변환
            return key, value
        
        if not deep:
            # Shallow 처리
            if action == "drop":
                return {k: v for k, v in data.items() if not is_blank(v)}
            else:  # to_none
                return {k: (None if is_blank(v) else v) for k, v in data.items()}
        
        return remap(data, visit=visit)
    
    # ------------------------------------------------------------------
    # Blank Value Handling (Legacy - Backward Compatibility)
    # ------------------------------------------------------------------
    @staticmethod
    def blanks_to_none(data: Dict[str, Any], *, deep: bool = True) -> Dict[str, Any]:
        """Convert blank values (empty strings) to None.
        
        ⚠️ Legacy: 새 코드에서는 process_blanks() 사용 권장
        
        Args:
            data: The dictionary to process.
            deep: If ``True``, convert blank values recursively in nested dicts.
                If ``False``, only process top-level values.

        Returns:
            A new dictionary with blank values converted to None.

        Examples:
            >>> DictOps.blanks_to_none({"a": "test", "b": "", "c": "  "})
            {'a': 'test', 'b': None, 'c': None}
            >>> DictOps.blanks_to_none({"a": {"b": "", "c": "ok"}}, deep=True)
            {'a': {'b': None, 'c': 'ok'}}
        """
        return DictOps.process_blanks(
            data,
            types=BlankType.EMPTY_STRINGS,
            action="to_none",
            deep=deep
        )

    # ------------------------------------------------------------------
    # Drop None Values
    # ------------------------------------------------------------------
    @staticmethod
    def drop_none(data: Dict[str, Any], *, deep: bool = True) -> Dict[str, Any]:
        """Remove all keys with None values from a dictionary.
        
        ⚠️ Legacy: 새 코드에서는 process_blanks() 사용 권장

        Args:
            data: The dictionary to filter.
            deep: If ``True``, remove None values recursively in nested dicts.
                If ``False``, only filter top-level keys.

        Returns:
            A new dictionary with None values removed.

        Examples:
            >>> DictOps.drop_none({"a": 1, "b": None, "c": 3})
            {'a': 1, 'c': 3}
            >>> DictOps.drop_none({"a": {"b": None, "c": 2}}, deep=True)
            {'a': {'c': 2}}
        """
        return DictOps.process_blanks(
            data,
            types=BlankType.NONE,
            action="drop",
            deep=deep
        )
    
    @staticmethod
    def drop_blanks(
        data: Dict[str, Any], 
        *, 
        deep: bool = True, 
        include_empty_containers: bool = True
    ) -> Dict[str, Any]:
        """Remove all keys with blank values (None, empty strings, and optionally empty containers).
        
        ⚠️ Legacy: 새 코드에서는 process_blanks() 사용 권장

        Args:
            data: The dictionary to filter.
            deep: If ``True``, remove blank values recursively in nested dicts.
                If ``False``, only filter top-level keys.
            include_empty_containers: If ``True``, also remove empty lists and dicts.
                If ``False``, only remove None and empty strings.

        Returns:
            A new dictionary with blank values removed.

        Examples:
            >>> DictOps.drop_blanks({"a": 1, "b": None, "c": "", "d": "ok"})
            {'a': 1, 'd': 'ok'}
            >>> DictOps.drop_blanks({"a": {"b": "", "c": 2}}, deep=True)
            {'a': {'c': 2}}
            >>> DictOps.drop_blanks({"a": 1, "b": [], "c": {}}, include_empty_containers=True)
            {'a': 1}
            >>> DictOps.drop_blanks({"a": 1, "b": [], "c": {}}, include_empty_containers=False)
            {'a': 1, 'b': [], 'c': {}}
        """
        types = BlankType.STANDARD  # None + EMPTY_STRINGS
        if include_empty_containers:
            types |= BlankType.EMPTY_CONTAINERS
        
        return DictOps.process_blanks(
            data,
            types=types,
            action="drop",
            deep=deep
        )

    # ------------------------------------------------------------------
    # Rekey
    # ------------------------------------------------------------------
    @staticmethod
    def rekey(
        data: Dict[str, Any],
        mapping_or_func: Union[Mapping[str, str], Callable[[str], str]],
        *,
        deep: bool = True,
    ) -> Dict[str, Any]:
        """Remap the keys of a dictionary using a mapping or callable.

        Args:
            data: The dictionary whose keys should be remapped.
            mapping_or_func: Either a mapping of old key to new key names, or a
                callable that takes a key and returns a new key.
            deep: If ``True``, remap keys in nested dictionaries recursively.
                If ``False``, only remap the top-level keys.

        Returns:
            A new dictionary with keys remapped according to ``mapping_or_func``.
        """

        def visit(path, key, value):
            if isinstance(mapping_or_func, Mapping):
                new_key = mapping_or_func.get(key, key)
            else:
                new_key = mapping_or_func(key)
            return new_key, value

        # ✅ deep=False일 때도 함수/매핑 모두 지원
        if not deep:
            def shallow_visit(p, k, v):
                if isinstance(mapping_or_func, Mapping):
                    return mapping_or_func.get(k, k), v
                return mapping_or_func(k), v
            return remap(data, visit=shallow_visit)

        return remap(data, visit=visit)



