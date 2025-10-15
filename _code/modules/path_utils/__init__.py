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
from typing import Union

from .os_paths import OSPath

__all__ = [
    "OSPath",
    "home",
    "downloads",
    "resolve",
    "ensure_absolute",
]

# Lazy singleton instance of OSPath used by convenience functions below
_os_paths = OSPath()

def home() -> Path:
    """Return the current user's home directory as a ``Path``.

    This wraps :meth:`OSPath.home` on a shared instance of :class:`OSPath`.
    """
    return _os_paths.home()

def downloads() -> Path:
    """Return the default downloads directory as a ``Path``.

    This wraps :meth:`OSPath.downloads` on a shared instance of :class:`OSPath`.
    """
    return _os_paths.downloads()

def resolve(
    path: Union[str, Path], 
    *, 
    expand_user: bool = True,
    strict: bool = False
) -> Path:
    """Convert a path to an absolute, normalized Path object.
    
    This wraps :meth:`OSPath.resolve` on a shared instance of :class:`OSPath`.
    
    Args:
        path: Path to convert (str or Path)
        expand_user: Whether to expand ~ to user home directory (default: True)
        strict: If True, raise error if path doesn't exist (default: False)
    
    Returns:
        Absolute, normalized Path object
    """
    return _os_paths.resolve(path, expand_user=expand_user, strict=strict)

def ensure_absolute(path: Union[str, Path]) -> Path:
    """Ensure path is absolute, converting if necessary.
    
    This wraps :meth:`OSPath.ensure_absolute` on a shared instance of :class:`OSPath`.
    
    Args:
        path: Path to convert (str or Path)
    
    Returns:
        Absolute Path object
    """
    return _os_paths.ensure_absolute(path)
