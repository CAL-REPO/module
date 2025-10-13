# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Protocol, Optional
from pathlib import Path

class IPathBuilderPort(Protocol):
    def build_path(
        self,
        base_dir: Path,
        sub_dir: Optional[str],
        name_template: str,
        ensure_unique: bool,
        name: str,
        extension: str,
        kind: str,
    ) -> Path: ...

class IFileSaver(Protocol):
    async def save_bytes(self, path: Path, data: bytes) -> None: ...
    async def save_text(self, path: Path, text: str, encoding: str = "utf-8") -> None: ...
