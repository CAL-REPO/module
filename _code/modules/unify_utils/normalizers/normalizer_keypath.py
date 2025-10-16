# -*- coding: utf-8 -*-
# unify_utils/normalizers/normalizer_keypath.py

from __future__ import annotations
from typing import List, Sequence
from data_utils.core.types import KeyPath
from data_utils.services.string_ops import StringOps
from unify_utils.core.base_normalizer import NormalizerBase
from unify_utils.core.policy import KeyPathNormalizePolicy


class KeyPathNormalizer(NormalizerBase):
    """KeyPath 문자열 또는 리스트를 정규화하여 List[str] 형태로 변환합니다.

    정책 기반 해석:
        - sep: 구분자 (예: ".", "__", "|")
        - collapse: 빈 세그먼트 제거
        - escape_char: 구분자 이스케이프 처리
        - accept_dot: 구분자 없을 때 "." fallback
        - enable_list_index: 배열 인덱스 [0], [1] 지원

    Examples:
        >>> policy = KeyPathNormalizePolicy(sep="__", collapse=True)
        >>> norm = KeyPathNormalizer(policy)
        >>> norm.apply("a__b__c")
        ['a', 'b', 'c']
        
        >>> # 리스트 경로는 리터럴 유지
        >>> norm.apply(["a.b", "c"])
        ['a.b', 'c']
        
        >>> # 이스케이프 처리
        >>> policy2 = KeyPathNormalizePolicy(sep=".", escape_char="\\")
        >>> norm2 = KeyPathNormalizer(policy2)
        >>> norm2.apply("a\\.b.c")  # a.b → c (리터럴 점)
        ['a.b', 'c']
    """

    def __init__(self, policy: KeyPathNormalizePolicy):
        super().__init__(recursive=policy.recursive, strict=policy.strict)
        self.policy = policy

    def _apply_single(self, value: KeyPath) -> List[str]:
        """단일 KeyPath 값을 정규화
        
        Args:
            value: 문자열 또는 리스트 경로
        
        Returns:
            정규화된 경로 세그먼트 리스트
        """
        # 리스트/튜플은 리터럴로 처리 (권장)
        if isinstance(value, (list, tuple)):
            return [str(v) for v in value if v]
        
        if isinstance(value, str):
            return self._parse_string_path(value)
        
        # 지원하지 않는 타입
        if self.strict:
            raise TypeError(f"[KeyPathNormalizer] Invalid KeyPath type: {type(value).__name__}")
        return []
    
    def _parse_string_path(self, key_str: str) -> List[str]:
        """문자열 경로를 파싱 (정책 기반)
        
        Args:
            key_str: 경로 문자열
        
        Returns:
            파싱된 세그먼트 리스트
        """
        # escape 문자 처리
        if self.policy.escape_char and self.policy.escape_char in key_str:
            # 이스케이프된 구분자를 임시 토큰으로 치환
            escaped_sep = key_str.replace(
                f"{self.policy.escape_char}{self.policy.sep}",
                "\x00"  # NULL 문자를 임시 플레이스홀더로 사용
            )
            parts = escaped_sep.split(self.policy.sep)
            # 임시 토큰을 다시 구분자로 복원
            parts = [p.replace("\x00", self.policy.sep) for p in parts]
        else:
            # 일반 split
            parts = key_str.split(self.policy.sep)
        
        # collapse: 빈 문자열 제거
        if self.policy.collapse:
            parts = [p for p in parts if p]
        
        # 배열 인덱스 처리 (옵션)
        if self.policy.enable_list_index:
            parts = self._parse_list_indices(parts)
        
        return parts
    
    def _parse_list_indices(self, parts: List[str]) -> List[str]:
        """[0], [1] 형태를 배열 인덱스로 변환 (선택 기능)
        
        Args:
            parts: 파싱된 세그먼트 리스트
        
        Returns:
            인덱스 변환된 세그먼트 리스트
        """
        result = []
        for part in parts:
            if part.startswith("[") and part.endswith("]"):
                try:
                    idx = int(part[1:-1])
                    result.append(f"[{idx}]")
                except ValueError:
                    result.append(part)
            else:
                result.append(part)
        return result
