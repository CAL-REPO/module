# -*- coding: utf-8 -*-
# log_utils/policy.py - 로그 정책 정의 (FSO 통합 + 회전/보존/압축 + Notifier 정책 지원)

from __future__ import annotations
from pathlib import Path
from typing import Optional, Literal
from pydantic import BaseModel, Field, model_validator

from fso_utils.policy import (
    FSONamePolicy,
    FSOOpsPolicy,
    ExistencePolicy,
)
from fso_utils.ops import FSOOps
import path_utils

class NotifierPolicy(BaseModel):
    """
    ✅ 외부 알림 설정 정책
    - LogNotifier의 설정값을 캡슐화
    """
    enabled: bool = Field(False, description="외부 알림 기능 활성화 여부")
    email_host: Optional[str] = None
    email_port: int = 587
    email_sender: Optional[str] = None
    email_password: Optional[str] = None
    email_recipient: Optional[str] = None
    slack_webhook_url: Optional[str] = None

class LogPolicy(BaseModel):
    """
    ✅ 통합 로그 정책(LogPolicy)
    - FSO 기반 파일/디렉터리 관리
    - 회전(rotation), 보존(retention), 압축(compression), 외부 알림(Notifier) 통합 관리
    """

    # -----------------------------
    # ⚙️ 로깅 기본 설정
    # -----------------------------
    enabled: bool = Field(True, description="로그 활성화 여부")
    level: str = Field("INFO", description="로그 레벨")
    encoding: str = Field("utf-8", description="로그 파일 인코딩")
    diagnose: bool = Field(True, description="예외 발생 시 진단 출력 여부")
    backtrace: bool = Field(True, description="traceback 상세 출력 여부")
    enqueue: bool = Field(True, description="멀티프로세스 안전 큐 사용 여부")

    # -----------------------------
    # 📁 파일/디렉터리 정책
    # -----------------------------
    base_dir: Path = Field(default_factory=path_utils.downloads, description="로그 기본 디렉터리")
    dir_name: str = Field("Default", description="로그 디렉터리 이름")

    # -----------------------------
    # 🧱 FSO 정책
    # -----------------------------
    file_name_policy: FSONamePolicy = Field(
        default_factory=lambda: FSONamePolicy(
            as_type="file",
            name="log",
            extension="log",
            tail_mode="datetime_counter",
            ensure_unique=True,
        )
    )

    fso_policy: FSOOpsPolicy = Field(
        default_factory=lambda: FSOOpsPolicy(
            as_type="file",
            exist=ExistencePolicy(create_if_missing=True)
        )
    )

    # -----------------------------
    # ♻️ 파일 회전 / 보존 / 압축
    # -----------------------------
    rotation: str = Field("1 day", description="로그 회전 주기")
    retention: Optional[str | int] = Field(None, description="로그 보존 기간 또는 개수")
    compression: Optional[Literal["zip", "tar", "gz", "bz2", "xz", "lzma", None]] = Field(
        None, description="로그 파일 회전 시 적용할 압축 형식"
    )

    # -----------------------------
    # 🔔 외부 알림 정책
    # -----------------------------
    use_notifier: bool = Field(False, description="LogNotifier 자동 활성화 여부")
    notifier_policy: NotifierPolicy = Field(
        default_factory=lambda: NotifierPolicy(
            enabled=False 
        )
    )

    # -----------------------------
    # ✅ 후처리 검증
    # -----------------------------
    @model_validator(mode="after")
    def validate_dir(self):
        if self.enabled:
            dir_path = self.dir_path
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
        return self

    # -----------------------------
    # 🧭 유틸리티 프로퍼티
    # -----------------------------
    @property
    def dir_path(self) -> Path:
        """최종 로그 디렉터리 경로 반환 (자동 생성 포함)"""
        ops = FSOOps(
            self.base_dir / self.dir_name,
            policy=FSOOpsPolicy(as_type="dir", exist=ExistencePolicy(create_if_missing=True)),
        )
        return ops.path
