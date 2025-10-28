# -*- coding: utf-8 -*-
# crawl_utils/services/item_normalizer.py
"""
ItemNormalizer - 아이템 자동 추론 (source -> CrawlItems)

Responsibilities:
- Infer as much as possible from `source` (URL or bytes)
- Return a fully populated `CrawlItems` object (with defaults)
- Works without presets

Main changes compared to original:
- Corrected constructor and public API for `normalize`
- Robust URL detection and fallbacks
- Removed unused imports
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Union, Mapping
from urllib.parse import urlparse, unquote

from modules.path_utils.os_paths import OSPath
from ..core.policy import ItemKind, CrawlItemSourcePolicy, CrawlItemSavePolicy, CrawlItem
from modules.fso_utils.core.policy import FSONamePolicy, FSOOpsPolicy


class ItemNormalizer:
    """ItemNormalizer: infer metadata (kind, filename, extension, dir_path) from source.

    Public API:
      normalize(source: str|bytes, kind: Optional[ItemKind]=None) -> CrawlItem

    Notes:
      - If `source` is bytes, name inference is not possible (use 'untitled').
      - If `kind` is provided, it overrides inferred kind.
    """

    def __init__(self) -> None:
        # No special initialization required; keep object stateless
        pass

    def normalize(
        self,
        source: Union[str, bytes, Mapping, None] = None,
        *,
        kind: Optional[ItemKind] = None,
        policy_like: Optional[Mapping] = None,
        apply_fragment: Optional[dict] = None,
        runtime_overrides: Optional[dict] = None,
    ) -> CrawlItem:
        """
        Normalize a single item source into CrawlItem.

        Args:
            source: URL (str), bytes, or dict-like record/fragment (may include 'source','kind','fso_name', etc.)
            policy_like: optional mapping representing a pre-built item policy (may contain
                         'source_policy' and/or 'save_policy'). When provided, its explicit
                         fields take precedence over values parsed from `source`.
            kind: optional override for item kind
            apply_fragment: preset fragment (explicit fields) to prefer over inferred
            runtime_overrides: final flat-key overrides (optional)
        Returns:
            CrawlItem (with source_policy and save_policy)
        """
        # Resolve initial values from 'policy_like' or 'source' when either is dict-like
        explicit_source = None
        explicit_kind = None
        explicit_dir = None
        explicit_fso_name = None
        explicit_fso_ops = None
        # If a policy_like mapping was provided, prefer its explicit fields
        src_map = policy_like if isinstance(policy_like, Mapping) else (source if isinstance(source, Mapping) else None)
        if isinstance(src_map, Mapping):
            sp = src_map.get("source_policy") or src_map.get("sourcePolicy") or {}
            if isinstance(sp, Mapping):
                explicit_source = sp.get("source") or explicit_source
                explicit_kind = sp.get("kind") or explicit_kind

            sv = src_map.get("save_policy") or src_map.get("savePolicy") or {}
            if isinstance(sv, Mapping):
                if "dir_path" in sv:
                    explicit_dir = sv.get("dir_path")
                if "fso_name" in sv:
                    explicit_fso_name = sv.get("fso_name")
                if "fso_ops" in sv:
                    explicit_fso_ops = sv.get("fso_ops")

            # flattened keys
            if explicit_source is None and "source" in src_map:
                explicit_source = src_map.get("source")
            if explicit_kind is None and "kind" in src_map:
                explicit_kind = src_map.get("kind")
            if explicit_fso_name is None and "fso_name" in src_map:
                explicit_fso_name = src_map.get("fso_name")
            if explicit_dir is None and "dir_path" in src_map:
                explicit_dir = src_map.get("dir_path")

        # If not provided via policy_like, but source itself is a mapping, allow it as a secondary source
        if src_map is None and isinstance(source, Mapping):
            sp = source.get("source_policy") or source.get("sourcePolicy") or {}
            if isinstance(sp, Mapping):
                explicit_source = sp.get("source") or explicit_source
                explicit_kind = sp.get("kind") or explicit_kind

            sv = source.get("save_policy") or source.get("savePolicy") or {}
            if isinstance(sv, Mapping):
                if "dir_path" in sv:
                    explicit_dir = sv.get("dir_path")
                if "fso_name" in sv:
                    explicit_fso_name = sv.get("fso_name")
                if "fso_ops" in sv:
                    explicit_fso_ops = sv.get("fso_ops")

            # flattened keys
            if explicit_source is None and "source" in source:
                explicit_source = source.get("source")
            if explicit_kind is None and "kind" in source:
                explicit_kind = source.get("kind")
            if explicit_fso_name is None and "fso_name" in source:
                explicit_fso_name = source.get("fso_name")
            if explicit_dir is None and "dir_path" in source:
                explicit_dir = source.get("dir_path")
        else:
            # non-mapping: keep as-is (str or bytes)
            explicit_source = source

        # Apply apply_fragment (preset fragment has higher precedence than explicit values from source/policy_like)
        fragment = apply_fragment or {}
        if isinstance(fragment, Mapping):
            if fragment.get("source") is not None:
                explicit_source = fragment.get("source")
            if fragment.get("kind") is not None:
                explicit_kind = fragment.get("kind")
            if fragment.get("dir_path") is not None:
                explicit_dir = fragment.get("dir_path")
            if fragment.get("fso_name") is not None:
                explicit_fso_name = fragment.get("fso_name")
            if fragment.get("fso_ops") is not None:
                explicit_fso_ops = fragment.get("fso_ops")

        # runtime_overrides are highest precedence (flat keys like "save__fso_name__name")
        # We'll apply them later to the constructed pydantic models; for now we record them.
        overrides = runtime_overrides or {}

        # Now decide effective source value (string/bytes)
        effective_source = explicit_source if explicit_source is not None else (source if not isinstance(source, Mapping) else None)
        # ensure effective_source is only str/bytes or None (policies expect str|bytes)
        if isinstance(effective_source, Mapping):
            effective_source = None

        # 1) determine kind (explicit_kind > param kind > infer from effective_source)
        effective_kind = explicit_kind if explicit_kind is not None else (kind if kind is not None else None)
        if effective_kind is None:
            if isinstance(effective_source, (str, bytes)):
                effective_kind = self._infer_kind(effective_source)
            else:
                effective_kind = "file"

        # 2) infer name/extension if needed (only from URL/string)
        inferred_name = "untitled"
        inferred_ext = ""
        if isinstance(effective_source, str) and self._is_url(effective_source):
            name_from_url = self._infer_name_from_url(effective_source)
            ext_from_url = self._infer_extension_from_url(effective_source)
            if name_from_url:
                inferred_name = name_from_url
            if ext_from_url:
                inferred_ext = ext_from_url

        # If preset explicit fso_name provided as dict, prefer fields from it
        fso_name_policy = None
        if explicit_fso_name:
            if isinstance(explicit_fso_name, dict):
                # ensure as_type/name/extension defaults
                d = dict(explicit_fso_name)
                d.setdefault("as_type", "file")
                d.setdefault("name", inferred_name)
                if "extension" not in d:
                    d.setdefault("extension", inferred_ext)
                try:
                    fso_name_policy = FSONamePolicy(**d)
                except Exception:
                    # fallback: create default instance then set available fields
                    fso_name_policy = FSONamePolicy()
                    for kk, vv in d.items():
                        if hasattr(fso_name_policy, kk):
                            try:
                                setattr(fso_name_policy, kk, vv)
                            except Exception:
                                pass
            elif isinstance(explicit_fso_name, FSONamePolicy):
                fso_name_policy = explicit_fso_name

        if fso_name_policy is None:
            fso_name_policy = FSONamePolicy()
            try:
                fso_name_policy.as_type = "file"
                fso_name_policy.name = inferred_name
                fso_name_policy.extension = inferred_ext
            except Exception:
                pass

        # dir path
        dir_path = explicit_dir if explicit_dir is not None else OSPath.downloads()
        # fso_ops
        fso_ops_policy = explicit_fso_ops if explicit_fso_ops is not None else FSOOpsPolicy(as_type="file")

        # Build source/save policies
        # Ensure source value is of expected type (str|bytes). If not present, use empty string.
        source_val = effective_source if isinstance(effective_source, (str, bytes)) else ""
        source_policy = CrawlItemSourcePolicy(kind=effective_kind, source=source_val)
        save_policy = CrawlItemSavePolicy(dir_path=dir_path, fso_name=fso_name_policy, fso_ops=fso_ops_policy)

        ci = CrawlItem(source_policy=source_policy, save_policy=save_policy)

        # Apply runtime flat-key overrides if any (support multiple flat-key styles)
        if overrides:
            # Accept keys like:
            #  - 'source__source' or 'source__kind'
            #  - 'save__fso_name__name' or 'save_policy__fso_name__name'
            #  - 'fso_name__name' (ItemsNormalizer strips item keypath prefix)
            #  - 'fso_ops__overwrite'
            #  - 'dir_path'
            for flat_key, v in overrides.items():
                parts = [p for p in str(flat_key).split("__") if p != ""]
                if not parts:
                    continue

                # Normalize root and handling
                root = parts[0]

                try:
                    if root == "source":
                        # source__source or source__kind
                        if len(parts) >= 2:
                            attr = parts[1]
                            try:
                                setattr(ci.source_policy, attr, v)
                            except Exception:
                                pass
                    elif root in ("save", "save_policy"):
                        # save__fso_name__name or save__dir_path
                        if len(parts) >= 2:
                            sub = parts[1]
                            if sub == "fso_name" and len(parts) >= 3:
                                attr = parts[2]
                                try:
                                    fn = ci.save_policy.fso_name
                                    setattr(fn, attr, v)
                                    ci.save_policy.fso_name = fn
                                except Exception:
                                    pass
                            elif sub == "fso_ops" and len(parts) >= 3:
                                attr = parts[2]
                                try:
                                    fo = ci.save_policy.fso_ops
                                    setattr(fo, attr, v)
                                    ci.save_policy.fso_ops = fo
                                except Exception:
                                    pass
                            elif sub == "dir_path":
                                try:
                                    ci.save_policy.dir_path = v
                                except Exception:
                                    pass
                    elif root == "fso_name":
                        # direct fso_name__name (ItemsNormalizer passes this form)
                        if len(parts) >= 2:
                            attr = parts[1]
                            try:
                                fn = ci.save_policy.fso_name
                                setattr(fn, attr, v)
                                ci.save_policy.fso_name = fn
                            except Exception:
                                pass
                    elif root == "fso_ops":
                        if len(parts) >= 2:
                            attr = parts[1]
                            try:
                                fo = ci.save_policy.fso_ops
                                setattr(fo, attr, v)
                                ci.save_policy.fso_ops = fo
                            except Exception:
                                pass
                    elif root in ("dir_path",):
                        # plain dir_path override
                        try:
                            ci.save_policy.dir_path = v
                        except Exception:
                            pass
                    elif root == "kind":
                        try:
                            ci.source_policy.kind = v
                        except Exception:
                            pass
                    else:
                        # unsupported/unknown root — ignore
                        pass
                except Exception:
                    # be defensive — don't let one bad override abort normalization
                    continue
        return ci

    def _infer_kind(self, source: Union[str, bytes]) -> ItemKind:
        """Infer item kind from source."""
        if isinstance(source, bytes):
            return "file"
        if not isinstance(source, str):
            return "file"

        # try extension-based inference
        ext = self._infer_extension_from_url(source)
        if not ext:
            return "file"

        image_exts = {"jpg", "jpeg", "png", "gif", "bmp", "webp", "svg", "ico"}
        if ext.lower() in image_exts:
            return "image"

        text_exts = {"txt", "md", "csv", "json", "xml", "html", "css", "js"}
        if ext.lower() in text_exts:
            return "text"

        return "file"

    def _is_url(self, source: str) -> bool:
        """Return True if the given string is an http(s) URL."""
        try:
            parsed = urlparse(source)
            return parsed.scheme in ("http", "https") and bool(parsed.netloc)
        except Exception:
            return False

    def _infer_name_from_url(self, url: str) -> Optional[str]:
        """Extract file stem from URL path (URL-decoded)."""
        try:
            parsed = urlparse(url)
            path = unquote(parsed.path)
            filename = Path(path).name
            if not filename:
                return None
            name = Path(filename).stem
            if not name:
                return None
            return self._sanitize(name)
        except Exception:
            return None

    def _infer_extension_from_url(self, url: str) -> Optional[str]:
        """Return extension for URL path (without dot), lowercased."""
        try:
            parsed = urlparse(url)
            path = unquote(parsed.path)
            ext = Path(path).suffix
            if not ext:
                return None
            return ext.lstrip(".").lower() or None
        except Exception:
            return None

    def _sanitize(self, text: Optional[str]) -> str:
        """Sanitize a filename stem for filesystems.

        - Removes Windows/Unix forbidden characters
        - Collapses whitespace
        - Falls back to 'untitled' for empty results
        """
        if not text:
            return "untitled"

        # Remove characters invalid in filenames and control chars
        UNSAFE_CHARS = r'[<>:"/\\|?*\x00-\x1f]'
        text = re.sub(UNSAFE_CHARS, "", text)
        # collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        # avoid names like '.' or '..'
        if text in ("", ".", ".."):
            return "untitled"
        return text


__all__ = ["ItemNormalizer"]