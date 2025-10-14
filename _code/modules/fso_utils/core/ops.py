# -*- coding: utf-8 -*-
# fso_utils/ops.py - 정책 기반 경로 관리

from __future__ import annotations

from pathlib import Path
from typing import Optional

from typing import Union
from data_utils.core.types import PathLike
from .policy import FSOOpsPolicy

class FSOOps:
    def __init__(self, base: PathLike, policy: Optional[FSOOpsPolicy] = None):
        self._raw = Path(base).expanduser()
        self.policy = policy or FSOOpsPolicy() # pyright: ignore[reportCallIssue]
        self.path = self.policy.apply_to(self._raw)  # 정책 적용 (이제 policy.py로 이동됨)

    @property
    def exists(self) -> bool:
        return self.path.exists()

    @property
    def is_file(self) -> bool:
        return self.path.is_file()

    @property
    def is_dir(self) -> bool:
        return self.path.is_dir()

    def __str__(self):
        return str(self.path)

    def __fspath__(self):
        return str(self.path)

    def __repr__(self):
        return f"<FileOps path={self.path!s}>"