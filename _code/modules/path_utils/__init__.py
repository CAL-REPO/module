# -*- coding: utf-8 -*-
# path_utils/__init__.py

from pathlib import Path

from .os_paths import OSPath

__all__ = [
    "OSPath",
    "home",
    "downloads",
]

_os_paths = OSPath()

def home() -> Path:
    """Return the current user's home directory."""
    return _os_paths.home()

def downloads() -> Path:
    """Return the default downloads directory."""
    return _os_paths.downloads()
