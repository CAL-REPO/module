# -*- coding: utf-8 -*-
"""
Source loading utilities for the translation pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from modules.fso_utils.core.io import FileReader

from ..core.policy import SourcePolicy


@dataclass
class SourcePayload:
    texts: List[str]
    source_path: Optional[Path]


class TextSourceLoader:
    """Load translation texts from inline lists or external files."""

    def __init__(self, policy: SourcePolicy):
        self.policy = policy

    def load(self) -> SourcePayload:
        texts = list(self.policy.text)
        source_path: Optional[Path] = None

        if self.policy.file_path:
            source_path = Path(self.policy.file_path).expanduser()

        if not texts and source_path:
            try:
                reader = FileReader(source_path)
                content = reader.read_text()
                texts = [line.strip() for line in content.splitlines() if line.strip()]
            except FileNotFoundError:
                texts = []

        return SourcePayload(texts=texts, source_path=source_path)
