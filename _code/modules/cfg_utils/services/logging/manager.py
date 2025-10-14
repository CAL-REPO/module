# -*- coding: utf-8 -*-
# cfg_utils/services/logging/manager.py
from __future__ import annotations
from loguru import logger
from pathlib import Path
from cfg_utils.services.logging.policy import LogPolicy

class LogManager:
    def __init__(self, name: str, policy: LogPolicy):
        self.name = name
        self.policy = policy
        self._configure_logger()

    def _configure_logger(self):
        logger.remove()
        for sink in self.policy.sink:
            if sink.console:
                logger.add(lambda msg: print(msg, end=""),
                           level=self.policy.level,
                           format=self.policy.format,
                           enqueue=True)
            if sink.file:
                file_path = Path(sink.file)
                file_path.parent.mkdir(parents=True, exist_ok=True)
                logger.add(file_path,
                           rotation=self.policy.rotation,
                           retention=self.policy.retention,
                           level=self.policy.level,
                           format=self.policy.format,
                           enqueue=True)
        if not any(s.file for s in self.policy.sink):
            path = self.policy.build_path()
            logger.add(path,
                       rotation=self.policy.rotation,
                       retention=self.policy.retention,
                       level=self.policy.level,
                       format=self.policy.format,
                       enqueue=True)
        self.logger = logger

    def get_logger(self):
        return self.logger
