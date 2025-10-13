# -*- coding: utf-8 -*-
# fso_utils/policy.py - 파일 시스템 및 이름 정책 정의

from __future__ import annotations
from typing import Literal, Optional, Sequence, List
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel, Field, model_validator


# -------------------------------------------------------------------------
# 📘 파일/디렉터리 이름 정책 (통합 버전)
# -------------------------------------------------------------------------
class FSONamePolicy(BaseModel):
    """
    파일 또는 디렉터리 이름 생성 정책
    - as_type: "file" | "dir" (기본: "file")
    - 파일인 경우 extension 필수 검증 포함
    """

    as_type: Literal["file", "dir"] = Field("file", description="이름 생성 대상 타입")
    prefix: Optional[str] = None
    name: str
    suffix: Optional[str] = None
    tail: Optional[str] = None
    extension: Optional[str] = None

    # tail 관련 정책
    delimiter: str = "_"
    tail_mode: Optional[Literal["date", "datetime", "counter", "datetime_counter"]] = None
    date_format: str = "%Y-%m-%d"
    counter_width: int = 3
    auto_expand: bool = True
    tail_suffix: Optional[str] = None

    # 출력 제어
    sanitize: bool = True
    case: Literal["lower", "upper", "keep"] = "keep"
    ensure_unique: bool = False

    # -----------------------------
    # 🔍 Pydantic validation
    # -----------------------------
    @model_validator(mode="after")
    def validate_policy(self):
        # 파일일 경우 확장자 필수
        if self.as_type == "file" and not self.extension:
            raise ValueError(
                f"파일 이름 생성 시 'extension'은 필수입니다. (name='{self.name}')"
            )

        # 디렉터리일 경우 확장자 지정 금지 권장 (허용하되 경고용)
        if self.as_type == "dir" and self.extension:
            import warnings
            warnings.warn(
                f"[FSONamePolicy] 'dir' 타입에서 extension이 지정되었습니다. "
                f"확장자는 무시됩니다. (name='{self.name}')",
                UserWarning,
            )
        return self


# -------------------------------------------------------------------------
# 📘 파일 존재/확장자 등 기존 정책
# -------------------------------------------------------------------------
class ExistencePolicy(BaseModel):
    must_exist: bool = False
    create_if_missing: bool = False
    overwrite: bool = False


class FileExtensionPolicy(BaseModel):
    require_ext: bool = False
    default_ext: Optional[str] = None
    allowed_exts: Optional[Sequence[str]] = None


class FSOOpsPolicy(BaseModel):
    as_type: Literal["file", "dir"] = "file"
    exist: ExistencePolicy = ExistencePolicy()
    ext: FileExtensionPolicy = FileExtensionPolicy()

    def apply_to(self, raw: Path) -> Path:
        path = raw

        # 확장자 처리
        if self.as_type == "file":
            if not path.suffix:
                if self.ext.require_ext:
                    raise ValueError(f"파일 경로에 확장자가 필요합니다: {path}")
                if self.ext.default_ext:
                    path = path.with_suffix(self.ext.default_ext)

        path = path.resolve()

        # 존재성 정책 적용
        if self.exist.must_exist and not path.exists():
            raise FileNotFoundError(f"경로가 존재하지 않습니다: {path}")

        if not path.exists() and self.exist.create_if_missing:
            if self.as_type == "dir":
                path.mkdir(parents=True, exist_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)

        return path


class FSOIOPolicy(BaseModel):
    encoding: str = Field("utf-8", description="텍스트 파일 입출력 기본 인코딩")
    atomic_writes: bool = Field(True, description="파일 쓰기 시 원자적 교체 수행 여부")
    reader: FSOOpsPolicy = Field(
        default_factory=lambda: FSOOpsPolicy(as_type="file", exist=ExistencePolicy(must_exist=True))
    )
    writer: FSOOpsPolicy = Field(
        default_factory=lambda: FSOOpsPolicy(as_type="file", exist=ExistencePolicy(create_if_missing=True))
    )

    def copy_with(self, **updates) -> "FSOIOPolicy":
        return self.model_copy(update=updates)


class FSOExplorerPolicy(BaseModel):
    recursive: bool = False
    allowed_exts: Optional[List[str]] = None
    name_patterns: Optional[List[str]] = None
    min_size: Optional[int] = None
    max_size: Optional[int] = None
    modified_after: Optional[datetime] = None
    modified_before: Optional[datetime] = None
