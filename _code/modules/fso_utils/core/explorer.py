# -*- coding: utf-8 -*-
# fso_utils/explorer.py - 디렉터리 기반 파일/디렉터리 탐색기 with 정책 및 필터 지원

from __future__ import annotations

from pathlib import Path
from typing import List, Optional
from datetime import datetime

from typing import Union
from data_utils.types import PathLike
from .policy import FSOExplorerPolicy

class FSOExplorer:
    """
    디렉터리 내 파일/서브디렉터리 탐색기 (정책 기반 필터링 지원)
    - 확장자, 이름, 크기, 수정일 기준 필터링
    - 재귀 탐색 지원
    """

    def __init__(self, root: PathLike, policy: Optional[FSOExplorerPolicy] = None):
        self.root = Path(root).expanduser().resolve()
        self.policy = policy or FSOExplorerPolicy() # pyright: ignore[reportCallIssue]

        # Validate that the root exists and is a directory. Use English messages for errors.
        if not self.root.exists():
            raise FileNotFoundError(f"Specified path does not exist: {self.root}")
        if not self.root.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {self.root}")

    def _filter(self, paths: List[Path]) -> List[Path]:
        result = []
        for p in paths:
            if self.policy.allowed_exts and p.suffix.lower() not in [e.lower() if e.startswith('.') else f".{e.lower()}" for e in self.policy.allowed_exts]:
                continue
            if self.policy.name_patterns:
                if not any(p.match(pat) for pat in self.policy.name_patterns):
                    continue
            if self.policy.min_size or self.policy.max_size:
                try:
                    size = p.stat().st_size
                    if self.policy.min_size and size < self.policy.min_size:
                        continue
                    if self.policy.max_size and size > self.policy.max_size:
                        continue
                except Exception:
                    continue
            if self.policy.modified_after or self.policy.modified_before:
                try:
                    mtime = datetime.fromtimestamp(p.stat().st_mtime)
                    if self.policy.modified_after and mtime < self.policy.modified_after:
                        continue
                    if self.policy.modified_before and mtime > self.policy.modified_before:
                        continue
                except Exception:
                    continue
            result.append(p)
        return result

    def files(self) -> List[Path]:
        """정책 기반 파일 목록 반환"""
        paths = [p for p in self._scan() if p.is_file()]
        return self._filter(paths)

    def dirs(self) -> List[Path]:
        """정책 기반 디렉터리 목록 반환"""
        paths = [p for p in self._scan() if p.is_dir()]
        return self._filter(paths)

    def all(self) -> List[Path]:
        """정책 기반 전체 항목 반환 (파일 + 디렉터리)"""
        return self._filter(self._scan())

    def _scan(self) -> List[Path]:
        return list(self.root.rglob('*')) if self.policy.recursive else list(self.root.iterdir())

    def __str__(self):
        return f"<FSOExplorer root={self.root}>"
