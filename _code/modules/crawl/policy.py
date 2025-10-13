# -*- coding: utf-8 -*-
# crawl/policy.py
from __future__ import annotations
from pathlib import Path
from typing import Optional, Sequence, Literal, Any, Dict
from pydantic import BaseModel, Field, model_validator
from firefox.config import FirefoxConfig
from fso_utils.policy import FileExtensionPolicy

# =======================================================
# 1️⃣ RetryPolicy — 공통 정책 (DownloadPolicy, SessionPolicy 등에서 재사용)
# =======================================================
class RetryPolicy(BaseModel):
    """네트워크/IO 재시도 정책"""
    retries: int = Field(3, ge=0, description="재시도 횟수")
    backoff: float = Field(1.0, ge=0.0, description="백오프 계수(초)")

# =======================================================
# 2️⃣ SessionPolicy — HTTP 헤더 및 연결 관련 정책
# =======================================================
class SessionPolicy(BaseModel):
    referer: Optional[str] = None
    accept_context: Optional[str] = None
    accept_encoding: Optional[str] = None
    retry: RetryPolicy = Field(default_factory=RetryPolicy) # pyright: ignore[reportArgumentType]

# =======================================================
# 3️⃣ DownloadPolicy — 세션, 재시도, 최소크기, ContentType 검증
# =======================================================
class DownloadPolicy(BaseModel):
    session: Optional[SessionPolicy] = Field(default=None)
    retry: RetryPolicy = Field(default_factory=RetryPolicy) # pyright: ignore[reportArgumentType]
    min_size: int = Field(default=1024)
    allow_content_types: Optional[Sequence[str]] = Field(default=None)
    timeout: float = Field(default=15.0)

    @model_validator(mode="after")
    def inherit_from_session(self):
        """SessionPolicy.retry 존재 시 상속"""
        if self.session and self.session.retry:
            self.retry = self.session.retry
        return self

# =======================================================
# 4️⃣ SavePolicy — 이미지/텍스트 저장 정책
# =======================================================
class ImageSourcePolicy(BaseModel):
    save_dir: Path = Field(default_factory=lambda: Path.home() / "Downloads" / "CRAWL_OUTPUT")
    name_template: str = "{section}_{key}_{idx}"
    format: Literal["JPEG", "PNG", "WEBP"] = "JPEG"
    quality: int = Field(default=85, ge=1, le=100)
    exif: bool = Field(default=False)
    max_width: int = Field(default=4096, ge=1)
    max_height: int = Field(default=4096, ge=1)

class TextSourcePolicy(BaseModel):
    save_dir: Path = Field(default_factory=lambda: Path.home() / "Downloads" / "CRAWL_OUTPUT")
    filename_template: str = "{section}.txt"
    mode: Literal["append", "overwrite"] = "overwrite"
    encoding: str = "utf-8"

class SavePolicy(BaseModel):
    image: Optional[ImageSourcePolicy] = None
    text: Optional[TextSourcePolicy] = None

    @model_validator(mode="after")
    def validate_sources(self):
        if not (self.image or self.text):
            raise ValueError("SavePolicy: image 또는 text 정책 중 하나는 필요합니다.")
        return self
