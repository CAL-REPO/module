# -*- coding: utf-8 -*-
# yaml_utils/parser.py
from __future__ import annotations
import io
import yaml
from pathlib import Path
from typing import Any
from yaml import SafeLoader, FullLoader, ScalarNode, Loader
from .policy import YamlParserPolicy

from unify_utils.normalizers.placeholder_resolver import PlaceholderResolver
from unify_utils.normalizers.reference_resolver import ReferenceResolver


class YamlParser:
    """정책 기반 YAML 파서 (환경변수·Placeholder·Reference 치환 통합 지원)"""

    def __init__(
        self,
        policy: YamlParserPolicy | None = None,
        context: dict[str, Any] | None = None,
    ):
        self.policy = policy or YamlParserPolicy.default()
        self.context = context or {}
        self._register_include_tags()

    # ------------------------------------------------------------------
    # !include 지원
    # ------------------------------------------------------------------
    def _register_include_tags(self):
        """SafeLoader, FullLoader 모두에 !include 등록"""
        for loader_cls in (SafeLoader, FullLoader):
            yaml.add_constructor("!include", self._include_constructor, Loader=loader_cls) # pyright: ignore[reportArgumentType, reportCallIssue]

    def _include_constructor(self, loader: Loader, node: ScalarNode) -> Any:
        filename = loader.construct_scalar(node)
        base_path = Path(getattr(loader, "name", str(Path.cwd()))).parent
        full_path = (base_path / filename).resolve()
        with open(full_path, "r", encoding=self.policy.encoding) as f:
            return self.parse(f.read(), base_path=full_path.parent)

    # ------------------------------------------------------------------
    # 메인 파싱 로직
    # ------------------------------------------------------------------
    def parse(self, text: str, base_path: Path | None = None) -> dict:
        source_path = Path(base_path) if base_path else None
        try:
            # 1️⃣ 사전 처리 (PlaceholderResolver)
            if self.policy.enable_placeholder or self.policy.enable_env:
                placeholder = PlaceholderResolver(context=self.context)
                text = placeholder.apply(text)

            # 2️⃣ YAML 로딩
            loader_cls = SafeLoader if self.policy.is_safe_loader() else FullLoader
            stream: Any
            if source_path is not None:
                stream_io = io.StringIO(text)
                setattr(stream_io, "name", str(source_path))
                stream = stream_io
            else:
                stream = text
            data = yaml.load(stream, Loader=loader_cls) or {}

            # 3️⃣ 사후 처리 (ReferenceResolver)
            if self.policy.enable_reference and isinstance(data, dict):
                ref_resolver = ReferenceResolver(data, recursive=True)
                data = ref_resolver.apply(data)

            return data

        except Exception as e:
            self._handle_error(f"YAML 파싱 실패: {e}")
            return {}

    # ------------------------------------------------------------------
    # 에러 정책
    # ------------------------------------------------------------------
    def _handle_error(self, msg: str):
        if self.policy.on_error == "raise":
            raise RuntimeError(msg)
        elif self.policy.on_error == "warn":
            print(f"[경고] {msg}")
        # ignore 모드는 조용히 무시
