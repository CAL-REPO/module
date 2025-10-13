# -*- coding: utf-8 -*-
# crawl/normalizer.py
from __future__ import annotations
from typing import Any, Dict, List, Tuple, Optional
from data_utils.trans_ops import DataTransOps

def normalize_groups(js_result: Any, schema: Optional[dict[str, str]] = None) -> Dict[str | None, List[Tuple[str | None, Any]]]:
    if isinstance(js_result, list) and len(js_result) >= 3 and all(not isinstance(x, (list, dict)) for x in js_result):
        return DataTransOps.list_to_grouped_pairs(js_result)
    if isinstance(js_result, dict):
        out: Dict[str | None, List[Tuple[str | None, Any]]] = {}
        for mk, arr in js_result.items():
            for it in DataTransOps.value_to_list(arr):
                if isinstance(it, (list, tuple)) and len(it) >= 2:
                    t, v = it[0], it[1]
                    out.setdefault(str(mk) if mk else None, []).append((str(t) if t else None, v))
        return out
    return {}
