# -*- coding: utf-8 -*-
# crawl_utils/services/preset_policy_normalizer.py
"""
PresetPolicyNormalizer - Preset 정책 데이터 KeyPath 처리

책임:
- Preset policy dict → KeyPathDict 변환
- KeyPath 처리 (source 필드에서 추출)
- KeyPathDict.drop_blank() 사용
- NOT merge (ItemsNormalizer 책임)

KeyPath 처리:
- source 필드에서 KeyPath 추출 (images, product__images, optionsItems__url)
- 배열 인덱스 지원 ([0], [1], [*])
- 중간 경로 와일드카드 지원

데이터 흐름:
    YAML Preset → dict → PresetPolicyNormalizer.normalize()
    → KeyPathDict (preset_policy_kp)
    → ItemsNormalizer.process(preset_items=preset_policy_kp)

Author: GitHub Copilot
Date: 2025-10-28 (v8.0 - PresetItemsNormalizer → PresetPolicyNormalizer)
"""
from __future__ import annotations

from typing import Any, Dict, Tuple, Optional
from keypath_utils import KeyPathDict

class PresetPolicyNormalizer():
    """Preset 정책 데이터 KeyPath 처리 (dict → KeyPathDict)
    
    책임:
    - Preset policy dict를 KeyPathDict로 변환
    - KeyPath 추출 및 처리 (source 필드 기반)
    - 빈값 제거 (KeyPathDict.drop_blank() 사용)
    - merge 안함 (ItemsNormalizer 책임)
    
    설계 원칙:
    - 입력: dict (preset policy data from YAML)
    - 출력: KeyPathDict (preset_policy_kp)
    - 단일 책임: KeyPath 처리만 담당
    - merge 로직 없음 (ItemsNormalizer에서 처리)
    
    데이터 흐름:
        YAML → dict → normalize() → KeyPathDict
        → ItemsNormalizer (policy-driven iteration)
    
    Examples:
        >>> normalizer = PresetPolicyNormalizer()
        
        >>> # Case 1: 단순 KeyPath
        >>> preset = {
        ...     "items": [
        ...         {
        ...             "source_policy": {
        ...                 "kind": "image",
        ...                 "source": "images"
        ...             },
        ...             "save_policy": {
        ...                 "fso_name": {
        ...                     "prefix": "ALI",
        ...                     "name": "DETAILED"
        ...                 }
        ...             }
        ...         }
        ...     ]
        ... }
        >>> result = normalizer.normalize(preset)
        >>> # result = KeyPathDict({
        >>> #     "images": {
        >>> #         "kind": "image",
        >>> #         "source": "images",
        >>> #         "fso_name": {"prefix": "ALI", "name": "DETAILED"}
        >>> #     }
        >>> # })
        
        >>> # Case 2: 배열 KeyPath
        >>> preset = {
        ...     "items": [
        ...         {
        ...             "source_policy": {
        ...                 "kind": "image",
        ...                 "source": "optionsItems__url"
        ...             },
        ...             "save_policy": {
        ...                 "fso_name": {
        ...                     "prefix": "ALI",
        ...                     "name": "OPTION"
        ...                 }
        ...             }
        ...         }
        ...     ]
        ... }
        >>> result = normalizer.normalize(preset)
    """
    def __init__(self) -> None:
        pass

    def normalize(self, preset_policy_dict: dict[str, Any]) -> KeyPathDict:
        """Preset policy dict → KeyPathDict 변환 및 KeyPath 처리
        
        Args:
            preset_policy_dict: Preset policy dict (YAML에서 로드)
                형식: {"items": [{"source_policy": {...}, "save_policy": {...}}]}
        
        Returns:
            KeyPathDict: KeyPath를 key로 하는 정책 dict
                형식: {keypath: {kind, source, fso_name, fso_ops, dir_path}}
        
        Examples:
            >>> normalizer = PresetPolicyNormalizer()
            
            >>> preset = {
            ...     "items": [
            ...         {
            ...             "source_policy": {"kind": "image", "source": "images"},
            ...             "save_policy": {"fso_name": {"prefix": "ALI", "name": "DETAILED"}}
            ...         }
            ...     ]
            ... }
            
            >>> result = normalizer.normalize(preset)
            >>> # KeyPathDict({"images": {"kind": "image", "source": "images", "fso_name": {...}}})
        """

        if not isinstance(preset_policy_dict, dict):
            return KeyPathDict({})

        items = preset_policy_dict.get("items", [])
        if not isinstance(items, list) or not items:
            return KeyPathDict({})

        policy_dict: Dict[str, Any] = {}

        for item in items:
            if not isinstance(item, dict):
                continue

            keypath, data = self._extract_keypath_and_data(item)
            if not keypath:
                continue

            # Only include fields explicitly present in preset (do NOT fill blanks)
            # _extract_keypath_and_data already returns only present fields.
            if data:
                policy_dict[keypath] = data
        
        # Return a KeyPathDict and drop blank entries so callers get a clean model
        from keypath_utils import KeyPathDict as _KPD
        result = _KPD(policy_dict)
        result.drop_blanks()
        return result
    
    def _extract_keypath_and_data(self, item: dict[str, Any]) -> Tuple[Optional[str], dict[str, Any]]:
        """
        Extract keypath and data dict from a single preset item dict.

        Expecting item shapes like:
        {
            "source_policy": {"kind": "image", "source": "images"},
            "save_policy": {"fso_name": {"prefix": "ALI", "name": "DETAILED"}, "dir_path": None}
        }
        or possibly a flattened variant.

        Returns:
            (keypath, data) where data contains only fields explicitly present in the preset:
                data keys: kind, source, dir_path, fso_name, fso_ops (only if present)
        """
        if not isinstance(item, dict):
            return None, {}

        source_policy = item.get("source_policy", {})
        save_policy = item.get("save_policy", {})

        # if user supplied flattened item (less likely), try to use those keys directly
        # but prefer nested structure.
        if not source_policy and ("kind" in item or "source" in item):
            # treat item itself as source/save flattened
            source_policy = {k: item.get(k) for k in ("kind", "source") if k in item}
            # save_policy fields might be top-level as well
            save_policy = {k: item.get(k) for k in ("dir_path", "fso_name", "fso_ops") if k in item}

        keypath = None
        if isinstance(source_policy, dict):
            keypath = source_policy.get("source")
        if not keypath:
            return None, {}

        data: dict[str, Any] = {}

        # kind (only if explicitly present)
        if isinstance(source_policy, dict) and "kind" in source_policy:
            data["kind"] = source_policy["kind"]

        # source - keep original keypath for reference
        data["source"] = keypath

        # save_policy optional fields (only include when present in preset)
        if isinstance(save_policy, dict):
            if "dir_path" in save_policy:
                data["dir_path"] = save_policy["dir_path"]
            if "fso_name" in save_policy:
                data["fso_name"] = save_policy["fso_name"]
            if "fso_ops" in save_policy:
                data["fso_ops"] = save_policy["fso_ops"]

        return keypath, data


__all__ = ["PresetPolicyNormalizer"]
