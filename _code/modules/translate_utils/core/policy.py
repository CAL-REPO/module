# -*- coding: utf-8 -*-
"""
Translation policy (Pydantic)
-----------------------------

Defines validated configuration models for the translation pipeline.
- TranslatePolicy: Translate(Adapter) 전용 - 순수 번역 로직 설정
- TranslatorPolicy: Translator(EntryPoint) 전용 - YAML 기반 진입점 설정

Integrates with cfg_utils.ConfigLoader so callers can pass YAML paths,
dicts, or already-built models.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

from pydantic import BaseModel, Field, model_validator

from cfg_utils import ConfigLoader, ConfigPolicy
from logs_utils import LogPolicy


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
    """Translate(Adapter) 전용 Policy - 순수 번역 로직 설정
    
    이 Policy는 Translate 클래스에서 사용하며, 번역 실행에 필요한 설정만 포함합니다.
    - provider: 번역 Provider 설정 (deepl, mock 등)
    - zh: 중국어 세그먼트 분할 설정
    - store: 캐싱 및 결과 저장 설정
    - log: 로깅 설정 (Optional, config_loader에서 주입 가능)
    """
    provider: ProviderPolicy = Field(default_factory=ProviderPolicy)
    zh: ZhChunkPolicy = Field(default_factory=ZhChunkPolicy)
    store: StorePolicy = Field(default_factory=StorePolicy)
    log: Optional[LogPolicy] = None  # ✨ logging 설정 (Optional)

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

        # Ensure storage filenames fallback to defaults
        self.store.db_name = self.store.db_name or "translate_cache.sqlite3"
        self.store.tr_name = self.store.tr_name or "translated_text.json"

        return self


class TranslatorPolicy(BaseModel):
    """Translator(EntryPoint) 전용 Policy - YAML 기반 진입점 설정
    
    이 Policy는 Translator 클래스에서 사용하며, EntryPoint 실행에 필요한 설정을 포함합니다.
    - source: 소스 텍스트 로딩 설정 (YAML 파일 또는 직접 텍스트)
    - translate: Translate 내부 Policy (TranslatePolicy 포함, log도 여기 포함)
    """
    source: SourcePolicy = Field(default_factory=SourcePolicy)
    translate: TranslatePolicy = Field(default_factory=TranslatePolicy)

    @staticmethod
    def load(cfg_like: str | Path | dict | BaseModel, *, policy: ConfigPolicy | None = None) -> "TranslatorPolicy":
        """Load TranslatorPolicy from various sources.
        
        Args:
            cfg_like: Configuration source (YAML path, dict, BaseModel instance, etc.)
            policy: ConfigPolicy for advanced loader options
        
        Returns:
            TranslatorPolicy instance
        """
        return ConfigLoader.load(cfg_like, model=TranslatorPolicy, policy=policy)

    @model_validator(mode="after")
    def _derive_source_defaults(self) -> "TranslatorPolicy":
        """Derive default storage directories from source file path."""
        # Default storage directories to the source file parent when absent
        if self.source.file_path:
            base_path = Path(self.source.file_path).expanduser()
            try:
                parent = base_path.resolve().parent
            except Exception:
                parent = base_path.parent
            if not self.translate.store.db_dir:
                self.translate.store.db_dir = str(parent)
            if not self.translate.store.tr_dir:
                self.translate.store.tr_dir = str(parent)

        return self
