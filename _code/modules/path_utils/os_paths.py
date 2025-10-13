# -*- coding: utf-8 -*-
# path_utils/os_paths.py

from pathlib import Path
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
        """
        Return the current user's downloads directory as a ``Path``.

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