# structured_io/base/base_parser.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from pathlib import Path

class BaseParser(ABC):
    def __init__(self, policy, context: dict | None = None):
        self.policy = policy
        self.context = context or {}

    @abstractmethod
    def parse(self, text: str, base_path: Path | None = None) -> Any:
        ...
