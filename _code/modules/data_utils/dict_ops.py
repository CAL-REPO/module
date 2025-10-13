# -*- coding: utf-8 -*-
# data_utils/dict_ops.py

from __future__ import annotations

from typing import Any, Callable, Dict, Mapping, Union, List
import copy
from boltons.iterutils import remap


class DictOps:
    """
    boltons.iterutils.remap 기반 dict 조작 유틸리티.
    - deep_update: 재귀 병합
    - rekey: 키 리매핑
    """

    # ------------------------------------------------------------------
    # Deep Update / Merge
    # ------------------------------------------------------------------
    @staticmethod
    def deep_update(base: Dict[str, Any], patch: Dict[str, Any], *, inplace: bool = True) -> Dict[str, Any]:
        """
        remap 기반 재귀 병합
        base: 대상 dict
        patch: 병합할 dict
        inplace: 원본 수정 여부
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
        """
        remap 기반 키 리매핑
        - mapping: {"old": "new"}
        - func: lambda k: k.upper()
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



