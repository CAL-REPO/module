# -*- coding: utf-8 -*-
# cfg_utils/services/logging/loader.py
from __future__ import annotations
import yaml
from pathlib import Path
from cfg_utils.services.logging.policy import LogPolicy, LogSinkPolicy

class LogPolicyLoader:
    @staticmethod
    def from_yaml(path: str | Path) -> LogPolicy:
        path = Path(path)
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        sinks = [LogSinkPolicy(**s) for s in data.get("sink", [])] if "sink" in data else [LogSinkPolicy(console=True)]
        data["sink"] = sinks
        return LogPolicy(**data)
