# -*- coding: utf-8 -*-
# fso_utils/core/io.py

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from data_utils.core.types import PathLike

from .ops import FSOOps
from .policy import FSOOpsPolicy, FSOIOPolicy, ExistencePolicy


class BaseFileHandler:
    def __init__(
        self,
        path: PathLike,
        policy: FSOOpsPolicy,
        encoding: str = "utf-8",
        *,
        require_exists: bool = True,
    ):
        self.file = FSOOps(path, policy)
        self.encoding = encoding
        self._require_exists = require_exists
        self._validate()

    def _validate(self):
        if not self._require_exists:
            return
        if not self.file.path.exists():
            raise FileNotFoundError(f"파일이 존재하지 않습니다: {self.file.path}")
        if not self.file.path.is_file():
            raise FileNotFoundError(f"파일이 아니거나 접근할 수 없습니다: {self.file.path}")


class FileReader(BaseFileHandler):
    def __init__(
        self,
        path: PathLike,
        ops_policy: Optional[FSOOpsPolicy] = None,
        *,
        encoding: Optional[str] = None,
        io_policy: Optional[FSOIOPolicy] = None,
    ):
        self.io_policy = io_policy or FSOIOPolicy()
        effective_policy = ops_policy or self.io_policy.reader
        text_encoding = encoding or self.io_policy.encoding
        super().__init__(path, effective_policy, text_encoding, require_exists=True)

    def read_text(self) -> str:
        return self.file.path.read_text(encoding=self.encoding)

    def read_bytes(self) -> bytes:
        return self.file.path.read_bytes()


class FileWriter(BaseFileHandler):
    def __init__(
        self,
        path: PathLike,
        *,
        encoding: Optional[str] = None,
        atomic: Optional[bool] = None,
        ops_policy: Optional[FSOOpsPolicy] = None,
        io_policy: Optional[FSOIOPolicy] = None,
    ):
        self.io_policy = io_policy or FSOIOPolicy()
        effective_policy = ops_policy or self.io_policy.writer
        text_encoding = encoding or self.io_policy.encoding
        super().__init__(path, effective_policy, text_encoding, require_exists=False)
        self.atomic = self.io_policy.atomic_writes if atomic is None else atomic

    def write_text(self, text: str) -> Path:
        p = self.file.path
        if self.atomic:
            tmp = p.with_suffix(p.suffix + ".part")
            tmp.write_text(text, encoding=self.encoding)
            os.replace(tmp, p)
        else:
            p.write_text(text, encoding=self.encoding)
        return p

    def write_bytes(self, data: bytes) -> Path:
        p = self.file.path
        if self.atomic:
            tmp = p.with_suffix(p.suffix + ".part")
            tmp.write_bytes(data)
            os.replace(tmp, p)
        else:
            p.write_bytes(data)
        return p


class JsonFileIO:
    def __init__(
        self,
        path: PathLike,
        *,
        encoding: Optional[str] = None,
        ops_policy: Optional[FSOOpsPolicy] = None,
        io_policy: Optional[FSOIOPolicy] = None,
    ):
        self.io_policy = io_policy or FSOIOPolicy()
        effective_encoding = encoding or self.io_policy.encoding
        reader_policy = ops_policy or self.io_policy.reader
        writer_policy = ops_policy or self.io_policy.writer
        self._reader = FileReader(path, encoding=effective_encoding, ops_policy=reader_policy, io_policy=self.io_policy)
        self._writer = FileWriter(path, encoding=effective_encoding, ops_policy=writer_policy, io_policy=self.io_policy)

    def read(self) -> Any:
        return json.loads(self._reader.read_text())

    def write(self, data: Any) -> Path:
        return self._writer.write_text(json.dumps(data, ensure_ascii=False, indent=2))


class BinaryFileIO:
    def __init__(
        self,
        path: PathLike,
        *,
        ops_policy: Optional[FSOOpsPolicy] = None,
        io_policy: Optional[FSOIOPolicy] = None,
    ):
        self.io_policy = io_policy or FSOIOPolicy()
        reader_policy = ops_policy or self.io_policy.reader
        writer_policy = ops_policy or self.io_policy.writer
        self._reader = FileReader(path, ops_policy=reader_policy, io_policy=self.io_policy)
        self._writer = FileWriter(path, ops_policy=writer_policy, io_policy=self.io_policy)

    def read(self) -> bytes:
        return self._reader.read_bytes()

    def write(self, data: bytes) -> Path:
        return self._writer.write_bytes(data)
