# -*- coding: utf-8 -*-
# firefox/config.py

from __future__ import annotations
from typing import Optional, Tuple
from pathlib import Path
from pydantic import Field, BaseModel, field_validator, model_validator

from log_utils import LogPolicy, LogManager
# FSONamePolicy is provided by fso_utils.core.policy and re‑exported at the
# top level.  Use the top‑level import to avoid missing module errors.
from fso_utils import FSONamePolicy


# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------
def _default_log_policy() -> LogPolicy:
    """Firefox 전용 기본 로그 정책."""
    file_policy = FSONamePolicy(
        as_type="file",
        name="firefox",
        suffix="driver",
        tail_mode="datetime_counter",
        tail_suffix="run",
        extension="log",
        ensure_unique=True,
    )
    return LogPolicy(dir_name="Firefox", file_name_policy=file_policy) # pyright: ignore[reportCallIssue]


# -------------------------------------------------------------------------
# Firefox 설정 모델
# -------------------------------------------------------------------------
class FirefoxConfig(BaseModel):
    driver_path: Optional[Path] = None
    binary_path: Optional[Path] = None
    profile_path: Optional[Path] = None
    headless: bool = False
    window_size: Tuple[int, int] = (1440, 900)
    log_policy: LogPolicy = Field(default_factory=_default_log_policy)  # pyright: ignore[reportCallIssue]

    # 브라우저 설정
    accept_languages: Optional[str] = None
    user_agent: Optional[str] = None
    dom_enabled: bool = False
    resist_fingerprint_enabled: bool = True
    session_path: Optional[Path] = None

    @field_validator("window_size", mode="before")
    @classmethod
    def validate_window_size(cls, v):
        if isinstance(v, (list, tuple)) and len(v) == 2:
            return (int(v[0]), int(v[1]))
        raise ValueError("window_size must be a tuple of two integers")

    @model_validator(mode="after")
    def validate_paths(self):
        # ------------------------------
        # 🔹 경로 유효성 검증
        # ------------------------------
        if self.driver_path and not self.driver_path.is_file():
            raise ValueError(f"Invalid driver_path: {self.driver_path}")
        if self.binary_path and not self.binary_path.is_file():
            raise ValueError(f"Invalid binary_path: {self.binary_path}")
        if self.profile_path and not self.profile_path.is_dir():
            raise ValueError(f"Invalid profile_path: {self.profile_path}")

        if self.session_path:
            self.session_path.parent.mkdir(parents=True, exist_ok=True)

        return self

    # ------------------------------
    # 🔹 로거 매니저 초기화 헬퍼
    # ------------------------------
    def create_logger(self) -> LogManager:
        """현재 설정 기반 LogManager 생성"""
        return LogManager("firefox", policy=self.log_policy)
