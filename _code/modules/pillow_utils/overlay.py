# -*- coding: utf-8 -*-
"""
modules.overlay — YAML/dict-aware overlay renderer
- cfg_like 입력 지원: str(Path to yaml) | dict | OverlayConfig
- 2-PASS: 모든 poly 먼저 마스킹 → 모든 텍스트 한 번에 그리기
- 문자 단위(ko/ch/en) 폰트 적용 + 혼합문자 폭 기준 자동 폰트 크기

overlay:
  file_path: "path/to/image.jpg"
  ol_save_dir: ""                # default: dirname(file_path)
  ol_save_suffix: ""             # default: _overlay (같은 폴더 저장 시 자동)
  common:
    font_min_size: 3
    font_ratio_box: 0.5
  fonts:
    dir: ""                      # default: OS font dir
    lang:
      ch: { family: "Noto Sans CJK SC", color: "#000000", size_px: null, weight: 1000 }
      en: { family: "Arial",            color: "#000000", size_px: null, weight: 1000 }
      ko: { family: "Noto Sans KR",     color: "#000000", size_px: null, weight: 1000 }
    common:
      align: center
      coord_space: px_orig
      place: { anchor: c, offset: {dx: 0, dy: 0}, padding_px: 2 }
  ol:
    - text: "TEST"
      poly: [[120,180],[360,170],[365,220],[125,230]]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path
import platform
import math

from PIL import Image, ImageDraw, ImageFont

from modules.fileio import ensure_dir, compute_output_path_for_copy
from modules.yamlutil import load_yaml, section_or_root
from pillow.pillow import load_image, save_image


# =============================================================================
# Dataclasses
# =============================================================================

def _default_fonts_dir() -> str:
    sys = platform.system().lower()
    if "windows" in sys: return r"C:\Windows\Fonts"
    if "darwin" in sys or "mac" in sys: return "/System/Library/Fonts"
    return "/usr/share/fonts"

@dataclass
class PlaceSpec:
    anchor: str = "c"          # tl,t,tr,l,c,r,bl,b,br
    offset_dx: float = 0.0
    offset_dy: float = 0.0
    padding_px: float = 2.0

@dataclass
class FontSpec:
    family: str = "Arial"      # path or family hint
    color: str = "#000000"
    size_px: Optional[int] = None  # None -> auto fit
    weight: int = 500
    stroke_color: Optional[str] = None
    stroke_px: int = 0

@dataclass
class CommonSpec:
    align: str = "center"      # left|center|right
    coord_space: str = "px_orig"  # px_orig|norm
    place: PlaceSpec = field(default_factory=PlaceSpec)
    font_min_size: int = 3
    font_ratio_box: float = 0.5  # box height * ratio

@dataclass
class OverlayConfig:
    file_path: str
    ol_save_dir: str
    ol_save_suffix: Optional[str]
    fonts_dir: str
    fonts_lang: Dict[str, FontSpec]
    common: CommonSpec
    ol_items: List[Dict[str, Any]]   # {text, poly}

@dataclass
class PreparedItem:
    text: str
    poly_px: List[List[float]]
    bbox: Dict[str, float]
    angle_deg: float

# =============================================================================
# Parse & Normalize (cfg_like 지원)
# =============================================================================

CfgLike = Union[str, Path, Dict[str, Any], OverlayConfig, None]

def _get(d: Dict[str, Any], path: List[str], default=None):
    cur = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur: return default
        cur = cur[k]
    return cur

def _parse_place(d: Dict[str, Any]) -> PlaceSpec:
    anchor = str(_get(d, ["anchor"], "c")).lower()
    off = _get(d, ["offset"], {}) or {}
    return PlaceSpec(
        anchor=anchor if anchor in {"tl","t","tr","l","c","r","bl","b","br"} else "c",
        offset_dx=float(_get(off, ["dx"], 0.0)),
        offset_dy=float(_get(off, ["dy"], 0.0)),
        padding_px=float(_get(d, ["padding_px"], 2.0)),
    )

def _parse_font(d: Dict[str, Any]) -> FontSpec:
    sp = _get(d, ["size_px"], None)
    return FontSpec(
        family=str(_get(d, ["family"], "Arial")),
        color=str(_get(d, ["color"], "#000000")),
        size_px=None if (sp in (None, "")) else int(sp),
        weight=int(_get(d, ["weight"], 500)),
        stroke_color=_get(d, ["stroke_color"], None),
        stroke_px=int(_get(d, ["stroke_px"], 0)),
    )

def _overlay_section(cfg_like: CfgLike) -> Dict[str, Any]:
    if cfg_like is None:
        return {}
    if isinstance(cfg_like, OverlayConfig):
        fonts = {
            "dir": cfg_like.fonts_dir,
            "lang": {k: cfg_like.fonts_lang[k].__dict__ for k in cfg_like.fonts_lang},
            "common": {
                "align": cfg_like.common.align,
                "coord_space": cfg_like.common.coord_space,
                "place": cfg_like.common.place.__dict__,
            },
        }
        common = {"font_min_size": cfg_like.common.font_min_size, "font_ratio_box": cfg_like.common.font_ratio_box}
        return {
            "file_path": cfg_like.file_path,
            "ol_save_dir": cfg_like.ol_save_dir,
            "ol_save_suffix": cfg_like.ol_save_suffix,
            "fonts": fonts,
            "common": common,
            "ol": list(cfg_like.ol_items),
        }
    if isinstance(cfg_like, (str, Path)):
        root = load_yaml(str(cfg_like)) or {}
        return section_or_root(root, "overlay")
    if isinstance(cfg_like, dict):
        return section_or_root(cfg_like, "overlay")
    raise TypeError("overlay cfg must be dict|str|Path|OverlayConfig|None")

def normalize_overlay_cfg(cfg_like: CfgLike) -> OverlayConfig:
    ov = _overlay_section(cfg_like) or {}

    file_path = str(ov.get("file_path", "") or "")
    ol_save_dir = str(ov.get("ol_save_dir", "") or "")
    ol_save_suffix = str(ov.get("ol_save_suffix", "") or "")

    fonts_dir = str(_get(ov, ["fonts","dir"], "") or _default_fonts_dir())

    fonts_lang_cfg = _get(ov, ["fonts","lang"], {}) or {}
    fonts_lang: Dict[str, FontSpec] = {str(k): _parse_font(v) for k, v in fonts_lang_cfg.items()}

    fonts_common = _get(ov, ["fonts","common"], {}) or {}
    size_common = _get(ov, ["common"], {}) or {}

    common = CommonSpec(
        align=str(fonts_common.get("align", "center")).lower(),
        coord_space=str(fonts_common.get("coord_space", "px_orig")).lower(),
        place=_parse_place(fonts_common.get("place", {}) or {}),
        font_min_size=int(size_common.get("font_min_size", 3)),
        font_ratio_box=float(size_common.get("font_ratio_box", 0.5)),
    )

    ol_items = list(ov.get("ol", []) or [])

    return OverlayConfig(
        file_path=file_path,
        ol_save_dir=ol_save_dir,
        ol_save_suffix=ol_save_suffix,
        fonts_dir=fonts_dir,
        fonts_lang=fonts_lang,
        common=common,
        ol_items=ol_items,
    )

# =============================================================================
# Language detect (char-level)
# =============================================================================

def detect_lang_char(ch: str) -> str:
    if "\uac00" <= ch <= "\ud7a3" or "\u3130" <= ch <= "\u318f" or "\u1100" <= ch <= "\u11ff":
        return "ko"
    if "\u4e00" <= ch <= "\u9fff":
        return "ch"
    if ("A" <= ch <= "Z") or ("a" <= ch <= "z"):
        return "en"
    return "en"

# =============================================================================
# Geometry & Font helpers
# =============================================================================

_ANCHOR_AX = {"tl":0.0,"t":0.5,"tr":1.0,"l":0.0,"c":0.5,"r":1.0,"bl":0.0,"b":0.5,"br":1.0}
_ANCHOR_AY = {"tl":0.0,"t":0.0,"tr":0.0,"l":0.5,"c":0.5,"r":0.5,"bl":1.0,"b":1.0}

def _scale_poly(poly: List[List[float]], W: int, H: int) -> List[List[float]]:
    return [[float(px)*W, float(py)*H] for (px,py) in poly]

def _poly_to_bbox(poly: List[List[float]]) -> Dict[str, float]:
    xs = [float(p[0]) for p in poly]; ys = [float(p[1]) for p in poly]
    return {"x0": min(xs), "y0": min(ys), "x1": max(xs), "y1": max(ys)}

def _expand_bbox(b: Dict[str,float], pad: float) -> Dict[str,float]:
    return {"x0": b["x0"]-pad, "y0": b["y0"]-pad, "x1": b["x1"]+pad, "y1": b["y1"]+pad}

def _angle_from_poly(poly: List[List[float]]) -> float:
    (x1,y1),(x2,y2) = poly[0], poly[1]
    return math.degrees(math.atan2(y2 - y1, x2 - x1))

def _anchor_xy(b: Dict[str,float], anchor: str) -> Tuple[float,float]:
    ax = _ANCHOR_AX.get(anchor, 0.5); ay = _ANCHOR_AY.get(anchor, 0.5)
    return (b["x0"] + (b["x1"]-b["x0"])*ax, b["y0"] + (b["y1"]-b["y0"])*ay)

def _find_font_path(fonts_dir: str, family: str) -> Optional[str]:
    p = Path(family)
    if p.suffix.lower() in (".ttf",".otf",".ttc") and p.exists(): return str(p)
    base = Path(fonts_dir or _default_fonts_dir())
    if not base.exists(): return None
    try:
        for ext in ("*.ttf","*.otf","*.ttc"):
            for fp in base.rglob(ext):
                if family.lower() in fp.name.lower():
                    return str(fp)
    except Exception:
        return None
    return None

def _load_font(fonts_dir: str, spec: FontSpec, size_px: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = _find_font_path(fonts_dir, spec.family)
    if path:
        try:
            return ImageFont.truetype(path, size=size_px)
        except Exception:
            pass
    try:
        return ImageFont.truetype("arial.ttf", size=size_px)
    except Exception:
        return ImageFont.load_default()

def _measure_char(draw: ImageDraw.ImageDraw, ch: str, font: ImageFont.ImageFont) -> Tuple[int,int]:
    x0,y0,x1,y1 = draw.textbbox((0,0), ch, font=font, anchor="lt")
    return (max(0,x1-x0), max(0,y1-y0))

def _auto_font_px_ratio_fit(
    text: str,
    fonts_dir: str,
    specs_by_lang: Dict[str, FontSpec],
    bbox: Dict[str,float],
    ratio: float,
    min_px: int,
) -> int:
    fixed = [fs.size_px for fs in specs_by_lang.values() if fs.size_px]
    if fixed:
        return max(min_px, min(int(s) for s in fixed))

    box_w = max(1.0, float(bbox["x1"] - bbox["x0"]))
    box_h = max(1.0, float(bbox["y1"] - bbox["y0"]))
    start = max(min_px, int(round(box_h * float(ratio))))
    start = max(start, min_px)

    tmp_img = Image.new("RGB", (max(1,int(box_w)), max(1,int(box_h))), "white")
    d = ImageDraw.Draw(tmp_img)

    for sz in range(start, min_px-1, -1):
        total = 0
        for ch in text:
            lg = detect_lang_char(ch)
            spec = specs_by_lang.get(lg) or specs_by_lang.get("en") or FontSpec()
            f = _load_font(fonts_dir, spec, size_px=sz)
            cw, _ = _measure_char(d, ch, f)
            total += cw
            if total > (box_w * 0.98):
                break
        if total <= (box_w * 0.98):
            return sz
    return max(3, min_px)

# =============================================================================
# Prepare & 2-PASS render
# =============================================================================

def _prepare_items(cfg: OverlayConfig, base_size: Tuple[int,int]) -> List[PreparedItem]:
    W,H = base_size
    out: List[PreparedItem] = []
    for it in cfg.ol_items:
        text = str(it.get("text",""))
        poly = it.get("poly") or []
        if not text or not (isinstance(poly, list) and len(poly) >= 4):
            continue
        poly_px = _scale_poly(poly, W, H) if cfg.common.coord_space == "norm" else [[float(p[0]), float(p[1])] for p in poly]
        bbox = _poly_to_bbox(poly_px)
        if cfg.common.place.padding_px:
            bbox = _expand_bbox(bbox, cfg.common.place.padding_px)
        angle = _angle_from_poly(poly_px)
        out.append(PreparedItem(text=text, poly_px=poly_px, bbox=bbox, angle_deg=angle))
    return out

def _pass1_mask_all(base: Image.Image, cfg: OverlayConfig, prepared: List[PreparedItem]) -> None:
    draw = ImageDraw.Draw(base, "RGBA")
    for p in prepared:
        draw.polygon([(x,y) for (x,y) in p.poly_px], fill=(255,255,255,255))
        if cfg.common.place.padding_px > 0:
            x0,y0,x1,y1 = map(int, [p.bbox["x0"], p.bbox["y0"], p.bbox["x1"], p.bbox["y1"]])
            draw.rectangle([x0,y0,x1,y1], fill=(255,255,255,255))

def _pass2_draw_all(base: Image.Image, cfg: OverlayConfig, prepared: List[PreparedItem]) -> None:
    W,H = base.size
    text_layer = Image.new("RGBA", (W,H), (0,0,0,0))

    for p in prepared:
        specs_by_lang: Dict[str, FontSpec] = {
            "ko": cfg.fonts_lang.get("ko", FontSpec()),
            "ch": cfg.fonts_lang.get("ch", FontSpec()),
            "en": cfg.fonts_lang.get("en", FontSpec()),
        }
        target_px = _auto_font_px_ratio_fit(
            p.text, cfg.fonts_dir, specs_by_lang, p.bbox,
            ratio=cfg.common.font_ratio_box, min_px=cfg.common.font_min_size
        )

        tmp_img = Image.new("RGB", (max(1,int(p.bbox["x1"]-p.bbox["x0"])), max(1,int(p.bbox["y1"]-p.bbox["y0"]))), "white")
        tmp_draw = ImageDraw.Draw(tmp_img)
        fonts_cache: Dict[Tuple[str,int], ImageFont.ImageFont] = {}
        widths: List[int] = []; total_w = 0
        for ch in p.text:
            lg = detect_lang_char(ch)
            spec = specs_by_lang.get(lg) or specs_by_lang["en"]
            key = (lg, target_px)
            if key not in fonts_cache:
                fonts_cache[key] = _load_font(cfg.fonts_dir, spec, size_px=target_px)
            cw,_ = _measure_char(tmp_draw, ch, fonts_cache[key])
            widths.append(cw); total_w += cw

        align = cfg.common.align if cfg.common.align in ("left","center","right") else "center"
        if align == "left":   start_x = p.bbox["x0"]
        elif align == "right":start_x = p.bbox["x1"] - total_w
        else:                 start_x = (p.bbox["x0"] + p.bbox["x1"]) / 2.0 - total_w/2.0
        center_y = (p.bbox["y0"] + p.bbox["y1"]) / 2.0

        sl = Image.new("RGBA", (W,H), (0,0,0,0))
        ds = ImageDraw.Draw(sl)
        x = start_x
        for ch, cw in zip(p.text, widths):
            lg = detect_lang_char(ch)
            spec = specs_by_lang.get(lg) or specs_by_lang["en"]
            f = fonts_cache[(lg, target_px)]
            ds.text((x, center_y), ch, font=f, fill=(spec.color or "#000000"), anchor="lm",
                    stroke_width=int(spec.stroke_px or 0), stroke_fill=spec.stroke_color)
            x += cw

        ax = (p.bbox["x0"] + p.bbox["x1"]) / 2.0 + cfg.common.place.offset_dx
        ay = (p.bbox["y0"] + p.bbox["y1"]) / 2.0 + cfg.common.place.offset_dy
        if abs(p.angle_deg) > 0.1:
            sl = sl.rotate(p.angle_deg, resample=Image.Resampling.BICUBIC, center=(ax, ay), expand=False)

        text_layer.alpha_composite(sl)

    base.alpha_composite(text_layer)

# =============================================================================
# Public API
# =============================================================================
def render_overlay(cfg_like: CfgLike) -> Path:
    cfg = normalize_overlay_cfg(cfg_like)
    if not cfg.file_path:
        raise ValueError("overlay.file_path가 비어있습니다.")

    base, _ = load_image(cfg.file_path, convert="RGBA")
    prepared = _prepare_items(cfg, base.size)

    _pass1_mask_all(base, cfg, prepared)
    _pass2_draw_all(base, cfg, prepared)

    out_path = compute_output_path_for_copy(
        cfg.file_path,
        save_dir=(cfg.ol_save_dir or None),
        suffix=cfg.ol_save_suffix,                 # None/""면 규칙에 따라 자동
        default_suffix_if_same_dir="_overlay",     # 같은 폴더일 때 자동 suffix
    )
    ensure_dir(out_path.parent)
    save_image(base.convert("RGB"), out_path)
    return out_path