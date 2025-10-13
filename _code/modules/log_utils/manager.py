# -*- coding: utf-8 -*-
# log_utils/manager.py - 정책 기반 Loguru 로거 매니저

from __future__ import annotations
from pathlib import Path
from typing import Optional
from loguru import logger

from .policy import LogPolicy
from .fso_builder import LogFSOBuilder


class DummyLogger:
    """로그 비활성화 시 사용하는 Null Object logger"""
    def __getattr__(self, _):
        return lambda *_, **__: None


class LogManager:
    """
    ✅ 정책 기반 Loguru 매니저
    - LogPolicy를 기반으로 로그 경로, 회전, 보존, 압축 설정 자동화
    """

    def __init__(
        self,
        name: str,
        *,
        policy: Optional[LogPolicy] = None,
    ):
        self.name = name
        self.policy = policy or LogPolicy() # pyright: ignore[reportCallIssue]
        self._configured = False
        self.log_file: Optional[Path] = None

    def setup(self):
        """
        로거 초기화 및 설정 적용
        - 정책에 따라 로그 파일 자동 생성
        - rotation, retention, compression 반영
        """
        if not self.policy.enabled:
            return DummyLogger()

        if self._configured:
            return logger

        # -----------------------------
        # 1️⃣ 로그 경로 자동 생성
        # -----------------------------
        builder = LogFSOBuilder(self.policy)
        self.log_file = builder.prepare()

        # -----------------------------
        # 2️⃣ Loguru 초기 설정
        # -----------------------------
        logger.remove()  # 기존 핸들러 제거

        # 콘솔 출력 추가 (기본)
        logger.add(lambda msg: print(msg, end=""), level=self.policy.level)

        # -----------------------------
        # 3️⃣ 파일 핸들러 설정
        # -----------------------------
        if self.log_file:
            logger.add(
                str(self.log_file),
                level=self.policy.level,
                encoding=self.policy.encoding,
                rotation=self.policy.rotation,
                retention=self.policy.retention,
                compression=self.policy.compression,
                enqueue=self.policy.enqueue,
                backtrace=self.policy.backtrace,
                diagnose=self.policy.diagnose,
            )

        self._configured = True
        return logger
