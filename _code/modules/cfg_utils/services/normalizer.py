# -*- coding: utf-8 -*-
# cfg_utils/normalizer.py

from __future__ import annotations
from typing import Any
from data_utils.services.dict_ops import DictOps
from modules.cfg_utils.core.policy import ConfigPolicy

class ConfigNormalizer:
    """Config 데이터 후처리기 (Dict 정규화 전담)
    
    책임:
    1. ReferenceResolver: 내부 참조 치환 (${key.path})
    2. Drop blanks: 빈 값 제거
    
    Resolver 역할 구분:
    - YamlParser: 외부 변수 치환 (PlaceholderResolver)
      * {{VAR}}: 사용자 context
      * ${VAR}: 환경 변수
    - ConfigNormalizer: 내부 참조 치환 (ReferenceResolver)
      * ${key.path}: dict 내부 키 경로 참조
    
    사용 시나리오:
    1. Dict 직접 로드 시 내부 참조 치환
    2. 병합 후 생성된 내부 참조 치환
    3. Blank 필터링 등 정규화 작업
    """

    def __init__(self, policy: ConfigPolicy):
        """ConfigNormalizer 초기화.
        
        Args:
            policy: ConfigPolicy 인스턴스
        """
        self.policy = policy

    def apply(self, data: dict[str, Any]) -> dict[str, Any]:
        """정규화 적용.
        
        Args:
            data: 정규화할 딕셔너리
            
        Returns:
            정규화된 딕셔너리
            
        Examples:
            >>> # 내부 참조 치환
            >>> policy = ConfigPolicy(resolve_reference=True)
            >>> normalizer = ConfigNormalizer(policy)
            >>> data = {
            ...     "db": {"host": "localhost"},
            ...     "server": {"url": "${db.host}:3000"}
            ... }
            >>> result = normalizer.apply(data)
            >>> result["server"]["url"]
            'localhost:3000'
            
            >>> # reference_context 사용
            >>> policy = ConfigPolicy(
            ...     resolve_reference=True,
            ...     reference_context={"base_path": "/path"}
            ... )
            >>> data = {"config": {"path": "${base_path}/config.yaml"}}
            >>> result = normalizer.apply(data)
            >>> result["config"]["path"]
            '/path/config.yaml'
        """
        result = data.copy()

        # 1️⃣ Reference 치환 (내부 keypath 참조)
        if self.policy.resolve_reference:
            from unify_utils.resolver.reference import ReferenceResolver
            
            # reference_context가 있으면 data와 병합 (우선순위: context > data)
            resolve_data = dict(result)
            if self.policy.reference_context:
                # context를 우선순위 높게 병합
                resolve_data = {**result, **self.policy.reference_context}
            
            resolver = ReferenceResolver(
                data=resolve_data,
                recursive=True,
                strict=False
            )
            result = resolver.apply(result)

        # 2️⃣ Blank 필터링 (deep=True로 중첩 dict까지 처리)
        if self.policy.drop_blanks:
            result = DictOps.drop_blanks(result, deep=True)

        return result
