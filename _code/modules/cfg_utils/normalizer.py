# -*- coding: utf-8 -*-
# cfg_utils/normalizer.py

from __future__ import annotations
from typing import Any
from unify_utils.normalizers.resolver_reference import ReferenceResolver

class ConfigNormalizer:
    """Config 데이터 후처리기
    - env/include/reference/drop_blanks 처리 담당
    """

    def __init__(self, policy):
        self.policy = policy

    def apply(self, data: dict[str, Any]) -> dict[str, Any]:
        result = data.copy()

        # 1️⃣ Reference 해석
        if self.policy.resolve_reference:
            result = ReferenceResolver(result, recursive=True, strict=False).apply(result)

        # 2️⃣ Blank 필터링
        if self.policy.drop_blanks:
            result = {k: v for k, v in result.items() if v not in (None, "", "None")}

        return result
