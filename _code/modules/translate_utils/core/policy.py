# -*- coding: utf-8 -*-
"""
Translation policy (Pydantic)
-----------------------------

Defines a validated configuration model for the translation pipeline.
Integrates with cfg_utils.ConfigLoader so callers can pass YAML paths,
dicts, or already-built models.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

from pydantic import BaseModel, Field, model_validator

from cfg_utils import ConfigLoader, ConfigPolicy


class LogConfig(BaseModel):
    """Logging configuration model compatible with logs_utils.LogContextManager"""
    name: str = Field(default="Translator")
    sinks: List[Dict[str, Any]] = Field(default_factory=lambda: [
        {
            "sink_type": "console",
            "level": "INFO",
            "format": "<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | <cyan>{name}</cyan> | <level>{message}</level>",
            "colorize": True
        }
    ])


class SourcePolicy(BaseModel):
    text: List[str] = Field(default_factory=list, description="Texts to translate")
    file_path: str = Field(default="", description="Optional UTF-8 file to read texts from")


class ProviderPolicy(BaseModel):
    provider: str = Field(default="deepl")
    target_lang: str = Field(default="KO")
    source_lang: str = Field(default="AUTO")
    model_type: str = Field(default="prefer_quality_optimized")
    timeout: int = Field(default=30)


class ZhChunkPolicy(BaseModel):
    mode: str = Field(default="clause", description="off|clause")
    max_len: int = Field(default=48)
    min_len: int = Field(default=80)
    phrase_map: List[Tuple[str, str]] = Field(default_factory=list)


class StorePolicy(BaseModel):
    save_db: bool = Field(default=True)
    db_dir: str = Field(default="")
    db_name: str = Field(default="translate_cache.sqlite3")
    save_tr: bool = Field(default=False)
    tr_dir: str = Field(default="")
    tr_name: str = Field(default="translated_text.json")


class TranslatePolicy(BaseModel):
    source: SourcePolicy = Field(default_factory=SourcePolicy)
    provider: ProviderPolicy = Field(default_factory=ProviderPolicy)
    zh: ZhChunkPolicy = Field(default_factory=ZhChunkPolicy)
    store: StorePolicy = Field(default_factory=StorePolicy)
    log_config: Optional[LogConfig] = Field(default=None, description="Logging configuration")
    debug: bool = Field(default=False)

    @staticmethod
    def load(cfg_like: str | Path | dict | BaseModel, *, policy: ConfigPolicy | None = None) -> "TranslatePolicy":
        loader = ConfigLoader(cfg_like, policy=policy)
        return loader.as_model(TranslatePolicy)

    @model_validator(mode="after")
    def _derive_defaults(self) -> "TranslatePolicy":
        # Normalize provider id
        self.provider.provider = (self.provider.provider or "deepl").strip().lower() or "deepl"
        self.provider.model_type = (self.provider.model_type or "prefer_quality_optimized").strip() or "prefer_quality_optimized"

        # Normalize phrase map entries to tuple[str, str]
        normalized_map: List[Tuple[str, str]] = []
        for pair in self.zh.phrase_map:
            try:
                src, dst = pair[0], pair[1]
            except (IndexError, TypeError):
                continue
            normalized_map.append((str(src), str(dst)))
        self.zh.phrase_map = normalized_map

        # Default storage directories to the source file parent when absent
        if self.source.file_path:
            base_path = Path(self.source.file_path).expanduser()
            try:
                parent = base_path.resolve().parent
            except Exception:
                parent = base_path.parent
            if not self.store.db_dir:
                self.store.db_dir = str(parent)
            if not self.store.tr_dir:
                self.store.tr_dir = str(parent)

        # Ensure storage filenames fallback to defaults
        self.store.db_name = self.store.db_name or "translate_cache.sqlite3"
        self.store.tr_name = self.store.tr_name or "translated_text.json"

        return self
