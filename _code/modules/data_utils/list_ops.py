# -*- coding: utf-8 -*-
# data_utils/list_ops.py

from __future__ import annotations

from typing import Any, List, Iterable

class ListOps:
    """Utility functions for list operations."""
    @staticmethod
    def dedupe_keep_order(seq: Iterable[Any]) -> List[Any]:
        """Remove duplicates from a sequence while preserving the original order.

        Args:
            seq: An iterable possibly containing duplicate values.

        Returns:
            A list of unique values in the order they first appeared in ``seq``.
        """
        seen: set[Any] = set()
        out: List[Any] = []
        for x in seq:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out





