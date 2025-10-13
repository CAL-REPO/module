# -*- coding: utf-8 -*-
# data_utils/dict_ops.py

from __future__ import annotations

from typing import Any, Callable, Dict, Mapping, Union, List
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

        Uses :func:`boltons.iterutils.remap` to traverse the patch dictionary
        and merge nested dictionaries. Non-dictionary values will overwrite
        existing values. Nested dictionaries are merged recursively.

        Args:
            base: The destination dictionary to merge into.
            patch: The source dictionary whose values should be merged into ``base``.
            inplace: If ``True``, modifies ``base`` in place. If ``False``, a deep
                copy of ``base`` is merged and returned.

        Returns:
            The merged dictionary.
        """
        target = base if inplace else copy.deepcopy(base)

        def visit(path, key, value):
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                DictOps.deep_update(target[key], value, inplace=True)
                return key, target[key]
            target[key] = copy.deepcopy(value)
            return key, value

        remap(patch, visit=visit)
        return target

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



