"""Compatibility alias for :mod:`crawl_utils.pipeline`."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_impl = import_module("crawl_refactor.pipeline")

__all__ = [n for n in dir(_impl) if not n.startswith("_")]

for _name in __all__:
    globals()[_name] = getattr(_impl, _name)


def __getattr__(name: str) -> Any:
    return getattr(_impl, name)


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(dir(_impl)))
