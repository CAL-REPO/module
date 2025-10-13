# -*- coding: utf-8 -*-
# crawl_refactor/normalizer.py

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Sequence

from .models import NormalizedItem
from .policy import NormalizationPolicy, NormalizationRule


def _get_by_path(data: Dict[str, Any], path: str | None) -> Any:
    if not path:
        return None
    current: Any = data
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


class DataNormalizer:
    """Rule-based normalizer that turns extractor output into NormalizedItem objects."""

    def __init__(self, policy: NormalizationPolicy):
        self.policy = policy

    def normalize(self, records: Sequence[Dict[str, Any]]) -> List[NormalizedItem]:
        items: List[NormalizedItem] = []
        for record_index, record in enumerate(records, start=1):
            for rule in self.policy.rules:
                value = _get_by_path(record, rule.source)
                if value is None and not rule.allow_empty:
                    continue

                values: Iterable[Any]
                if rule.explode and isinstance(value, (list, tuple, set)):
                    values = value
                else:
                    values = [value]

                section = rule.static_section or str(_get_by_path(record, rule.section_field) or "default")
                for item_index, val in enumerate(values, start=1):
                    if val is None and not rule.allow_empty:
                        continue

                    name_hint = None
                    if rule.name_template:
                        context = {
                            "record": record,
                            "value": val,
                            "section": section,
                            "record_index": record_index,
                            "item_index": item_index,
                        }
                        try:
                            name_hint = rule.name_template.format(**context)
                        except Exception:
                            name_hint = rule.name_template

                    normalized = NormalizedItem(
                        kind=rule.kind,
                        value=val,
                        section=section,
                        name_hint=name_hint,
                        extension=rule.extension,
                        metadata={"rule_source": rule.source},
                        record_index=record_index,
                        item_index=item_index,
                    )
                    items.append(normalized)
        return items
