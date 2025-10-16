# structured_io/formats/yaml_io.py
from __future__ import annotations
import io
import yaml
from pathlib import Path
from typing import Any
from yaml import SafeLoader, FullLoader, ScalarNode, Loader, SafeDumper, Dumper

from structured_io.core.base_parser import BaseParser
from structured_io.core.base_dumper import BaseDumper
from unify_utils.normalizers.resolver_placeholder import PlaceholderResolver
from unify_utils.normalizers.resolver_reference import ReferenceResolver


class YamlParser(BaseParser):
    """
    - SafeLoader/FullLoader 선택(safe_mode)
    - !include 지원(enable_include)
    - Placeholder/Env 치환(enable_placeholder/enable_env)
    - Reference 치환(enable_reference)
    """
    def __init__(self, policy, context: dict | None = None):
        super().__init__(policy, context=context)
        if self.policy.enable_include:
            self._register_include_tag()

    def _register_include_tag(self):
        for loader_cls in (SafeLoader, FullLoader):
            yaml.add_constructor("!include", self._include_constructor, Loader=loader_cls)  # pyright: ignore

    def _include_constructor(self, loader: Loader, node: ScalarNode) -> Any:
        filename = loader.construct_scalar(node)
        base_path = Path(getattr(loader, "name", str(Path.cwd()))).parent
        full_path = (base_path / filename).resolve()
        with open(full_path, "r", encoding=self.policy.encoding) as f:
            return self.parse(f.read(), base_path=full_path.parent)

    def parse(self, text: str, base_path: Path | None = None) -> dict:
        try:
            # 1) First pass: Load raw YAML to get initial values
            loader_cls = SafeLoader if self.policy.is_safe_loader() else FullLoader
            stream: Any
            if base_path is not None:
                stream_io = io.StringIO(text)
                setattr(stream_io, "name", str(base_path))
                stream = stream_io
            else:
                stream = text
            
            raw_data = yaml.load(stream, Loader=loader_cls) or {}
            
            # 2) Build context from raw data + user context
            combined_context = {**raw_data, **(self.context or {})}
            
            # 3) Placeholder/Env resolution with context (recursive)
            if self.policy.enable_placeholder or self.policy.enable_env:
                placeholder = PlaceholderResolver(context=combined_context, recursive=True)
                data = placeholder.apply(raw_data)
            else:
                data = raw_data

            # 4) Reference resolution
            if self.policy.enable_reference and isinstance(data, dict):
                data = ReferenceResolver(data, recursive=True).apply(data)

            return data

        except Exception as e:
            if self.policy.on_error == "raise":
                raise RuntimeError(f"YAML 파싱 실패: {e}")
            elif self.policy.on_error == "warn":
                print(f"[경고] YAML 파싱 실패: {e}")
            return {}


class YamlDumper(BaseDumper):
    def dump(self, data: Any) -> str:
        dumper_cls = SafeDumper if self.policy.safe_mode else Dumper
        return yaml.dump(
            data,
            Dumper=dumper_cls,
            allow_unicode=self.policy.allow_unicode,
            sort_keys=self.policy.sort_keys,
            default_flow_style=self.policy.default_flow_style,
            indent=self.policy.indent,
        )
