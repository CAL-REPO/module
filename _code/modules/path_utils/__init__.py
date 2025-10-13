# path_utils/__init__.py
"""
path_utils package
-----------------
Public API for OS-specific path helpers. Exposes the ``OSPath`` class and
helper functions for obtaining user-level directories such as the home and
downloads directories.

The UTF-8 BOM marker has been removed to prevent syntax errors when importing
this module.
"""

from __future__ import annotations

from pathlib import Path

from .os_paths import OSPath

__all__ = [
    "OSPath",
    "home",
    "downloads",
]

# Lazy singleton instance of OSPath used by convenience functions below
_os_paths = OSPath()

def home() -> Path:
    """
    Return the current user's home directory as a ``Path``.

    This wraps :meth:`OSPath.home` on a shared instance of :class:`OSPath`.
    """
    return _os_paths.home()

def downloads() -> Path:
    """
    Return the default downloads directory as a ``Path``.

    This wraps :meth:`OSPath.downloads` on a shared instance of :class:`OSPath`.
    """
    return _os_paths.downloads()
