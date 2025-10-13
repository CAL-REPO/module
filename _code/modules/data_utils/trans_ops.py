# -*- coding: utf-8 -*-
# data_utils/trans_ops.py
# description: data_utils.trans_ops — 데이터 구조 변환용 유틸리티 클래스 (TransOps)

from __future__ import annotations
from typing import Any, Dict, List, Tuple
from boltons.iterutils import remap


class TransOps:
    """데이터 구조 변환용 정적 유틸리티.

    주요 기능:
    1. 단일값을 리스트로 변환 (`value_to_list`)
    2. 평면 리스트를 그룹형 pair 구조로 변환 (`list_to_grouped_pairs`)
    3. pair 기반 그룹 구조를 다중값 딕셔너리로 병합 (`group_pairs_to_multivalue`)

    반환 구조 표준:
    - GroupedPairDict: {section: [(key, value), ...]}
    - MultiValueGroupDict: {section: {key: [values]}}
    """

    # ------------------------------------------------------------------
    # 1️⃣ 단일값을 리스트로 정규화
    # ------------------------------------------------------------------
    @staticmethod
    def value_to_list(x: Any) -> List[Any]:
        """입력값을 항상 리스트로 변환합니다.

        예:
            >>> TransOps.value_to_list(5)
            [5]
            >>> TransOps.value_to_list([5, 6])
            [5, 6]
            >>> TransOps.value_to_list(None)
            []
        """
        if x is None:
            return []
        if isinstance(x, list):
            return x
        if isinstance(x, tuple):
            return list(x)
        return [x]

    # ------------------------------------------------------------------
    # 2️⃣ 평면 리스트 → 그룹형 (section: [(key, value)]) 구조
    # ------------------------------------------------------------------
    @staticmethod
    def list_to_grouped_pairs(
        seq: List[Any],
        group_size: int = 3,
        *,
        section_index: int = 0,
        key_index: int = 1,
        value_index: int = 2,
        skip_missing: bool = False,
    ) -> Dict[str | None, List[Tuple[str | None, Any]]]:
        """평면 리스트 [section, key, value, section, key, value, ...] 를
        {section: [(key, value), ...]} 형태로 변환합니다.

        Args:
            seq: 변환할 평면 리스트
            group_size: 반복 단위 크기 (기본 3)
            skip_missing: key 또는 value가 None일 때 스킵 여부
        Returns:
            dict[str|None, list[tuple[str|None, Any]]]
        """
        out: Dict[str | None, List[Tuple[str | None, Any]]] = {}
        if not isinstance(seq, list) or len(seq) % group_size != 0:
            return out

        for i in range(0, len(seq), group_size):
            group = seq[i:i + group_size]
            if len(group) < group_size:
                continue
            section, key, value = group[section_index], group[key_index], group[value_index]

            if skip_missing and (key is None or value is None):
                continue

            section = str(section) if section is not None else None
            key = str(key) if key is not None else None
            out.setdefault(section, []).append((key, value))

        return out

    # ------------------------------------------------------------------
    # 3️⃣ pair 그룹 → 다중값 병합 구조
    # ------------------------------------------------------------------
    @staticmethod
    def group_pairs_to_multivalue(
        grouped_pairs: Dict[str | None, List[Tuple[str | None, Any]]]
    ) -> Dict[str | None, Dict[str | None, List[Any]]]:
        """GroupedPairDict ({section: [(key, value), ...]}) → MultiValueGroupDict 변환.

        동일 key가 여러 value를 가질 경우 리스트로 병합됩니다.

        예:
            >>> pairs = {"section": [("key1", "value1"), ("key1", "value2"), ("key2", "value3")]}
            >>> TransOps.group_pairs_to_multivalue(pairs)
            {'section': {'key1': ['value1', 'value2'], 'key2': ['value3']}}
        """
        out: Dict[str | None, Dict[str | None, List[Any]]] = {}

        for section, items in grouped_pairs.items():
            section_key = section if section is not None else None
            out.setdefault(section_key, {})

            for key, value in items:
                key_norm = key if key is not None else None
                out[section_key].setdefault(key_norm, []).append(value)

        return out

    # ------------------------------------------------------------------
    # Flatten
    # ------------------------------------------------------------------
    @staticmethod
    def dict_to_keypath(data: Dict[str, Any], sep: str = ".") -> Dict[str, Any]:
        """
        remap 기반 평탄화 {"a": {"b": 1}} -> {"a.b": 1}
        """
        flat: Dict[str, Any] = {}

        def visit(path, key, value):
            if isinstance(value, dict):
                return key, value
            joined_key = sep.join([*path, key]) if path else key
            flat[joined_key] = value
            return key, value

        remap(data, visit=visit)
        return flat

    # ------------------------------------------------------------------
    # Unflatten
    # ------------------------------------------------------------------
    @staticmethod
    def keypath_to_dict(data: Dict[str, Any], sep: str = ".") -> Dict[str, Any]:
        """
        평탄화된 dict를 중첩 구조로 복원 {"a.b": 1} -> {"a": {"b": 1}}
        """
        result: Dict[str, Any] = {}
        for key, value in data.items():
            parts: List[str] = key.split(sep)
            cur = result
            for part in parts[:-1]:
                cur = cur.setdefault(part, {})
            cur[parts[-1]] = value
        return result