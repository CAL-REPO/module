# -*- coding: utf-8 -*-
# fso_utils/path_builder.py - 파일/디렉터리 경로 빌더 (FSONameBuilder + FSOOps 통합)

from __future__ import annotations
from pathlib import Path
from typing import Optional
from copy import deepcopy

from .name_builder import FSONameBuilder
from .ops import FSOOps
from .policy import FSONamePolicy, FSOOpsPolicy


class FSOPathBuilder:
    """
    FSONameBuilder와 FSOOps를 통합한 고수준 경로 생성기

    ✅ 주요 기능:
    - FSONamePolicy를 기반으로 파일/폴더명 생성
    - FSOOpsPolicy를 적용하여 존재 정책/확장자 정책 검증
    - 필요 시 디렉터리 자동 생성
    - ensure_unique, tail_mode, extension, sanitize 등 모든 이름 정책 반영
    """

    def __init__(
        self,
        base_dir: Path,
        name_policy: FSONamePolicy,
        ops_policy: Optional[FSOOpsPolicy] = None,
    ):
        self.base_dir = Path(base_dir).expanduser().resolve()
        self.name_policy = deepcopy(name_policy)
        self.ops_policy = deepcopy(ops_policy) if ops_policy else FSOOpsPolicy(as_type=name_policy.as_type)

        if not self.base_dir.exists():
            if self.ops_policy.exist.create_if_missing:
                self.base_dir.mkdir(parents=True, exist_ok=True)
            else:
                raise FileNotFoundError(f"기본 디렉터리가 존재하지 않습니다: {self.base_dir}")

    def build(self, **override) -> Path:
        """
        정책 기반 파일/디렉터리 경로 생성 (override 가능)
        """
        name_policy = self.name_policy.model_copy(update=override)
        builder = FSONameBuilder(name_policy)

        target_path = (
            self.base_dir / builder.build()
            if name_policy.as_type == "dir"
            else builder.build_unique(self.base_dir)
        )

        fso = FSOOps(target_path, policy=self.ops_policy)
        return fso.path

    def __call__(self, **override) -> Path:
        return self.build(**override)
