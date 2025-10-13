# -*- coding: utf-8 -*-
# data_utils/string_ops.py

from typing import List

class StringOps:
    """Utility functions for working with strings."""
    @staticmethod
    def split_str_path(path: str, sep: str = ".") -> List[str]:
        """Split a string path into parts using the given separator.

        Consecutive separators and empty segments are ignored. For example,

        ``"a.b.c"`` becomes ``["a", "b", "c"]``, and ``"a//b/c"`` with
        ``sep="/"`` becomes ``["a", "b", "c"]``.

        Args:
            path: The string containing separated segments.
            sep: The delimiter used to separate segments. Defaults to a period ``'.'``.

        Returns:
            A list of non-empty segments extracted from ``path``.
        """
        return [p for p in path.split(sep) if p]
