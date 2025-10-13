# -*- coding: utf-8 -*-
# yaml_utils/file_io.py
# description: YAML 파일 단위 입출력 통합 (YamlParser + YamlDumper)

from __future__ import annotations
from pathlib import Path
from typing import Any
from fso_utils.policy import FSOOpsPolicy
from fso_utils.ops import FSOOps
from .parser import YamlParser
from .dumper import YamlDumper
from .policy import YamlParserPolicy, YamlDumperPolicy


class YamlFileIO:
    """YAML 파일 단위 입출력 통합 클래스"""

    def __init__(
        self,
        path: str | Path,
        *,
        parser_policy: YamlParserPolicy | None = None,
        dumper_policy: YamlDumperPolicy | None = None,
        fso_policy: FSOOpsPolicy | None = None,
    ):
        self.path = FSOOps(path, fso_policy or FSOOpsPolicy(as_type="file"))
        self.parser = YamlParser(parser_policy)
        self.dumper = YamlDumper(dumper_policy)

    # ------------------------------------------------------------------
    # 읽기
    # ------------------------------------------------------------------
    def read(self) -> dict:
        """YAML 파일을 로드하여 dict 반환"""
        text = self.path.path.read_text(encoding=self.parser.policy.encoding)
        return self.parser.parse(text, base_path=self.path.path)

    # ------------------------------------------------------------------
    # 쓰기
    # ------------------------------------------------------------------
    def write(self, data: dict) -> Path:
        """dict를 YAML로 직렬화하여 파일로 저장"""
        yaml_text = self.dumper.dump(data)
        self.path.path.write_text(yaml_text, encoding=self.dumper.policy.encoding)
        return self.path.path
