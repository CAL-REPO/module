# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from typing import Optional
import asyncio

from ..core.interfaces import IFileSaver, IPathBuilderPort
from ..core.policy import FSONamePolicy, FSOOpsPolicy, ExistencePolicy
from ..core.path_builder import FSOPathBuilder

class LocalFileSaver(IFileSaver):
    async def save_bytes(self, path: Path, data: bytes) -> None:
        await asyncio.to_thread(path.write_bytes, data)

    async def save_text(self, path: Path, text: str, encoding: str = "utf-8") -> None:
        await asyncio.to_thread(path.write_text, text, encoding=encoding)

class FSOPathBuilderAdapter(IPathBuilderPort):
    def build_path(
        self,
        base_dir: Path,
        sub_dir: Optional[str],
        name_template: str,
        ensure_unique: bool,
        name: str,
        extension: str,
        kind: str,
    ) -> Path:
        target_dir = base_dir / (sub_dir or kind)
        # name is already resolved by caller (e.g., name_template + indices)
        name_policy = FSONamePolicy(as_type="file", name=name, extension=extension, ensure_unique=ensure_unique) # pyright: ignore[reportCallIssue]
        ops_policy = FSOOpsPolicy(as_type="file", exist=ExistencePolicy(create_if_missing=True)) # pyright: ignore[reportCallIssue]
        builder = FSOPathBuilder(target_dir, name_policy, ops_policy)
        return builder()
