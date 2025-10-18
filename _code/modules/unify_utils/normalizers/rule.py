# -*- coding: utf-8 -*-
# unify_utils/normalizers/rule.py
# description: unify_utils.normalizers — 정규식 및 문자열 클린 룰 기반 정규화기
from __future__ import annotations

import re
from typing import Any
from ..core.interface import Normalizer
from ..core.policy import RuleType, RegexFlag, LetterCase, RuleNormalizePolicy


class RuleBasedNormalizer(Normalizer):
    """정규식 및 문자열 클린 룰 기반 정규화기

    RulePolicy를 기반으로 문자열을 정규화하며, dict/list 구조에 대해 재귀 처리 가능.
    - REGEX: re.sub()을 통한 패턴 치환
    - CLEAN: strip 및 대소문자 변환
    """

    def __init__(self, policy: RuleNormalizePolicy):
        super().__init__(recursive=policy.recursive, strict=policy.strict)
        self.policy = policy

    # ------------------------------------------------------------------
    # Core Logic
    # ------------------------------------------------------------------
    def _apply_single(self, value: Any) -> Any:
        if not isinstance(value, str):
            return value

        result = value
        for rule in self.policy.rules:
            if rule.rule_type == RuleType.REGEX:
                flags = 0
                if rule.flags and RegexFlag.IGNORECASE in rule.flags:
                    flags |= re.IGNORECASE

                result = re.sub(rule.pattern if rule.pattern is not None else "",
                                 rule.replace if rule.replace is not None else "",
                                 result, flags=flags)

            elif rule.rule_type == RuleType.CLEAN:
                if rule.strip:
                    result = result.strip()
                if rule.lettercase == LetterCase.LOWER:
                    result = result.lower()
                elif rule.lettercase == LetterCase.UPPER:
                    result = result.upper()

        return result
