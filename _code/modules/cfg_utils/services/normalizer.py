# -*- coding: utf-8 -*-
# cfg_utils/normalizer.py

from __future__ import annotations
from typing import Any
from unify_utils.normalizers.resolver_reference import ReferenceResolver
from data_utils.services.dict_ops import DictOps

class ConfigNormalizer:
    """Config 데이터 후처리기
    - env/include/reference/drop_blanks 처리 담당
    """

    def __init__(self, policy, reference_context: dict[str, Any] | None = None):
        self.policy = policy
        self.reference_context = reference_context or {}

    def apply(self, data: dict[str, Any]) -> dict[str, Any]:
        result = data.copy()

        # 1️⃣ Reference 해석
        if self.policy.resolve_reference:
            # reference_context와 data를 병합한 context 사용
            # reference_context가 우선순위 높음 (paths_dict 등)
            context = {**result, **self.reference_context}
            result = ReferenceResolver(context, recursive=True, strict=False).apply(result)

        # 2️⃣ Blank 필터링 (deep=True로 중첩 dict까지 처리)
        if self.policy.drop_blanks:
            result = DictOps.drop_blanks(result, deep=True)

        return result
