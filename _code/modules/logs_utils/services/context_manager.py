# -*- coding: utf-8 -*-
# logs_utils/services/context_manager.py

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Union
from pydantic import BaseModel
from loguru import logger
from logs_utils.services.manager import LogManager


class LogContextManager:
    def __init__(
        self,
        cfg_like: Union[BaseModel, Path, str, dict, list, None] = None,
        *,
        policy: Optional[Any] = None,
        **overrides: Any
    ):
        self.manager: Optional[LogManager] = None
        self._cfg_like = cfg_like
        self._policy = policy
        self._overrides = overrides
        self._active = False
    
    def __enter__(self):
        self.manager = LogManager(self._cfg_like, policy=self._policy, **self._overrides)
        self._active = True
        app_name = self.manager.config.name
        self.manager.logger.info(f"[{app_name}] Logger started.")
        return self.manager.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self._active or not self.manager:
            return
        app_name = self.manager.config.name
        if exc_type:
            self.manager.logger.exception(f"[{app_name}] Exception: {exc_val}")
        self.manager.logger.info(f"[{app_name}] Logger closed.")
        self.manager.remove_handlers()
        self._active = False
        self.manager = None
