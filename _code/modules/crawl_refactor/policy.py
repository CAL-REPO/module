# -*- coding: utf-8 -*-
# crawl_refactor/policy.py

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl, model_validator

from .models import ItemKind


class ScrollStrategy(str, Enum):
    NONE = "none"
    PAGINATE = "paginate"
    INFINITE = "infinite"


class WaitHook(str, Enum):
    NONE = "none"
    CSS = "css"
    XPATH = "xpath"


class WaitCondition(str, Enum):
    PRESENCE = "presence"
    VISIBILITY = "visibility"


class ExtractorType(str, Enum):
    DOM = "dom"
    JS = "js"
    API = "api"


class NavigationPolicy(BaseModel):
    base_url: HttpUrl
    url_template: Optional[str] = None
    params: Dict[str, str | int | float] = Field(default_factory=dict)
    page_param: str = Field("page", min_length=1)
    start_page: int = Field(1, ge=1)
    max_pages: int = Field(1, ge=1)


class ScrollPolicy(BaseModel):
    strategy: ScrollStrategy = Field(ScrollStrategy.NONE, description="Scroll strategy")
    max_scrolls: int = Field(0, ge=0)
    scroll_pause_sec: float = Field(0.5, ge=0.0)


class ExtractorPolicy(BaseModel):
    type: ExtractorType = Field(ExtractorType.DOM, description="Extractor type")
    item_selector: Optional[str] = None
    js_snippet: Optional[str] = Field(None, description="Custom JS snippet for JS extractor")
    api_endpoint: Optional[str] = None
    api_method: str = Field("GET", pattern="^[A-Z]+$")
    payload: Optional[Dict] = None


class WaitPolicy(BaseModel):
    hook: WaitHook = Field(WaitHook.NONE, description="Wait hook type")
    selector: Optional[str] = None
    timeout_sec: float = Field(5.0, ge=0.0)
    condition: WaitCondition = Field(
        WaitCondition.PRESENCE,
        description="Wait condition to satisfy (presence/visibility).",
    )


class HttpSessionPolicy(BaseModel):
    use_browser_headers: bool = Field(False, description="Load headers from browser session JSON")
    session_json_path: Optional[Path] = Field(None, description="Path to Firefox session JSON (expects {'headers': {...}})")
    headers: Dict[str, str] = Field(default_factory=dict, description="Extra static headers")


class NormalizationRule(BaseModel):
    kind: ItemKind
    source: str = Field(..., description="Dot-path to value within extractor record.")
    section_field: Optional[str] = Field(None, description="Dot-path for section grouping.")
    static_section: Optional[str] = None
    name_template: Optional[str] = Field(None, description="Format string for output names.")
    extension: Optional[str] = None
    explode: bool = Field(True, description="Treat iterable values as multiple items.")
    allow_empty: bool = Field(False, description="Keep empty values.")


class NormalizationPolicy(BaseModel):
    rules: List[NormalizationRule] = Field(default_factory=list)


def _default_output_root() -> Path:
    return Path.cwd() / "_output" / "crawl"


class StorageTargetPolicy(BaseModel):
    base_dir: Path = Field(default_factory=_default_output_root)
    sub_dir: Optional[str] = None
    name_template: str = Field("{section}_{index}", description="Default filename template.")
    extension: Optional[str] = None
    ensure_unique: bool = True

    @model_validator(mode="after")
    def ensure_exists(self):
        target = self.base_dir / (self.sub_dir or "")
        target.mkdir(parents=True, exist_ok=True)
        return self


class StoragePolicy(BaseModel):
    image: Optional[StorageTargetPolicy] = None
    text: Optional[StorageTargetPolicy] = None
    file: Optional[StorageTargetPolicy] = None

    def target_for(self, kind: ItemKind) -> Optional[StorageTargetPolicy]:
        return getattr(self, kind, None)

    @model_validator(mode="after")
    def validate_any(self):
        if not (self.image or self.text or self.file):
            raise ValueError("StoragePolicy requires at least one target (image/text/file).")
        return self


class CrawlPolicy(BaseModel):
    navigation: NavigationPolicy
    scroll: ScrollPolicy = Field(default_factory=ScrollPolicy) # pyright: ignore[reportArgumentType]
    extractor: ExtractorPolicy = Field(default_factory=ExtractorPolicy) # pyright: ignore[reportArgumentType]
    wait: WaitPolicy = Field(default_factory=WaitPolicy) # pyright: ignore[reportArgumentType]
    normalization: NormalizationPolicy = Field(default_factory=NormalizationPolicy)
    storage: StoragePolicy
    http_session: HttpSessionPolicy = Field(default_factory=HttpSessionPolicy) # pyright: ignore[reportArgumentType]
    concurrency: int = Field(default=2, ge=1, le=32)
    retries: int = Field(default=2, ge=0, le=10)
    retry_backoff_sec: float = Field(1.0, ge=0.0)

