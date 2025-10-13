# -*- coding: utf-8 -*-
"""
modules.translate — Translation runner (dataclass defaults, YAML-aware)
======================================================================

구성(ocr/overlay와 동일한 구조):
1) Dataclasses & Types
2) Config Load & Normalize (YAML/DICT → 내부 스키마)
3) Provider: DeepLTranslator (캐시/중문 분할/phrase map/next-gen 모델)
4) Runner & Public API: run_translate / translate_cfg / translate_cfg_one
5) CLI

환경:
- DeepL SDK: pip install deepl
- API Key: 환경변수 DEEPL_API_KEY (or DEEP_L_API_KEY)
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple, Union, Iterable
from pathlib import Path
import hashlib
import sqlite3
import json
import os
import re
import deepl  # type: ignore

from modules.yamlutil import section_or_root, load_yaml  # type: ignore
from modules.datautil import as_list  # type: ignore
from modules.fileio import ensure_dir, parent_dir_of  # type: ignore


# =============================================================================
# 1) Dataclasses & Types
# =============================================================================

@dataclass
class TranslateSourceDefaults:
    text: List[str] = field(default_factory=list)   # 번역 대상 문장 리스트
    file_path: str = ""                             # 또는 파일에서 읽기(UTF-8)


@dataclass
class TranslateProviderDefaults:
    provider: str = "deepl"
    target_lang: str = "KO"
    source_lang: str = "AUTO"
    model_type: str = "prefer_quality_optimized"  # "latency_optimized" | "quality_optimized" | "prefer_quality_optimized"
    timeout: int = 30


@dataclass
class TranslateZhChunkingDefaults:
    mode: str = "clause"    # "off" | "clause"
    max_len: int = 48
    min_len: int = 80
    phrase_map: List[Tuple[str, str]] = field(default_factory=list)  # [["慎拍","谨慎下单"], ...]


@dataclass
class TranslateStoreDefaults:
    save_db: bool = True
    db_dir: str = ""
    db_name: str = "translate_cache.sqlite3"
    save_tr: bool = False
    tr_dir: str = ""
    tr_name: str = "translated_text.json"


@dataclass
class TranslateDefaults:
    source: TranslateSourceDefaults = field(default_factory=TranslateSourceDefaults)
    provider: TranslateProviderDefaults = field(default_factory=TranslateProviderDefaults)
    zh: TranslateZhChunkingDefaults = field(default_factory=TranslateZhChunkingDefaults)
    store: TranslateStoreDefaults = field(default_factory=TranslateStoreDefaults)
    debug: bool = False


CfgLike = Union[None, str, Path, Dict[str, Any]]

# =============================================================================
# 2) Config Load & Normalize
# =============================================================================

def _translate_section(cfg_like: CfgLike) -> Dict[str, Any]:
    """
    YAML 경로/DICT에서 translate 섹션만 추출. 섹션이 없으면 루트를 사용.
    """
    if cfg_like is None:
        return {}
    if isinstance(cfg_like, (str, Path)):
        root = load_yaml(str(cfg_like)) or {}
        return section_or_root(root, "translate")
    if isinstance(cfg_like, dict):
        return section_or_root(cfg_like, "translate")
    raise TypeError("translate cfg must be dict|str|Path|None")


def _model_type_alias(s: str) -> str:
    s = (s or "").strip().lower()
    alias = {
        "classic": "latency_optimized",
        "next": "quality_optimized",
        "next-gen": "quality_optimized",
        "nextgen": "quality_optimized",
        "prefer_next": "prefer_quality_optimized",
    }
    s = alias.get(s, s)
    if s in {"latency_optimized", "quality_optimized", "prefer_quality_optimized"}:
        return s
    return "prefer_quality_optimized"


def _as_bool(val: Any) -> Optional[bool]:
    if isinstance(val, bool): return val
    if isinstance(val, (int, float)): return bool(val)
    if isinstance(val, str):
        s = val.strip().lower()
        if s in {"1","true","t","yes","y","on"}: return True
        if s in {"0","false","f","no","n","off"}: return False
    return None


def normalize_translate_cfg(cfg_like: CfgLike) -> TranslateDefaults:
    """
    외부 입력(cfg_like)을 TranslateDefaults dataclass로 정규화.
    """
    sec = _translate_section(cfg_like)
    d = TranslateDefaults()

    # -------- source --------
    d.source = TranslateSourceDefaults(
        text=list(as_list(sec.get("text"))) or d.source.text,
        file_path=str(sec.get("file_path", d.source.file_path) or ""),
    )

    # -------- provider --------
    prov = sec.get("provider", d.provider.provider)
    d.provider.provider = str(prov or d.provider.provider).strip().lower()
    d.provider.target_lang = str(sec.get("target_lang", d.provider.target_lang) or d.provider.target_lang)
    d.provider.source_lang = str(sec.get("source_lang", d.provider.source_lang) or d.provider.source_lang)
    if "model_type" in sec:
        d.provider.model_type = _model_type_alias(str(sec.get("model_type") or d.provider.model_type))
    # timeout(optional)
    if "timeout" in sec:
        try:
            d.provider.timeout = int(sec.get("timeout"))  # type: ignore[arg-type]
        except Exception:
            pass

    # -------- zh chunking --------
    zc = sec.get("zh_chunking", {}) or {}
    try:
        mode = str(zc.get("mode", d.zh.mode)).strip().lower()
        if mode not in {"off","clause"}: mode = d.zh.mode
        max_len = int(zc.get("max_len", d.zh.max_len))
        min_len = int(zc.get("min_len", d.zh.min_len))
        d.zh.mode = mode
        d.zh.max_len = max_len
        d.zh.min_len = min_len
    except Exception:
        pass
    # phrase map
    pm = sec.get("zh_phrase_map")
    if isinstance(pm, list):
        pairs: List[Tuple[str, str]] = []
        for x in pm:
            try:
                a, b = x[0], x[1]
                pairs.append((str(a), str(b)))
            except Exception:
                continue
        d.zh.phrase_map = pairs

    # -------- store --------
    sb = _as_bool(sec.get("save_db"))
    if sb is not None: d.store.save_db = sb
    st = _as_bool(sec.get("save_tr"))
    if st is not None: d.store.save_tr = st
    d.store.db_dir = str(sec.get("db_dir", d.store.db_dir) or "")
    d.store.db_name = str(sec.get("db_name", d.store.db_name) or "translate_cache.sqlite3")
    d.store.tr_dir = str(sec.get("tr_dir", d.store.tr_dir) or "")
    d.store.tr_name = str(sec.get("tr_name", d.store.tr_name) or "translated_text.json")

    # -------- debug --------
    d.debug = bool(sec.get("debug", d.debug))

    # -------- defaults based on file_path --------
    if d.source.file_path:
        parent = parent_dir_of(d.source.file_path)
        if not d.store.db_dir:
            d.store.db_dir = str(parent)
        if not d.store.tr_dir:
            d.store.tr_dir = str(parent)

    return d

# =============================================================================
# 3) Provider: DeepLTranslator
# =============================================================================

_CJK_RE = re.compile(r"[\u4E00-\u9FFF]")

def _mostly_zh(text: str, thresh: float = 0.25) -> bool:
    if not text: return False
    cjk = len(_CJK_RE.findall(text))
    return (cjk / max(1, len(text))) >= thresh

def _chunk_clauses(text: str, max_len: int = 48) -> List[str]:
    """중국어 문장을 절/문장 단위로 잘라 max_len을 넘지 않게 분할."""
    if not text:
        return []
    parts = re.split(r"([。！？!?；;：:])", text)
    chunks: List[str] = []
    buf = ""
    for i in range(0, len(parts), 2):
        seg = parts[i]
        punc = parts[i + 1] if i + 1 < len(parts) else ""
        unit = (seg + punc).strip()
        if not unit:
            continue
        if len(buf) + len(unit) <= max_len:
            buf += unit
        else:
            if buf:
                chunks.append(buf)
            if len(unit) <= max_len:
                buf = unit
            else:
                sub = re.split(r"([,，\s])", unit)
                tmp = ""
                for j in range(0, len(sub), 2):
                    s = sub[j]
                    sp = sub[j + 1] if j + 1 < len(sub) else ""
                    token = (s + sp)
                    if len(tmp) + len(token) <= max_len:
                        tmp += token
                    else:
                        if tmp:
                            chunks.append(tmp)
                        tmp = token
                if tmp:
                    chunks.append(tmp)
                buf = ""
    if buf:
        chunks.append(buf)
    return [c for c in (x.strip() for x in chunks) if c]


def _md5(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


@dataclass
class DeepLTranslator:
    api_key: str
    db_path: Path
    source_lang: str
    target_lang: str
    timeout: int = 30
    chunk_cfg: Dict[str, Any] = field(default_factory=dict)  # {mode,max_len,min_len,phrase_map,save_db}
    model_type: Optional[str] = None

    def __post_init__(self) -> None:
        ensure_dir(self.db_path.parent)
        self._conn = sqlite3.connect(str(self.db_path))
        self._ensure_schema()
        if deepl is None:
            raise ImportError("deepl 라이브러리가 필요합니다. pip install deepl")
        try:
            self._client = deepl.Translator(self.api_key)  # type: ignore[attr-defined]
        except Exception as e:  # type: ignore
            raise RuntimeError(f"DeepL 초기화 실패: {e}")
        self._model_type_used_set: set = set()

    # DB schema
    def _ensure_schema(self) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS translate_cache (
              provider TEXT NOT NULL,
              src_hash TEXT NOT NULL,
              src_lang TEXT NOT NULL,
              tgt_lang TEXT NOT NULL,
              out_text TEXT NOT NULL,
              created_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
              PRIMARY KEY(provider, src_hash, src_lang, tgt_lang)
            )
            """
        )
        self._conn.commit()

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    # Cache ops
    def _get_cache(self, text: str) -> Optional[str]:
        if not (self.chunk_cfg or {}).get("save_db", True):
            return None
        h = _md5(text)
        cur = self._conn.cursor()
        cur.execute(
            "SELECT out_text FROM translate_cache WHERE provider=? AND src_hash=? AND src_lang=? AND tgt_lang=?",
            ("deepl", h, self.source_lang, self.target_lang),
        )
        row = cur.fetchone()
        return row[0] if row else None

    def _put_cache(self, text: str, out_text: str) -> None:
        if not (self.chunk_cfg or {}).get("save_db", True):
            return
        h = _md5(text)
        cur = self._conn.cursor()
        cur.execute(
            "REPLACE INTO translate_cache(provider, src_hash, src_lang, tgt_lang, out_text) VALUES (?,?,?,?,?)",
            ("deepl", h, self.source_lang, self.target_lang, out_text),
        )
        self._conn.commit()

    # Pre-process
    def _apply_phrase_map(self, s: str) -> str:
        pm = (self.chunk_cfg or {}).get("phrase_map") or []
        if not pm:
            return s
        try:
            for pair in pm:
                if not (isinstance(pair, (list, tuple)) and len(pair) >= 2):
                    continue
                pat, rep = str(pair[0]), str(pair[1])
                s = s.replace(pat, rep)
        except Exception:
            pass
        return s

    # Translate
    def _translate_one(self, text: str) -> str:
        if not text:
            return ""
        text = self._apply_phrase_map(text)
        zc = self.chunk_cfg or {}
        if zc.get("mode") == "clause" and _mostly_zh(text):
            min_len = int(zc.get("min_len") or 80)
            if len(text) >= min_len:
                max_len = int(zc.get("max_len") or 48)
                pieces = _chunk_clauses(text, max_len=max_len)
                outs: List[str] = []
                for p in pieces:
                    outs.append(self._translate_one_atomic(p))
                return "".join(outs)
        return self._translate_one_atomic(text)

    def _translate_one_atomic(self, text: str) -> str:
        cached = self._get_cache(text)
        if cached is not None:
            return cached
        try:
            res = self._client.translate_text(  # type: ignore[attr-defined]
                text,
                target_lang=self.target_lang,
                source_lang=None if self.source_lang == "AUTO" else self.source_lang,
                model_type=self.model_type if self.model_type else None,  # type: ignore
            )
            out = res.text if hasattr(res, "text") else str(res)  # type: ignore
            try:
                used = getattr(res, "model_type_used", None)
                if used:
                    self._model_type_used_set.add(str(used))
            except Exception:
                pass
        except Exception as e:
            raise RuntimeError(f"DeepL 번역 실패: {e}")
        try:
            self._put_cache(text, out)
        except Exception:
            pass
        return out

    def translate(self, texts: Iterable[str]) -> List[str]:
        outs: List[str] = []
        for t in texts:
            outs.append(self._translate_one(t))
        return outs

