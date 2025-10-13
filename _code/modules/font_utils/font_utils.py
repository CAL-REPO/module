# -*- coding: utf-8 -*-
# font_utils/font.py

"""
modules.font — language-aware font helpers with caching
======================================================
- paths.fonts_dir()에서 폰트 폴더 단일 관리
- 언어 런 분할/간이 판별 + 언어별 폰트 선택
- 폰트 파일 로딩 캐시(@lru_cache)로 디스크 접근 최소화

공용 API
--------
- is_lang_char(ch, lang) -> bool
- detect_char_lang(ch) -> str
- segment_text_by_lang(text) -> List[(lang, run)]
- select_font_for_lang(lang, fonts_map, size=..., fonts_dir=...) -> ImageFont
- extract_lang_font_map(cfg_like) -> {lang: [filenames...]}

주의
- 여기서는 폰트 로딩/탐색/선택만 담당(렌더는 overlay.py)
"""


from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path
from functools import lru_cache

from .yamlutil import load_yaml
from ..paths import fonts_dir as paths_fonts_dir

try:
    from PIL import ImageFont
except Exception:
    ImageFont = None

PathLike = Union[str, Path]
CfgLike = Union[None, str, Path, Dict[str, object]]

__all__ = [
    "is_lang_char",
    "detect_char_lang",
    "segment_text_by_lang",
    "select_font_for_lang",
    "extract_lang_font_map",
]

# ---------------- language detection (lightweight) ----------------

def is_lang_char(ch: str, lang: str) -> bool:
    if not ch:
        return False
    cp = ord(ch)
    if lang == "space":
        return ch.isspace()
    if lang == "digit":
        return ch.isdigit()
    if lang == "en":
        return (0x41 <= cp <= 0x5A) or (0x61 <= cp <= 0x7A)
    if lang == "ko":
        return (0xAC00 <= cp <= 0xD7A3) or (0x1100 <= cp <= 0x11FF) or (0x3130 <= cp <= 0x318F)
    if lang == "punct":
        return (0x20 <= cp <= 0x40) or (0x5B <= cp <= 0x60) or (0x7B <= cp <= 0x7E)
    return True


def detect_char_lang(ch: str) -> str:
    if not ch:
        return "other"
    if is_lang_char(ch, "space"):
        return "space"
    if is_lang_char(ch, "digit"):
        return "digit"
    if is_lang_char(ch, "ko"):
        return "ko"
    if is_lang_char(ch, "en"):
        return "en"
    if is_lang_char(ch, "punct"):
        return "punct"
    return "other"


def segment_text_by_lang(text: str) -> List[Tuple[str, str]]:
    segs: List[Tuple[str, str]] = []
    cur_lang: Optional[str] = None
    buf: List[str] = []
    for ch in text:
        lg = detect_char_lang(ch)
        if lg == "space" and buf:
            buf.append(ch)
            continue
        if cur_lang is None:
            cur_lang = lg
            buf.append(ch)
            continue
        if lg == cur_lang:
            buf.append(ch)
        else:
            segs.append((cur_lang, "".join(buf)))
            cur_lang = lg
            buf = [ch]
    if buf:
        segs.append((cur_lang or "other", "".join(buf)))
    return segs

# ---------------- font loading with caching ----------------

@lru_cache(maxsize=256)
def _load_font_file_cached(path_str: str, size: int):
    """캐시된 폰트 로딩(ImageFont.truetype)."""
    if ImageFont is None:
        raise ImportError("Pillow is required. pip install pillow")
    return ImageFont.truetype(path_str, size=int(size))


def _resolve_base_dir(fonts_dir: Optional[PathLike]) -> Path:
    return Path(fonts_dir) if fonts_dir else paths_fonts_dir()


def _candidate_paths(names: List[str], base_dir: Path) -> List[Path]:
    out: List[Path] = []
    for nm in names or []:
        p = Path(nm)
        if not p.is_absolute():
            p = base_dir / p
        if p.exists():
            out.append(p)
        else:
            # 확장자 보간(ttf/otf/ttc)
            for ext in (".ttf", ".otf", ".ttc", ".TTF", ".OTF", ".TTC"):
                cand = p.with_suffix(ext)
                if cand.exists():
                    out.append(cand)
                    break
    # 중복 제거(해시 가능한 경로 문자열)
    seen = set()
    uniq: List[Path] = []
    for p in out:
        s = str(p.resolve())
        if s in seen:
            continue
        seen.add(s)
        uniq.append(p)
    return uniq


def select_font_for_lang(
    lang: str,
    fonts_map: Dict[str, List[str]],
    *,
    size: int = 28,
    fonts_dir: Optional[PathLike] = None,
):
    """언어 코드에 매핑된 후보 리스트에서 로드 가능한 첫 폰트 반환(ImageFont).
    - 캐시된 truetype 로더 사용으로 성능 향상
    - 실패 시 기본 폰트 반환
    """
    if ImageFont is None:
        raise ImportError("Pillow is required. pip install pillow")

    base = _resolve_base_dir(fonts_dir)
    names = fonts_map.get(lang) or fonts_map.get("other") or fonts_map.get("en") or []
    for p in _candidate_paths(list(names), base):
        try:
            return _load_font_file_cached(str(p.resolve()), int(size))
        except Exception:
            continue
    return ImageFont.load_default()

# ---------------- config extraction ----------------

def extract_lang_font_map(cfg_like: CfgLike) -> Dict[str, List[str]]:
    if cfg_like is None:
        return {}
    if isinstance(cfg_like, (str, Path)):
        root = load_yaml(cfg_like) or {}
    elif isinstance(cfg_like, dict):
        root = cfg_like
    else:
        return {}

    d = root.get("overlay") if isinstance(root, dict) else None
    d = d if isinstance(d, dict) else root
    fonts = d.get("fonts") if isinstance(d, dict) else None
    if isinstance(fonts, dict):
        norm: Dict[str, List[str]] = {}
        for k, v in fonts.items():
            if v is None:
                continue
            if isinstance(v, (list, tuple)):
                norm[k] = [str(x) for x in v]
            else:
                norm[k] = [str(v)]
        return norm
    return {}
