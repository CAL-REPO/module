# -*- coding: utf-8 -*-
# crawl_refactor/models.py

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Literal, Optional, List

ItemKind = Literal["image", "text", "file"]


@dataclass(slots=True)
class NormalizedItem:
    kind: ItemKind
    value: Any
    section: str = "default"
    name_hint: Optional[str] = None
    extension: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    record_index: int = 0
    item_index: int = 0


@dataclass(slots=True)
class SavedArtifact:
    path: Path
    item: NormalizedItem
    status: Literal["saved", "skipped", "failed"] = "saved"
    detail: Optional[str] = None


@dataclass(slots=True)
class SaveSummary:
    artifacts: Dict[str, List[SavedArtifact]]

    def flatten(self) -> List[SavedArtifact]:
        return [artifact for group in self.artifacts.values() for artifact in group]

    def __getitem__(self, kind: ItemKind) -> List[SavedArtifact]:
        return self.artifacts.get(kind, [])
