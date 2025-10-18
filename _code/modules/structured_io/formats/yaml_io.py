# structured_io/formats/yaml_io.py
from __future__ import annotations
import io
import yaml
from pathlib import Path
from typing import Any
from yaml import SafeLoader, FullLoader, ScalarNode, Loader, SafeDumper, Dumper

from structured_io.core.policy import BaseParserPolicy
from structured_io.core.interface import BaseParser, BaseDumper
from unify_utils.resolver.vars import VarsResolver
from unify_utils.core.policy import VarsResolverPolicy


class YamlParser(BaseParser):
    """YAML 파서.
    
    기능:
    - SafeLoader/FullLoader 선택(safe_mode)
    - !include 지원(enable_include)
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
            # 1) Placeholder/Env 치환 (VarsResolver 사용)
            if self.policy.enable_placeholder or self.policy.enable_env:
                # VarsResolver 정책 생성
                vars_policy = VarsResolverPolicy(
                    enable_env=self.policy.enable_env,
                    enable_context=self.policy.enable_placeholder,
                    context=self.context or {},
                    recursive=False,  # 문자열만 처리하므로 recursive 불필요
                    strict=False
                )
                # VarsResolver의 public API 사용 (apply 또는 __call__)
                resolver = VarsResolver(data={}, policy=vars_policy)
                text = resolver.apply(text)  # ✅ public API 사용

            # 2) YAML load (base_path 유지해서 !include 상대경로 대응)
            loader_cls = SafeLoader if self.policy.is_safe_loader() else FullLoader
            stream: Any
            if base_path is not None:
                stream_io = io.StringIO(text)
                setattr(stream_io, "name", str(base_path))  # include 기준 경로 제공
                stream = stream_io
            else:
                stream = text

            data = yaml.load(stream, Loader=loader_cls) or {}

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
