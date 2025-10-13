# -*- coding: utf-8 -*-
# yaml_utils/dumper.py
# description: YAML 직렬화 (dump) 유틸리티

from __future__ import annotations
import yaml
from yaml import SafeDumper, Dumper
from typing import Any
from .policy import YamlDumperPolicy


class YamlDumper:
    """정책 기반 YAML 직렬화 클래스"""

    def __init__(self, policy: YamlDumperPolicy | None = None):
        self.policy = policy or YamlDumperPolicy.default()

    def dump(self, data: Any) -> str:
        """Python 객체를 YAML 문자열로 직렬화"""
        dumper_cls = SafeDumper if self.policy.safe_mode else Dumper

        return yaml.dump(
            data,
            Dumper=dumper_cls,
            allow_unicode=self.policy.allow_unicode,
            sort_keys=self.policy.sort_keys,
            default_flow_style=self.policy.default_flow_style,
            indent=self.policy.indent,
        )

    def dump_to_file(self, data: Any, path: str | None = None) -> str:
        """파일로 직렬화 (path 없으면 YAML 문자열 반환)"""
        text = self.dump(data)
        if path:
            with open(path, "w", encoding=self.policy.encoding) as f:
                f.write(text)
        return text
