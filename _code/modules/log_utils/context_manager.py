# -*- coding: utf-8 -*-
# log_utils/context_manager.py - LogManager 기반 컨텍스트 매니저 (자동 Notifier 생성 지원)

from __future__ import annotations
import traceback
from typing import Optional

from .manager import LogManager, DummyLogger
from .policy import LogPolicy
from .notifier import LogNotifier


class LogContextManager:
    """
    ✅ LogManager 컨텍스트 매니저 (자동 Notifier 연동)
    - with 블록 진입 시 자동 setup()
    - DummyLogger 대응 (비활성화 시에도 에러 없이 작동)
    - LogPolicy에 설정된 notifier_policy 자동 반영
    - 예외 발생 시 traceback + 외부 알림 자동 전송
    """

    def __init__(
        self,
        name: str,
        policy: Optional[LogPolicy] = None,
    ):
        self.name = name
        self.policy = policy or LogPolicy() # pyright: ignore[reportCallIssue]
        self.manager = LogManager(name, policy=self.policy)
        self.log = None

        # ✅ Notifier 자동 생성
        self.use_notifier = self.policy.use_notifier and self.policy.notifier_policy.enabled
        self.notifier: Optional[LogNotifier] = None

        if self.use_notifier:
            try:
                # LogNotifier 자동 생성
                self.notifier = LogNotifier(**self.policy.notifier_policy.model_dump())
            except Exception as e:
                print(f"[LogContextManager] Notifier 초기화 실패: {e}")
                self.use_notifier = False

    def __enter__(self):
        """with 블록 진입 시 자동 초기화"""
        self.log = self.manager.setup()

        if hasattr(self.log, "info"):
            self.log.info(f"[{self.name}] Logging started.")
        return self.log

    def __exit__(self, exc_type, exc_val, exc_tb):
        """with 블록 종료 시 안전한 정리 수행 (예외 포함)"""
        if not self.log:
            return

        try:
            if exc_type:
                tb_text = ''.join(traceback.format_exception(exc_type, exc_val, exc_tb))
                if hasattr(self.log, "error"):
                    self.log.error(f"[{self.name}] Exception occurred: {exc_val}\n{tb_text}")

                # ✅ Notifier 자동 전송
                if self.use_notifier and self.notifier:
                    try:
                        self.notifier.notify(self.name, exc_type, exc_val, exc_tb)
                    except Exception as e:
                        print(f"[LogContextManager] Notifier 실행 실패: {e}")

            if hasattr(self.log, "info"):
                self.log.info(f"[{self.name}] Logging finished.")
        except Exception as e:
            print(f"[LogContextManager] Cleanup failed: {e}")
