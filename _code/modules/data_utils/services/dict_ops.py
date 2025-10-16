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
    # Blank Value Handling
    # ------------------------------------------------------------------
    @staticmethod
    def blanks_to_none(data: Dict[str, Any], *, deep: bool = True) -> Dict[str, Any]:
        """Convert blank values (empty strings) to None.

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
        def visit(path, key, value):
            # Convert empty/whitespace strings to None
            if isinstance(value, str) and not value.strip():
                return key, None
            return key, value

        if not deep:
            # Shallow conversion
            return {
                k: (None if isinstance(v, str) and not v.strip() else v)
                for k, v in data.items()
            }

        return remap(data, visit=visit)

    # ------------------------------------------------------------------
    # Drop None Values
    # ------------------------------------------------------------------
    @staticmethod
    def drop_none(data: Dict[str, Any], *, deep: bool = True) -> Dict[str, Any]:
        """Remove all keys with None values from a dictionary.

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
        def visit(path, key, value):
            # Drop if value is None
            if value is None:
                return False  # Drop this key-value pair
            return key, value

        if not deep:
            # Shallow filter
            return {k: v for k, v in data.items() if v is not None}

        return remap(data, visit=visit)
    
    @staticmethod
    def drop_blanks(data: Dict[str, Any], *, deep: bool = True) -> Dict[str, Any]:
        """Remove all keys with blank values (None or empty strings).

        Args:
            data: The dictionary to filter.
            deep: If ``True``, remove blank values recursively in nested dicts.
                If ``False``, only filter top-level keys.

        Returns:
            A new dictionary with blank values removed.

        Examples:
            >>> DictOps.drop_blanks({"a": 1, "b": None, "c": "", "d": "ok"})
            {'a': 1, 'd': 'ok'}
            >>> DictOps.drop_blanks({"a": {"b": "", "c": 2}}, deep=True)
            {'a': {'c': 2}}
        """
        def visit(path, key, value):
            # Drop if value is None or empty string
            if value is None or (isinstance(value, str) and not value.strip()):
                return False  # Drop this key-value pair
            return key, value

        if not deep:
            # Shallow filter
            return {
                k: v for k, v in data.items() 
                if v is not None and not (isinstance(v, str) and not v.strip())
            }

        return remap(data, visit=visit)

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



