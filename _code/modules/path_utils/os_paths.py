# -*- coding: utf-8 -*-
# path_utils/os_paths.py

from pathlib import Path
from typing import Union
import os
import sys

class OSPath:
    def __init__(self):
        self.os_type = os.name

    @staticmethod
    def home() -> Path:
        return Path.home()

    @staticmethod
    def downloads() -> Path:
        """Return the current user's downloads directory as a ``Path``.

        On Windows, the downloads directory typically resides under the user's
        profile directory (``%USERPROFILE%/Downloads``). On POSIX systems it
        generally lives at ``~/Downloads``. If the ``USERPROFILE`` environment
        variable is missing on Windows, this method falls back to using
        :meth:`pathlib.Path.home`.
        """
        # Detect Windows platform via sys.platform; 'win32' covers 32/64-bit.
        if sys.platform.startswith("win"):
            # USERPROFILE should point to the user's home directory on Windows
            user_dir = os.environ.get("USERPROFILE") or str(Path.home())
            return Path(user_dir) / "Downloads"

        # For non-Windows systems (macOS, Linux, etc.) return ~/Downloads
        return Path.home() / "Downloads"
    
    @staticmethod
    def resolve(
        path: Union[str, Path], 
        *, 
        expand_user: bool = True,
        strict: bool = False
    ) -> Path:
        """Convert a path to an absolute, normalized Path object.
        
        Handles string/Path conversion, tilde expansion, relative-to-absolute
        conversion, and path normalization (resolving symlinks, '..' and '.').
        
        Args:
            path: Path to convert (str or Path)
            expand_user: Whether to expand ~ to user home directory (default: True)
            strict: If True, raise error if path doesn't exist (default: False)
        
        Returns:
            Absolute, normalized Path object
        
        Note:
            Unlike fso_utils which assumes paths are already Path objects,
            this method handles all conversion steps:
            1. str → Path conversion
            2. Tilde expansion (if expand_user=True)
            3. Relative → absolute conversion (using cwd)
            4. Path normalization via resolve()
        """
        p = Path(path)
        
        # 1. Expand ~ to user home directory
        if expand_user:
            p = p.expanduser()
        
        # 2. Convert relative paths to absolute (using current working directory)
        if not p.is_absolute():
            p = Path.cwd() / p
        
        # 3. Normalize path (resolve symlinks, '..' and '.')
        return p.resolve(strict=strict)
    
    @staticmethod
    def ensure_absolute(path: Union[str, Path]) -> Path:
        """Ensure path is absolute, converting if necessary.
        
        Alias for resolve() with more explicit naming.
        
        Args:
            path: Path to convert (str or Path)
        
        Returns:
            Absolute Path object
        """
        return OSPath.resolve(path)