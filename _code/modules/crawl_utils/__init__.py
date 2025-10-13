"""Compatibility facade for the legacy :mod:`crawl_utils` package.

This shim simply re-exports the refactored implementation that lives under
``crawl_refactor`` so that existing imports continue to function without
modification.
"""

from __future__ import annotations

from typing import Any

import crawl_refactor as _impl

__all__ = list(getattr(_impl, "__all__", [])) or [
    name for name in dir(_impl) if not name.startswith("_")
]

for _name in __all__:
    globals()[_name] = getattr(_impl, _name)

def __getattr__(name: str) -> Any:
    """Delegate attribute access to :mod:`crawl_refactor`."""
    return getattr(_impl, name)


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(dir(_impl)))
