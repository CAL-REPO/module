
# -*- coding: utf-8 -*-
"""
data_utils.services.string_ops
-----------------------------
Utility functions for string manipulation, cleaning, and chunking.
"""

import re
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
    
    @staticmethod
    def strip_special_chars(text: str) -> str:
        """Remove special characters, keeping only alphanumeric and CJK characters.
        
        Preserves letters (Latin, CJK), digits, and spaces while removing punctuation
        and other special symbols.
        
        Args:
            text: Input string to clean.
            
        Returns:
            Cleaned string with special characters removed.
            
        Examples:
            >>> StringOps.strip_special_chars("Hello, 世界! 123")
            "Hello 世界 123"
            >>> StringOps.strip_special_chars("Price: $99.99 ₩")
            "Price 9999 "
        """
        return re.sub(r"[^\w\s\u3040-\u30ff\u4e00-\u9fff]+", " ", text).strip()

    @staticmethod
    def is_alphanumeric_only(text: str) -> bool:
        """Check if string contains no alphabetic characters (only numbers/symbols).
        
        Used to filter out numeric-only or symbol-only strings that don't contain
        meaningful text content.
        
        Args:
            text: String to check.
            
        Returns:
            True if text contains no letters, False otherwise.
            
        Examples:
            >>> StringOps.is_alphanumeric_only("12345")
            True
            >>> StringOps.is_alphanumeric_only("Hello123")
            False
            >>> StringOps.is_alphanumeric_only("$$$")
            True
        """
        return not re.search(r"[a-zA-Z\u3040-\u30ff\u4e00-\u9fff]", text)

    # ------------------------------------------------------------------
    # Translation‑oriented helpers
    # ------------------------------------------------------------------
    _CJK_RE = re.compile(r"[\u4E00-\u9FFF]")

    @staticmethod
    def mostly_zh(text: str, thresh: float = 0.25) -> bool:
        """Heuristic: whether text is mostly CJK (Chinese/Japanese/Korean).

        Args:
            text: Input string.
            thresh: Fraction threshold of CJK runes vs total length.

        Returns:
            True if CJK fraction >= threshold.
        """
        if not text:
            return False
        cjk = len(StringOps._CJK_RE.findall(text))
        return (cjk / max(1, len(text))) >= thresh

    @staticmethod
    def chunk_clauses(text: str, max_len: int = 48) -> list[str]:
        """Split Chinese text into clause‑sized chunks up to ``max_len``.

        Uses punctuation boundaries first, then falls back to commas/spaces.
        Empty parts are removed and whitespace is trimmed.
        """
        if not text:
            return []
        parts = re.split(r"([。！？!?；;：:])", text)
        chunks: list[str] = []
        buf = ""
        for i in range(0, len(parts), 2):
            seg = parts[i]
            punc = parts[i + 1] if i + 1 < len(parts) else ""
            unit = (seg + punc).strip()
            if not unit:
                continue
            if len(buf) + len(unit) <= max_len:
                buf += unit
            else:
                if buf:
                    chunks.append(buf)
                if len(unit) <= max_len:
                    buf = unit
                else:
                    sub = re.split(r"([,，\s])", unit)
                    tmp = ""
                    for j in range(0, len(sub), 2):
                        s = sub[j]
                        sp = sub[j + 1] if j + 1 < len(sub) else ""
                        token = (s + sp)
                        if len(tmp) + len(token) <= max_len:
                            tmp += token
                        else:
                            if tmp:
                                chunks.append(tmp)
                            tmp = token
                    if tmp:
                        chunks.append(tmp)
                    buf = ""
        if buf:
            chunks.append(buf)
        return [c for c in (x.strip() for x in chunks) if c]
