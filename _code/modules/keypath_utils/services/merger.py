# -*- coding: utf-8 -*-
# keypath_utils/services/merger.py
# KeyPath 기반 Dict Merger (프로젝트 특정)

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
from data_utils.services.dict_ops import DictOps


class KeyPathMergePolicy(BaseModel):
    """KeyPathMerger 정책.
    
    Attributes:
        deep: Deep merge 여부 (기본값: True)
        inplace: 원본 수정 여부 (기본값: True)
        overwrite_lists: 리스트 덮어쓰기 여부 (기본값: True, False면 append)
    """
    
    deep: bool = Field(
        default=True,
        description="재귀적 Deep merge 여부"
    )
    inplace: bool = Field(
        default=True,
        description="원본 딕셔너리 수정 여부 (False면 복사본 반환)"
    )
    overwrite_lists: bool = Field(
        default=True,
        description="리스트 값 처리 방식 (True: 덮어쓰기, False: append/extend)"
    )


class KeyPathMerger:
    """KeyPath 기반 Dict Merger.
    
    DictOps.deep_update를 래핑하여 정책 기반 merge 제공.
    
    Examples:
        >>> # 기본 deep merge
        >>> merger = KeyPathMerger()
        >>> base = {"a": {"b": 1, "c": 2}}
        >>> patch = {"a": {"b": 99, "d": 3}}
        >>> merger.merge(base, patch)
        {'a': {'b': 99, 'c': 2, 'd': 3}}
        
        >>> # Shallow merge
        >>> merger = KeyPathMerger(policy=KeyPathMergePolicy(deep=False))
        >>> base = {"a": {"b": 1, "c": 2}}
        >>> patch = {"a": {"d": 3}}
        >>> merger.merge(base, patch)
        {'a': {'d': 3}}  # 'a' 전체가 교체됨
        
        >>> # 원본 보호 (inplace=False)
        >>> merger = KeyPathMerger(policy=KeyPathMergePolicy(inplace=False))
        >>> base = {"a": 1}
        >>> result = merger.merge(base, {"b": 2})
        >>> base  # 원본 유지
        {'a': 1}
        >>> result  # 복사본 반환
        {'a': 1, 'b': 2}
    """
    
    def __init__(self, policy: Optional[KeyPathMergePolicy] = None):
        """
        Args:
            policy: Merge 정책 (기본값: KeyPathMergePolicy())
        """
        self.policy = policy or KeyPathMergePolicy()
    
    def merge(
        self,
        base: Dict[str, Any],
        patch: Dict[str, Any],
        *,
        policy: Optional[KeyPathMergePolicy] = None
    ) -> Dict[str, Any]:
        """Dict 병합.
        
        Args:
            base: 기본 딕셔너리
            patch: 덮어쓸 딕셔너리
            policy: 일회성 정책 오버라이드 (없으면 인스턴스 정책 사용)
        
        Returns:
            병합된 딕셔너리
        
        Examples:
            >>> merger = KeyPathMerger()
            >>> base = {"a": {"b": 1}}
            >>> patch = {"a": {"c": 2}}
            >>> result = merger.merge(base, patch)
            >>> result
            {'a': {'b': 1, 'c': 2}}
        """
        # 정책 결정 (파라미터 > 인스턴스)
        active_policy = policy or self.policy
        
        # Deep vs Shallow
        if active_policy.deep:
            return DictOps.deep_update(
                base,
                patch,
                inplace=active_policy.inplace
            )
        else:
            # Shallow update
            if active_policy.inplace:
                base.update(patch)
                return base
            else:
                import copy
                result = copy.deepcopy(base)
                result.update(patch)
                return result
    
    def merge_multiple(
        self,
        *dicts: Dict[str, Any],
        policy: Optional[KeyPathMergePolicy] = None
    ) -> Dict[str, Any]:
        """여러 딕셔너리를 순차적으로 병합.
        
        Args:
            *dicts: 병합할 딕셔너리들 (왼쪽에서 오른쪽 순서로 병합)
            policy: 일회성 정책 오버라이드
        
        Returns:
            병합된 딕셔너리
        
        Examples:
            >>> merger = KeyPathMerger()
            >>> result = merger.merge_multiple(
            ...     {"a": 1},
            ...     {"b": 2},
            ...     {"c": 3}
            ... )
            >>> result
            {'a': 1, 'b': 2, 'c': 3}
            
            >>> # Deep merge
            >>> result = merger.merge_multiple(
            ...     {"config": {"db": "localhost"}},
            ...     {"config": {"port": 5432}},
            ...     {"config": {"user": "admin"}}
            ... )
            >>> result
            {'config': {'db': 'localhost', 'port': 5432, 'user': 'admin'}}
        """
        if not dicts:
            return {}
        
        # 정책 결정
        active_policy = policy or self.policy
        
        # 첫 번째 dict를 기본으로
        import copy
        result = copy.deepcopy(dicts[0]) if not active_policy.inplace else dicts[0]
        
        # 나머지를 순차 병합
        for d in dicts[1:]:
            result = self.merge(result, d, policy=active_policy)
        
        return result
