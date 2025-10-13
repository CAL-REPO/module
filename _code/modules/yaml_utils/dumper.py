# -*- coding: utf-8 -*-
# yaml_utils/dumper.py
from __future__ import annotations
import yaml
from yaml_utils.policy import YamlParserPolicy

class YamlDumper:
    def __init__(self, policy: YamlParserPolicy | None = None):
        self.policy = policy or YamlParserPolicy.default()

    def dump(self, data: dict) -> str:
        return yaml.dump(
            data,
            allow_unicode=True,
            sort_keys=self.policy.sort_keys,
            default_flow_style=self.policy.default_flow_style,
            indent=self.policy.indent
        )