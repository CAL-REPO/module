# -*- coding: utf-8 -*-
# fso_utils/io.py - 파일 입출력 클래스 정의

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional, Any

from data_utils.types import PathLike
from .ops import FSOOps
from .policy import FSOOpsPolicy, ExistencePolicy
from yaml_utils import YamlParser, YamlDumper, YamlParserPolicy  # 구조적 분리 반영


class BaseFileHandler:
    def __init__(self, path: PathLike, policy: FSOOpsPolicy, encoding: str = "utf-8"):
        self.file = FSOOps(path, policy)
        self.encoding = encoding
        self._validate()

    def _validate(self):
        if not self.file.path.is_file():
            raise FileNotFoundError(f"파일이 존재하지 않거나 파일이 아닙니다: {self.file.path}")


class FileReader(BaseFileHandler):
    def read_text(self) -> str:
        return self.file.path.read_text(encoding=self.encoding)

    def read_bytes(self) -> bytes:
        return self.file.path.read_bytes()


class FileWriter(BaseFileHandler):
    def __init__(
        self,
        path: PathLike,
        *,
        encoding: str = "utf-8",
        atomic: bool = True,
        policy: FSOOpsPolicy = FSOOpsPolicy(as_type="file", exist=ExistencePolicy(create_if_missing=True))
    ):
        self.atomic = atomic
        super().__init__(path, policy, encoding)

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


# 파일 형식별 IO 클래스들

class JsonFileIO:
    def __init__(self, path: PathLike, *, encoding: str = "utf-8", policy: Optional[FSOOpsPolicy] = None):
        self._reader = FileReader(path, policy=policy or FSOOpsPolicy(exist=ExistencePolicy(must_exist=True)), encoding=encoding)
        self._writer = FileWriter(path, policy=policy or FSOOpsPolicy(exist=ExistencePolicy(create_if_missing=True)), encoding=encoding)

    def read(self) -> Any:
        return json.loads(self._reader.read_text())

    def write(self, data: Any) -> Path:
        return self._writer.write_text(json.dumps(data, ensure_ascii=False, indent=2))


class YamlFileIO:
    def __init__(
        self,
        path: PathLike,
        *,
        encoding: str = "utf-8",
        policy: Optional[FSOOpsPolicy] = None,
        yaml_policy: Optional[YamlParserPolicy] = None
    ):
        self._reader = FileReader(path, policy=policy or FSOOpsPolicy(exist=ExistencePolicy(must_exist=True)), encoding=encoding)
        self._writer = FileWriter(path, policy=policy or FSOOpsPolicy(exist=ExistencePolicy(create_if_missing=True)), encoding=encoding)
        self.policy = yaml_policy or YamlParserPolicy.default()  # type: ignore
        self.parser = YamlParser(policy=self.policy)
        self.dumper = YamlDumper(policy=self.policy)

    def read(self) -> Any:
        return self.parser.parse(self._reader.read_text(), base_path=self._reader.file.path)

    def write(self, data: Any) -> Path:
        text = self.dumper.dump(data)
        return self._writer.write_text(text)


class BinaryFileIO:
    def __init__(self, path: PathLike, *, policy: Optional[FSOOpsPolicy] = None):
        self._reader = FileReader(path, policy=policy or FSOOpsPolicy(exist=ExistencePolicy(must_exist=True)))
        self._writer = FileWriter(path, policy=policy or FSOOpsPolicy(exist=ExistencePolicy(create_if_missing=True)))

    def read(self) -> bytes:
        return self._reader.read_bytes()

    def write(self, data: bytes) -> Path:
        return self._writer.write_bytes(data)
