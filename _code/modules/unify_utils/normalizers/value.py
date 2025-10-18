# -*- coding: utf-8 -*-
# unify_utils/normalizers/value_normalizer.py
# description: unify_utils.normalizers — 단일 값 기반 타입 정규화기
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Optional
from ..core.interface import Normalizer
from ..core.policy import ValueNormalizePolicy


class ValueNormalizer(Normalizer):
    """단일 값 기반 정규화기.

    bool/int/date/filename 등의 값 변환을 수행합니다.
    ValuePolicy를 통해 동작 설정을 관리합니다.
    """

    def __init__(self, policy: ValueNormalizePolicy):
        super().__init__(recursive=policy.recursive, strict=policy.strict)
        self.policy = policy

    # ------------------------------------------------------------------
    # Core Logic
    # ------------------------------------------------------------------
    def _apply_single(self, value: Any) -> Any:
        return value  # 기본 동작: 그대로 반환 (명시적 메서드 사용 권장)

    # ------------------------------------------------------------------
    # Normalization Methods
    # ------------------------------------------------------------------
    def normalize_bool(self, v: Any) -> Optional[bool]:
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return bool(v)
        if isinstance(v, str):
            s = v.strip().lower()
            if s in ("true", "1", "y", "yes", "on"):
                return True
            if s in ("false", "0", "n", "no", "off"):
                return False
        return None if self.policy.bool_strict else False

    def normalize_int(self, v: Any, default: int = 0) -> int:
        try:
            return int(v)
        except Exception:
            if self.strict:
                raise
            return default

    def normalize_date(self, v: Any) -> Optional[str]:
        fmt = self.policy.date_fmt
        if not v:
            return None
        try:
            if isinstance(v, datetime):
                return v.strftime(fmt)
            if isinstance(v, str):
                dt = datetime.fromisoformat(v.strip())
                return dt.strftime(fmt)
        except Exception:
            if self.strict:
                raise
        return None

    def normalize_filename(self, name: str, *, mode: str = "safe") -> str:
        INVALID = re.compile(r"[\\/:*?\"<>|]+")
        s = INVALID.sub("_", (name or "").strip())
        s = re.sub(r"\s+", " ", s).strip()
        if mode == "slug":
            s = re.sub(r"[^0-9a-zA-Z가-힣_.\- ]+", "", s.lower())
            s = re.sub(r"\s+", "-", s).strip(".-_")
        return s or "_"
