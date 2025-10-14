# -*- coding: utf-8 -*-
"""
Public translation API
-----------------------

Entry points that hydrate :class:`TranslatePolicy` via ``cfg_utils`` and
delegate execution to :func:`translate_with_policy`.  Logging defaults to a
disabled ``LogManager`` so callers can opt in by passing a custom logger or
policy.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Dict

from modules.log_utils import LogManager, LogPolicy
from ..providers.base import Provider


CfgInput = Any


def translate_cfg(
    cfg_like: CfgInput,
    *,
    cfg_policy: Any | None = None,
    log_policy: Any | None = None,
    logger=None,
    logger_name: str = "Translate",
) -> List[str]:
    """Translate according to configuration input.

    Parameters
    ----------
    cfg_like:
        YAML path, mapping, or already-constructed :class:`TranslatePolicy`.
    cfg_policy:
        Optional :class:`ConfigPolicy` used when loading external sources.
    log_policy:
        Optional :class:`LogPolicy` applied when creating a :class:`LogManager`.
    logger:
        Existing logger to reuse. When ``None`` a ``LogManager`` is created
        with ``enabled=False`` by default so no files are touched.
    logger_name:
        Name for the ``LogManager`` instance when one is created.
    """

    # Lazy imports to avoid heavy import-time dependencies
    from .core.policy import TranslatePolicy
    from .translator import translate_with_policy
    from modules.cfg_utils import ConfigLoader, ConfigPolicy

    if isinstance(cfg_like, TranslatePolicy):
        model = cfg_like
    else:
        policy = cfg_policy or ConfigPolicy()
        loader = ConfigLoader(cfg_like, policy=policy)
        model = loader.as_model(TranslatePolicy)

    active_logger = logger
    if active_logger is None:
        manager = LogManager(logger_name, policy=log_policy or LogPolicy(enabled=False))
        active_logger = manager.setup()

    active_logger.info(
        "[translate] target_lang={} source_lang={} items={}",
        model.provider.target_lang,
        model.provider.source_lang,
        len(model.source.text) or (1 if model.source.file_path else 0),
    )

    return translate_with_policy(model, logger=active_logger)


__all__ = ["translate_cfg"]


class Translate:
    """Object-oriented translation facade.

    Usage:
        t = Translate(cfg_like, overrides={"provider.target_lang": "EN"})
        mapping = t.run()

    The result is a dict that maps source text -> translated text.
    """

    def __init__(
        self,
        cfg_like: CfgInput,
        *,
        cfg_policy: Any | None = None,
        log_policy: Any | None = None,
        logger=None,
        overrides: dict | None = None,
        provider: Provider | None = None,
    ):
        self.cfg_like = cfg_like
        # keep user-provided cfg_policy (may be None); default when needed
        self.cfg_policy = cfg_policy
        self.log_policy = log_policy
        self.logger = logger
        self.overrides = overrides or {}
        self.provider = provider

        # Load policy. Accept TranslatePolicy instance or dict without importing
        # heavy cfg_utils at module import time. Only import ConfigLoader when
        # needed (file path or fallback).
        # Load policy. Accept TranslatePolicy instance or dict without importing
        # heavy cfg_utils at module import time. Only import ConfigLoader when
        # needed (file path or fallback).
        from .core.policy import TranslatePolicy

        if isinstance(self.cfg_like, TranslatePolicy):
            self.model = self.cfg_like
        elif isinstance(self.cfg_like, dict):
            # Try to construct directly from dict (fast path, avoids ConfigLoader)
            try:
                self.model = TranslatePolicy(**self.cfg_like)
            except Exception:
                # Fallback to ConfigLoader when direct construction fails
                from modules.cfg_utils import ConfigLoader, ConfigPolicy

                loader = ConfigLoader(self.cfg_like, policy=self.cfg_policy or ConfigPolicy())
                if self.overrides:
                    loader.merge_overrides(self.overrides)
                self.model = loader.as_model(TranslatePolicy)
        elif isinstance(self.cfg_like, (str, Path)):
            from modules.cfg_utils import ConfigLoader, ConfigPolicy

            loader = ConfigLoader(self.cfg_like, policy=self.cfg_policy or ConfigPolicy())
            if self.overrides:
                loader.merge_overrides(self.overrides)
            self.model = loader.as_model(TranslatePolicy)
        else:
            raise TypeError(f"Unsupported cfg_like type: {type(self.cfg_like)}")

        # Ensure logger
        self.active_logger = self.logger
        if self.active_logger is None:
            manager = LogManager("Translate", policy=self.log_policy or LogPolicy(enabled=False))
            self.active_logger = manager.setup()

    def run(self) -> dict[str, str]:
        """Run pipeline and return mapping from source->translated string.

        This calls into the existing translate_with_policy plumbing and then
        zips the original texts with the returned translated strings.
        """
        self.active_logger.info(
            "[translate] target_lang={} source_lang={} items={}",
            self.model.provider.target_lang,
            self.model.provider.source_lang,
            len(self.model.source.text) or (1 if self.model.source.file_path else 0),
        )

        # Prepare source list using the same loader logic so file inputs are respected
    from .services.source_loader import TextSourceLoader

    source_loader = TextSourceLoader(self.model.source)
    payload = source_loader.load()
        sources = payload.texts

    from .translator import translate_with_policy

    results = translate_with_policy(self.model, logger=self.active_logger, provider=self.provider)

        # Map source to result by index (preserves order and handles duplicates)
        mapping: dict[str, str] = {}
        for idx, src in enumerate(sources):
            translated = results[idx] if idx < len(results) else ""
            mapping[str(src)] = translated

        return mapping


__all__.extend(["Translate", "TranslatePolicy"])
