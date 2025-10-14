# -*- coding: utf-8 -*-
# cfg_utils/services/logging/policy.py
from __future__ import annotations
from pydantic import BaseModel, Field
from pathlib import Path
from typing import Optional, List, Literal

class LogSinkPolicy(BaseModel):
    file: Optional[str] = None
    console: bool = False

class LogPolicy(BaseModel):
    dir_name: str = "logs"
    rotation: str = "5 MB"
    retention: str = "7 days"
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    format: str = "[{time:YYYY-MM-DD HH:mm:ss}] | {level:<8} | {message}"
    sink: List[LogSinkPolicy] = Field(default_factory=lambda: [LogSinkPolicy(console=True)])

    def build_path(self) -> Path:
        path = Path(self.dir_name)
        path.mkdir(parents=True, exist_ok=True)
        return path / "runtime.log"
