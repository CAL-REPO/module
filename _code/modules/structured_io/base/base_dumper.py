# structured_io/base/base_dumper.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any

class BaseDumper(ABC):
    def __init__(self, policy):
        self.policy = policy

    @abstractmethod
    def dump(self, data: Any) -> str:
        ...
