# structured_io/formats/json_io.py
from __future__ import annotations
import json
from typing import Any
from structured_io.base.base_parser import BaseParser
from structured_io.base.base_dumper import BaseDumper
from unify_utils.normalizers.placeholder_resolver import PlaceholderResolver
from unify_utils.normalizers.reference_resolver import ReferenceResolver

class JsonParser(BaseParser):
    """
    JSON은 include가 없으므로 enable_include는 무시.
    placeholder/env/reference는 동일하게 지원.
    """
    def parse(self, text: str, base_path=None) -> dict:
        try:
            if self.policy.enable_placeholder or self.policy.enable_env:
                text = PlaceholderResolver(context=self.context).apply(text)

            data = json.loads(text) if text.strip() else {}

            if self.policy.enable_reference and isinstance(data, dict):
                data = ReferenceResolver(data, recursive=True).apply(data)

            return data
        except Exception as e:
            if self.policy.on_error == "raise":
                raise RuntimeError(f"JSON 파싱 실패: {e}")
            elif self.policy.on_error == "warn":
                print(f"[경고] JSON 파싱 실패: {e}")
            return {}

class JsonDumper(BaseDumper):
    def dump(self, data: Any) -> str:
        # ensure_ascii는 allow_unicode의 반대 개념
        ensure_ascii = not self.policy.allow_unicode
        return json.dumps(
            data,
            ensure_ascii=ensure_ascii,
            indent=self.policy.indent if self.policy.indent > 0 else None,
            sort_keys=self.policy.sort_keys,
        )
