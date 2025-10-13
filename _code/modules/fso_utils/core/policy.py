# -*- coding: utf-8 -*-
# fso_utils/core/policy.py

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence

from pydantic import BaseModel, Field


class FSONamePolicy(BaseModel):
    as_type: str = Field("file", description="Target type: file or dir")
    prefix: Optional[str] = None
    name: str = Field("", description="Base name without extension")
    suffix: Optional[str] = None
    tail: Optional[str] = None
    extension: Optional[str] = None

    delimiter: str = Field("_", description="Delimiter when joining parts")
    tail_mode: Optional[str] = Field(
        None, description="Auto tail mode: date|datetime|counter|datetime_counter"
    )
    date_format: str = Field("%Y-%m-%d", description="strftime pattern for date tails")
    counter_width: int = Field(3, ge=1)
    auto_expand: bool = Field(True, description="Allow counter wider than counter_width")
    tail_suffix: Optional[str] = None

    sanitize: bool = Field(True, description="Remove illegal filesystem characters")
    case: str = Field("keep", description="Name casing: lower|upper|keep")
    ensure_unique: bool = Field(True, description="Avoid overwriting existing files")


class ExistencePolicy(BaseModel):
    must_exist: bool = Field(False, description="Require path to exist")
    create_if_missing: bool = Field(False, description="Create parent directories if missing")
    overwrite: bool = Field(False, description="Allow overwrite when creating files")


class FileExtensionPolicy(BaseModel):
    require_ext: bool = Field(False, description="Require extension on file paths")
    default_ext: Optional[str] = Field(None, description="Extension to append when absent")
    allowed_exts: Optional[Sequence[str]] = Field(None, description="Whitelist of extensions")


class FSOOpsPolicy(BaseModel):
    as_type: str = Field("file", description="file or dir")
    exist: ExistencePolicy = Field(default_factory=ExistencePolicy) # pyright: ignore[reportArgumentType]
    ext: FileExtensionPolicy = Field(default_factory=FileExtensionPolicy) # pyright: ignore[reportArgumentType]

    def apply_to(self, raw: Path) -> Path:
        path = raw

        if self.as_type == "file":
            if not path.suffix and self.ext.default_ext:
                ext = self.ext.default_ext
                if ext and not ext.startswith('.'):
                    ext = f'.{ext}'
                path = path.with_suffix(ext or '')
            elif self.ext.require_ext and not path.suffix:
                raise ValueError(f"파일 경로에 확장자가 필요합니다: {path}")
            if self.ext.allowed_exts and path.suffix not in self.ext.allowed_exts:
                raise ValueError(f"허용되지 않은 확장자: {path.suffix}")

        path = path.resolve()

        if self.exist.must_exist and not path.exists():
            raise FileNotFoundError(f"경로가 존재하지 않습니다: {path}")

        if not path.exists() and self.exist.create_if_missing:
            if self.as_type == "dir":
                path.mkdir(parents=True, exist_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)

        return path


class FSOIOPolicy(BaseModel):
    encoding: str = Field("utf-8", description="Default text encoding")
    atomic_writes: bool = Field(True, description="Write files atomically")
    reader: FSOOpsPolicy = Field(
        default_factory=lambda: FSOOpsPolicy(as_type="file", exist=ExistencePolicy(must_exist=True)) # pyright: ignore[reportCallIssue]
    )
    writer: FSOOpsPolicy = Field(
        default_factory=lambda: FSOOpsPolicy(as_type="file", exist=ExistencePolicy(create_if_missing=True)) # pyright: ignore[reportCallIssue]
    )


class FSOExplorerPolicy(BaseModel):
    recursive: bool = Field(False, description="Recurse into subdirectories")
    allowed_exts: Optional[List[str]] = None
    name_patterns: Optional[List[str]] = None
    min_size: Optional[int] = None
    max_size: Optional[int] = None
    modified_after: Optional[datetime] = None
    modified_before: Optional[datetime] = None
