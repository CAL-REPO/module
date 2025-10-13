# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union, Dict, Any
import os
from modules.yamlutil import load_yaml, load_paths_cfg, normalize_with_placeholders

PathLike = Union[str, os.PathLike[str], Path]

_ENV = "CASHOP_PATHS"
_CFG: Optional[dict] = None
_CFG_FILE: Optional[Path] = None

# -----------------------------------------------------------------------------
# 내부: YAML 경로/로드
# -----------------------------------------------------------------------------
def _cfg_file(paths_yaml: Optional[PathLike] = None) -> Path:
    """환경변수 CASHOP_PATHS 또는 인자로 받은 경로를 사용."""
    global _CFG_FILE
    if paths_yaml:
        p = Path(paths_yaml).expanduser()
        if not p.is_file():
            raise FileNotFoundError(f"paths YAML not found: {p}")
        _CFG_FILE = p
        return _CFG_FILE
    if _CFG_FILE is not None:
        return _CFG_FILE

    val = os.getenv(_ENV)
    if not val:
        raise EnvironmentError(
            f"환경변수 '{_ENV}' 가 설정되지 않았습니다. "
            f"(예: setx {_ENV} \"M:\\...\\configs\\paths.local.yaml\")"
        )
    p = Path(val).expanduser()
    if not p.is_file():
        raise FileNotFoundError(f"{_ENV} 가 가리키는 파일이 존재하지 않습니다: {p}")
    _CFG_FILE = p
    return _CFG_FILE


def _load_cfg(paths_yaml: Optional[PathLike] = None, refresh: bool = False) -> dict:
    """paths.local.yaml 로드 + {}/${} 치환 + *_dir 절대경로화 (자체 맵으로 치환)."""
    global _CFG
    if _CFG is not None and not refresh:
        return _CFG

    p = _cfg_file(paths_yaml)
    raw = load_yaml(p)
    cfg = normalize_with_placeholders(raw, vars_map=raw, root_key="root", dir_suffix="_dir", pass_count=2)
    _CFG = cfg
    return _CFG


# -----------------------------------------------------------------------------
# 공개: 컨텍스트/접근자
# -----------------------------------------------------------------------------
def refresh(paths_yaml: Optional[PathLike] = None) -> None:
    _load_cfg(paths_yaml, refresh=True)

def cfg(paths_yaml: Optional[PathLike] = None) -> dict:
    return _load_cfg(paths_yaml, refresh=False)

def get(key: str, default: Any = None, *, paths_yaml: Optional[PathLike] = None) -> Any:
    return cfg(paths_yaml).get(key, default)

def path(key: str, *, paths_yaml: Optional[PathLike] = None) -> Path:
    c = cfg(paths_yaml)
    if key not in c or not str(c[key]).strip():
        raise KeyError(f"paths.local.yaml 키 없음: {key}")
    return Path(str(c[key])).resolve()

class _PathsProxy:
    """
    프로젝트 전용 paths 컨텍스트.
    - paths_yaml를 명시하지 않으면 ENV CASHOP_PATHS로부터 읽음
    - .cfg()는 항상 '정규화된 dict' 반환(플레이스홀더 無, 절대경로化)
    """
    def __init__(self, paths_yaml: Optional[Union[str, Path]] = None):
        self._yaml = str(paths_yaml) if paths_yaml else os.environ.get(_ENV, "")
        if not self._yaml:
            raise ValueError(f"{_ENV} 환경변수 또는 paths_yaml 인자가 필요합니다.")
        self._cfg: Optional[Dict[str, Any]] = None

    def cfg(self) -> Dict[str, Any]:
        if self._cfg is None:
            self._cfg = load_paths_cfg(self._yaml)  # ← yamlutil에 위임
        return self._cfg

    # 편의: get / path / refresh
    def get(self, key: str, default: Any = None) -> Any:
        return self.cfg().get(key, default)

    def refresh(self) -> Dict[str, Any]:
        self._cfg = load_paths_cfg(self._yaml)
        return self._cfg

# 기본 컨텍스트(ENV 사용)
P = _PathsProxy(os.environ.get(_ENV, "")) if os.environ.get(_ENV) else None


# -----------------------------------------------------------------------------
# 이미지 디렉터리 (신규 키만, 폴백 없음)
# -----------------------------------------------------------------------------
def get_img_dir(
    kind: str,
    *,
    cas: Optional[str] = None,
    create: bool = False,
    paths_yaml: Optional[PathLike] = None,
) -> Path:
    """
    kind (필수 키):
      - "data_images"  ->  output_data_images_dir / <CAS>
      - "public"       ->  public_img_dir
      - "public_tr"    ->  public_img_tr_dir / <CAS>
      - "public_rm"    ->  public_img_rm_dir / <CAS>
      - "public_final" ->  public_img_final_dir / <CAS>
    """
    c = cfg(paths_yaml)

    key_map = {
        "data_images":  "output_data_images_dir",
        "public":       "public_img_dir",
        "public_tr":    "public_img_tr_dir",
        "public_rm":    "public_img_rm_dir",
        "public_final": "public_img_final_dir",
    }
    if kind not in key_map:
        raise ValueError(f"Unknown kind for get_img_dir: {kind}")

    base_key = key_map[kind]
    if base_key not in c or not str(c[base_key]).strip():
        raise KeyError(f"paths.local.yaml 필수 키가 없습니다: {base_key}")

    base = Path(str(c[base_key])).resolve()
    out = base if kind == "public" else base / (cas or "")
    if create:
        out.mkdir(parents=True, exist_ok=True)
    return out.resolve()
