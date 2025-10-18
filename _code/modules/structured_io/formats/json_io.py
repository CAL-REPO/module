# structured_io/formats/json_io.py
from __future__ import annotations
import json
from typing import Any
from structured_io.core.interface import BaseParser, BaseDumper
from unify_utils.resolver.vars import VarsResolver
from unify_utils.core.policy import VarsResolverPolicy

class JsonParser(BaseParser):
    """JSON 파서.
    
    JSON은 include가 없으므로 enable_include는 무시.
    placeholder/env는 VarsResolver로 처리.
    """
    def parse(self, text: str, base_path=None) -> dict:
        try:
            # Placeholder/Env 치환 (VarsResolver 사용)
            if self.policy.enable_placeholder or self.policy.enable_env:
                vars_policy = VarsResolverPolicy(
                    enable_env=self.policy.enable_env,
                    enable_context=self.policy.enable_placeholder,
                    context=self.context or {},
                    recursive=False,  # 문자열만 처리하므로 recursive 불필요
                    strict=False
                )
                resolver = VarsResolver(data={}, policy=vars_policy)
                text = resolver.apply(text)  # ✅ public API 사용

            data = json.loads(text) if text.strip() else {}

            # Reference 치환은 제거 (ConfigNormalizer에서 처리)

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
