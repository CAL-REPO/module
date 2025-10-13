# -*- coding: utf-8 -*-
# fso_utils/naming.py - FSONameBuilder (파일/디렉터리 이름 생성기)

from __future__ import annotations
from pathlib import Path
from datetime import datetime
import re
from .policy import FSONamePolicy

_ILLEGAL = r'[<>:"/\\|?*]'  # Windows 금지문자


class FSONameBuilder:
    """
    FSONamePolicy를 기반으로 파일 또는 디렉터리 이름을 생성하는 클래스
    """

    def __init__(self, policy: FSONamePolicy):
        self.p = policy

    def _sanitize(self, s: str) -> str:
        return re.sub(_ILLEGAL, "", s)

    def _apply_case(self, s: str) -> str:
        return s.lower() if self.p.case == "lower" else s.upper() if self.p.case == "upper" else s

    def _tail(self, counter: int | None = None) -> str | None:
        base_tail = None

        if self.p.tail is not None:
            base_tail = self.p.tail
        elif self.p.tail_mode:
            if self.p.tail_mode == "date":
                base_tail = datetime.now().strftime(self.p.date_format)
            elif self.p.tail_mode == "datetime":
                base_tail = datetime.now().strftime(self.p.date_format + "_%H-%M-%S")
            elif self.p.tail_mode == "counter":
                counter = counter or 1
                c_str = f"{counter:0{self.p.counter_width}d}"
                if self.p.auto_expand and len(c_str) > self.p.counter_width:
                    c_str = str(counter)
                base_tail = c_str
            elif self.p.tail_mode == "datetime_counter":
                date_part = datetime.now().strftime(self.p.date_format + "_%H-%M-%S")
                counter = counter or 1
                c_str = f"{counter:0{self.p.counter_width}d}"
                if self.p.auto_expand and len(c_str) > self.p.counter_width:
                    c_str = str(counter)
                base_tail = f"{date_part}{self.p.delimiter}{c_str}"

        # tail_suffix 적용
        if base_tail and self.p.tail_suffix:
            base_tail = f"{base_tail}{self.p.delimiter}{self.p.tail_suffix}"
        elif self.p.tail_suffix and not base_tail:
            base_tail = self.p.tail_suffix

        return base_tail

    def build(self, counter: int | None = None) -> str:
        parts = [self.p.prefix, self.p.name, self.p.suffix, self._tail(counter)]
        parts = [x for x in parts if x]
        stem = self.p.delimiter.join(
            self._apply_case(self._sanitize(x) if self.p.sanitize else self._apply_case(x))
            for x in parts
        )

        # 파일일 경우 확장자 부착
        if self.p.as_type == "file":
            ext = self.p.extension or ""
            ext = (ext if ext.startswith(".") else f".{ext}") if ext else ""
            return stem + ext
        else:
            return stem  # 디렉터리는 확장자 없음

    def build_unique(self, directory: Path) -> Path:
        """
        디렉터리 내 중복되지 않는 파일/폴더 경로 생성
        """
        name = self.build()
        candidate = directory / name
        if not self.p.ensure_unique:
            return candidate

        counter = 1
        while candidate.exists():
            candidate = directory / self.build(counter)
            counter += 1
        return candidate
