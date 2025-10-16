# -*- coding: utf-8 -*-
# cfg_utils/normalizer.py

from __future__ import annotations
from typing import Any
from unify_utils.normalizers.resolver_reference import ReferenceResolver
from data_utils.services.dict_ops import DictOps
from modules.cfg_utils.core.policy import ConfigPolicy

class ConfigNormalizer:
    """Config 데이터 후처리기
    
    SRP 준수: Reference 해석과 Blank 필터링만 담당
    - Reference 해석: policy.reference_context를 context로 사용
    - Blank 필터링: policy.drop_blanks 설정에 따라 처리
    """

    def __init__(self, policy: ConfigPolicy):
        """ConfigNormalizer 초기화.
        
        Args:
            policy: ConfigPolicy 인스턴스 (reference_context 포함)
        """
        self.policy = policy

    def apply(self, data: dict[str, Any]) -> dict[str, Any]:
        """정규화 적용.
        
        Args:
            data: 정규화할 딕셔너리
            
        Returns:
            정규화된 딕셔너리
        """
        result = data.copy()

        # 1️⃣ Reference 해석 (policy.reference_context 사용)
        if self.policy.resolve_reference:
            # policy.reference_context와 data를 병합한 context 사용
            # policy.reference_context가 우선순위 높음 (paths_dict 등)
            context = {**result, **self.policy.reference_context}
            result = ReferenceResolver(context, recursive=True, strict=False).apply(result)

        # 2️⃣ Blank 필터링 (deep=True로 중첩 dict까지 처리)
        if self.policy.drop_blanks:
            result = DictOps.drop_blanks(result, deep=True)

        return result
