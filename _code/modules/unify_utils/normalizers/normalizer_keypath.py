# -*- coding: utf-8 -*-
# unify_utils/normalizers/keypath_normalizer.py

from __future__ import annotations
from typing import List
from data_utils.types import KeyPath
from data_utils.string_ops import StringOps
from unify_utils.core.base_normalizer import NormalizerBase
from unify_utils.core.policy import KeyPathNormalizePolicy


class KeyPathNormalizer(NormalizerBase):
    """KeyPath 문자열 또는 리스트를 정규화하여 List[str] 형태로 변환합니다.

    - "a.b.c" → ["a", "b", "c"]
    - ["a", "b", "c"] → 그대로 유지
    - 잘못된 입력(str, list 외)은 strict 모드에서 예외 발생
    """

    def __init__(self, policy: KeyPathNormalizePolicy):
        super().__init__(recursive=policy.recursive, strict=policy.strict)
        self.policy = policy

    def _apply_single(self, value: KeyPath) -> List[str]:
        if isinstance(value, str):
            return StringOps.split_str_path(value, sep=self.policy.sep)
        elif isinstance(value, list):
            return [str(v) for v in value if v]
        if self.strict:
            raise TypeError(f"[KeyPathNormalizer] Invalid KeyPath type: {type(value).__name__}")
        return []
