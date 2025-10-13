# -*- coding: utf-8 -*-
# log_utils/fso_builder.py

from __future__ import annotations
from pathlib import Path
from fso_utils.path_builder import FSOPathBuilder

from .policy import LogPolicy


class LogFSOBuilder:
    """
    ✅ FSOPathBuilder 기반 로그 경로 생성기
    - LogPolicy.enabled == True 일 때만 동작
    - FSONamePolicy와 FSOOpsPolicy를 결합해 경로를 안전하게 생성
    """

    def __init__(self, policy: LogPolicy):
        self.policy = policy
        self.enabled = bool(policy.enabled)

        # 로그 비활성화 상태에서는 바로 종료
        if not self.enabled:
            return

        # FSOPathBuilder 초기화
        self.builder = FSOPathBuilder(
            base_dir=self.policy.dir_path,
            name_policy=self.policy.file_name_policy,
            ops_policy=self.policy.fso_policy,
        )

    def prepare(self, **override) -> Path | None:
        """
        ✅ 로그 파일 또는 디렉터리 경로 생성
        - override를 통해 name, tail_mode, suffix 등 동적 변경 가능
        """
        if not self.enabled:
            return None

        return self.builder.build(**override)
