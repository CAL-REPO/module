# structured_io/fileio/structured_fileio.py
from __future__ import annotations
from pathlib import Path
from typing import Any
from modules.fso_utils import FSOOps, FSOOpsPolicy

class StructuredFileIO:
    """포맷 무관한 파일 단위 입출력 어댑터 (fso_utils 연동)"""

    def __init__(self, path: str | Path, parser, dumper, fso_policy: FSOOpsPolicy | None = None):
        self.path = FSOOps(path, fso_policy or FSOOpsPolicy(as_type="file"))
        self.parser = parser
        self.dumper = dumper

    def read(self) -> Any:
        text = self.path.path.read_text(encoding=self.parser.policy.encoding)
        # base_path를 파일의 부모로 넘겨 !include 상대경로 보장
        return self.parser.parse(text, base_path=self.path.path)

    def write(self, data: Any) -> Path:
        text = self.dumper.dump(data)
        self.path.path.write_text(text, encoding=self.dumper.policy.encoding)
        return self.path.path
