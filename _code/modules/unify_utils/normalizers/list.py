# -*- coding: utf-8 -*-
# unify_utils/normalizers/list.py
# description: unify_utils.normalizers — 리스트 및 시퀀스형 데이터 정규화기
from __future__ import annotations

import re
from typing import Any, List
from ..core.interface import Normalizer
from ..core.policy import ListNormalizePolicy


class ListNormalizer(Normalizer):
    """리스트 및 시퀀스형 데이터 정규화기.

    문자열을 분리하거나, 리스트/튜플을 일관된 형태로 정제합니다.
    ListPolicy를 통해 구분자, 캐스팅 함수, 길이 제약 등을 지정합니다.
    """

    def __init__(self, policy: ListNormalizePolicy):
        super().__init__(recursive=policy.recursive, strict=policy.strict)
        self.policy = policy

    # ------------------------------------------------------------------
    # Core Logic
    # ------------------------------------------------------------------
    def _apply_single(self, value: Any) -> List[Any]:
        if value is None:
            return []

        # 이미 리스트/튜플인 경우
        if isinstance(value, (list, tuple)):
            out = list(value)

        elif isinstance(value, str):
            # ✅ sep 지정 없으면 쉼표·공백 구분
            sep_pattern = self.policy.sep if self.policy.sep else r"[,\s]+"
            parts = re.split(sep_pattern, value.strip())
            out = parts if self.policy.keep_empty else [p for p in parts if p]

        else:
            out = [value]

        # 타입 캐스팅 처리
        if self.policy.item_cast:
            casted = []
            for x in out:
                try:
                    casted.append(self.policy.item_cast(x))
                except Exception:
                    if self.strict:
                        raise
            out = casted

        # 길이 제약
        if self.policy.min_len is not None and len(out) < self.policy.min_len:
            return []
        if self.policy.max_len is not None and len(out) > self.policy.max_len:
            out = out[: self.policy.max_len]

        return out
