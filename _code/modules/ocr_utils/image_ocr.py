#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simple entrypoint to run OCR on a single config or image path.

Usage:
    python image_ocr.py path/to/config_or_image

The script delegates to `ocr_utils.run_ocr` and prints a short summary.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

# When executed directly, ensure the project `_code` directory is on sys.path
# so imports like `modules.xxx` resolve regardless of current working dir.
_THIS = Path(__file__).resolve()
_CODE_DIR = _THIS.parent
if _CODE_DIR.name == "scripts":
    _PROJECT_CODE = _CODE_DIR
else:
    # fallback: parent folder is expected to be `_code`
    _PROJECT_CODE = _THIS.parent
sys.path.insert(0, str(_PROJECT_CODE))

from modules.ocr_utils import run_ocr


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:]) if argv is None else argv
    if not argv:
        print("Usage: python image_ocr.py <cfg_or_image_path>")
        return 2

    cfg_like = argv[0]

    try:
        items, meta, saved = run_ocr(cfg_like)
    except Exception as exc:  # pragma: no cover - surface errors to user
        print(f"OCR failed: {exc!r}")
        raise

    print(f"OCR completed: items={len(items)}, counts={{'final': {len(items)}}}")
    if saved:
        print(f"Meta saved: {saved}")
    else:
        print("Meta not saved (set ocr.file.save_ocr_meta=True to persist).")

    # Optionally write a quick summary file next to the image if available
    src = meta.get("image", {}).get("src_path") if isinstance(meta, dict) else None
    if src:
        try:
            out = Path(src).with_suffix(".ocr-summary.json")
            import json
            out.write_text(json.dumps({"items": len(items), "meta": meta.get("counts")}, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"Wrote quick summary: {out}")
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
