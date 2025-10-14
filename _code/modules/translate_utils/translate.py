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
from typing import List

from modules.cfg_utils import ConfigPolicy
from modules.log_utils import LogManager, LogPolicy

from .policy import TranslatePolicy
from .translator import translate_with_policy


CfgInput = str | Path | dict | TranslatePolicy


def _ensure_policy(cfg_like: CfgInput, cfg_policy: ConfigPolicy | None) -> TranslatePolicy:
    if isinstance(cfg_like, TranslatePolicy):
        return cfg_like
    policy = cfg_policy or ConfigPolicy()
    return TranslatePolicy.load(cfg_like, policy=policy)


def translate_cfg(
    cfg_like: CfgInput,
    *,
    cfg_policy: ConfigPolicy | None = None,
    log_policy: LogPolicy | None = None,
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

    model = _ensure_policy(cfg_like, cfg_policy)
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


def translate_cfg_one(
    cfg_like: CfgInput,
    *,
    cfg_policy: ConfigPolicy | None = None,
    log_policy: LogPolicy | None = None,
    logger=None,
    logger_name: str = "Translate",
) -> str:
    """Translate a single text using configuration input."""

    result = translate_cfg(
        cfg_like,
        cfg_policy=cfg_policy,
        log_policy=log_policy,
        logger=logger,
        logger_name=logger_name,
    )
    return result[0] if result else ""


__all__ = ["translate_cfg", "translate_cfg_one", "TranslatePolicy"]
