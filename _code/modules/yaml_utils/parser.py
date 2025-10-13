# -*- coding: utf-8 -*-
# yaml_utils/parser.py
from __future__ import annotations
import os
import re
import yaml
from pathlib import Path
from typing import Any, cast
from yaml import Loader
from yaml.nodes import Node, ScalarNode
from .policy import YamlParserPolicy

class YamlParser:
    ENV_PATTERN = re.compile(r"\$\{([^}^{]+)\}")

    def __init__(self, policy: YamlParserPolicy | None = None):
        self.policy = policy or YamlParserPolicy.default()
        if self.policy.enable_include:
            yaml.add_constructor(
                "!include",
                lambda loader, node: self._include_constructor(cast(Loader, loader), node),
                Loader=yaml.FullLoader,
            )

    def parse(self, text: str, base_path: Path | None = None) -> dict:
        if self.policy.enable_env:
            text = self._expand_env(text)
        loader_cls = yaml.SafeLoader if self.policy.safe_mode else yaml.FullLoader
        data = yaml.load(text, Loader=loader_cls)
        return data or {}

    def _expand_env(self, text: str) -> str:
        def replacer(match: re.Match) -> str:
            expr = match.group(1)
            if ':' in expr:
                var, default = expr.split(':', 1)
            else:
                var, default = expr, ''
            return os.getenv(var, default)
        return self.ENV_PATTERN.sub(replacer, text)

    def _include_constructor(self, loader: Loader, node: Node) -> Any:
        if not isinstance(node, ScalarNode):
            raise TypeError("!include tag only supports scalar string paths.")
        filename = loader.construct_scalar(node)
        base_path = Path(getattr(loader, 'name', str(Path.cwd()))).parent
        full_path = (base_path / filename).resolve()
        with open(full_path, 'r', encoding=self.policy.encoding) as f:
            return yaml.load(f, Loader=type(loader))