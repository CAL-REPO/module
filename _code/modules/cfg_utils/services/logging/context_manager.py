# -*- coding: utf-8 -*-
# cfg_utils/services/logging/context.py
from __future__ import annotations
import asyncio
from cfg_utils.services.logging.manager import LogManager
from cfg_utils.services.logging.policy import LogPolicy

class LogContextManager:
    def __init__(self, name: str, policy: LogPolicy):
        self.name = name
        self.policy = policy
        self.manager = None
        self.logger = None

    def __enter__(self):
        self.manager = LogManager(self.name, self.policy)
        self.logger = self.manager.get_logger()
        self.logger.info(f"[{self.name}] Logger started.")
        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.logger.exception(f"[{self.name}] Exception: {exc_val}") # pyright: ignore[reportOptionalMemberAccess]
        self.logger.info(f"[{self.name}] Logger closed.") # pyright: ignore[reportOptionalMemberAccess]
        self.manager = None
        self.logger = None

    async def __aenter__(self):
        loop = asyncio.get_event_loop()
        self.manager = await loop.run_in_executor(None, LogManager, self.name, self.policy)
        self.logger = self.manager.get_logger()
        self.logger.info(f"[{self.name}] Async logger started.")
        return self.logger

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.logger.exception(f"[{self.name}] Async Exception: {exc_val}") # pyright: ignore[reportOptionalMemberAccess]
        self.logger.info(f"[{self.name}] Async logger closed.") # pyright: ignore[reportOptionalMemberAccess]
        self.manager = None
        self.logger = None
