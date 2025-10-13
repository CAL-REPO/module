# -*- coding: utf-8 -*-
"""
modules.color — color helpers (no Pillow dependency)

Exports
-------
- to_rgba(value) -> tuple[int, int, int, int]
"""

from __future__ import annotations
from typing import Any, Tuple, Iterable

__all__ = ["to_rgba"]

def _clamp255(x: int) -> int:
    return max(0, min(255, int(x)))

def _from_hex(s: str) -> Tuple[int, int, int, int]:
    s = s.strip().lstrip("#")
    if len(s) == 6:
        r = int(s[0:2], 16); g = int(s[2:4], 16); b = int(s[4:6], 16)
        return (r, g, b, 255)
    if len(s) == 8:
        r = int(s[0:2], 16); g = int(s[2:4], 16); b = int(s[4:6], 16); a = int(s[6:8], 16)
        return (r, g, b, a)
    return (0, 0, 0, 0)

def to_rgba(v: Any) -> Tuple[int, int, int, int]:
    """
    허용 입력:
      - "#RRGGBB" / "#RRGGBBAA"
      - [r,g,b] / [r,g,b,a]
      - "rgb(r,g,b)" / "rgba(r,g,b,a)"
    반환: (r,g,b,a) 0~255
    """
    if v is None:
        return (0, 0, 0, 0)

    # list/tuple
    if isinstance(v, (list, tuple)):
        arr = list(v)
        if len(arr) == 3:
            r, g, b = (_clamp255(x) for x in arr)
            return (r, g, b, 255)
        if len(arr) == 4:
            r, g, b, a = (_clamp255(x) for x in arr)
            return (r, g, b, a)

    s = str(v).strip()
    if s.startswith("#"):
        return _from_hex(s)

    low = s.lower()
    if low.startswith("rgb"):
        try:
            inside = s[s.index("(")+1 : s.rindex(")")]
            parts = [int(x) for x in inside.replace(" ", "").split(",")]
            return to_rgba(parts)
        except Exception:
            return (0, 0, 0, 0)

    # 기타 포맷 미지원 → 투명
    return (0, 0, 0, 0)