# =============================================================================
# 4) Runner & Public API
# =============================================================================

def run_translate(cfg_like: CfgLike) -> Tuple[List[str], Optional[Path], Dict[str, Any]]:
    """
    cfg_like (YAML 경로/DICT) → 번역 실행 → (translated_texts, saved_json_path, meta)
    - text 리스트 또는 file_path(UTF-8) 중 하나는 필수.
    - db_dir/tr_dir은 file_path가 있을 때 자동 채움. text만 있을 때는 제공 필요.
    """
    cfg = normalize_translate_cfg(cfg_like)

    # provider
    provider = (cfg.provider.provider or "deepl").strip().lower()
    if provider not in {"deepl"}:
        raise ValueError(f"Unsupported translate.provider: {provider}")

    # 소스 텍스트
    texts: List[str] = list(cfg.source.text)
    src_label = "text"
    if cfg.source.file_path:
        p = Path(cfg.source.file_path)
        if not p.exists():
            raise FileNotFoundError(f"file not found: {cfg.source.file_path}")
        texts = [p.read_text(encoding="utf-8")]
        src_label = str(p)

    if not texts:
        raise ValueError("translate.text 또는 translate.file_path 중 하나는 필수입니다.")

    # DB 경로
    if not cfg.store.db_dir:
        raise ValueError("translate.db_dir 가 필요합니다. (file_path가 있으면 자동 채워집니다)")
    db_path = Path(cfg.store.db_dir) / (cfg.store.db_name or "translate_cache.sqlite3")
    ensure_dir(db_path.parent)

    # API Key
    api_key = os.environ.get("DEEPL_API_KEY") or os.environ.get("DEEP_L_API_KEY")
    if not api_key:
        raise EnvironmentError("DEEPL_API_KEY 환경 변수를 설정하세요.")

    # chunk cfg dict
    chunk_cfg = {
        "mode": cfg.zh.mode,
        "max_len": cfg.zh.max_len,
        "min_len": cfg.zh.min_len,
        "phrase_map": list(cfg.zh.phrase_map),
        "save_db": bool(cfg.store.save_db),
    }

    translator = DeepLTranslator(
        api_key=api_key,
        db_path=db_path,
        source_lang=str(cfg.provider.source_lang or "AUTO"),
        target_lang=str(cfg.provider.target_lang or "KO"),
        timeout=int(cfg.provider.timeout or 30),
        chunk_cfg=chunk_cfg,
        model_type=str(cfg.provider.model_type or "").strip() or None,
    )

    try:
        outs = translator.translate(texts)
    finally:
        translator.close()

    # 선택 저장
    saved_path: Optional[Path] = None
    if bool(cfg.store.save_tr):
        if not cfg.store.tr_dir:
            raise ValueError("translate.tr_dir 가 필요합니다. (file_path가 있으면 자동 채워집니다)")
        ensure_dir(cfg.store.tr_dir)
        saved_path = Path(cfg.store.tr_dir) / (cfg.store.tr_name or "translated_text.json")
        payload = {
            "provider": provider,
            "source": src_label,
            "source_lang": cfg.provider.source_lang,
            "target_lang": cfg.provider.target_lang,
            "model_type": cfg.provider.model_type,
            "texts": texts,
            "translated": outs,
            "zh_chunking": {
                "mode": cfg.zh.mode, "max_len": cfg.zh.max_len, "min_len": cfg.zh.min_len
            },
            "zh_phrase_map": list(cfg.zh.phrase_map),
        }
        with saved_path.open("w", encoding="utf-8") as fp:
            json.dump(payload, fp, ensure_ascii=False, indent=2)

    meta = {
        "provider": provider,
        "source": src_label,
        "num_texts": len(texts),
        "target_lang": cfg.provider.target_lang,
        "source_lang": cfg.provider.source_lang,
        "model_type": cfg.provider.model_type,
        "db_path": str(db_path),
        "save_tr": bool(cfg.store.save_tr),
        "translated_path": str(saved_path) if saved_path else None,
    }

    return outs, saved_path, meta

def translate_cfg(texts: Iterable[str], cfg_like: CfgLike) -> List[str]:
    cfg = normalize_translate_cfg(cfg_like)
    tmp = asdict(cfg)  # dataclass → dict
    # 섹션 형태로 래핑하여 run_translate에 전달
    tmp["source"]["text"] = list(texts)
    tmp["source"]["file_path"] = ""
    outs, _, _ = run_translate({"translate": tmp})  # type: ignore
    return outs

def translate_cfg_one(text: str, cfg_like: CfgLike) -> str:
    return translate_cfg([text], cfg_like)[0] if text is not None else ""