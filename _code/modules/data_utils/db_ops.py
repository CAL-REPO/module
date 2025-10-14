# -*- coding: utf-8 -*-
"""
data_utils/db_ops.py — Lightweight DB ops for key-value caches
----------------------------------------------------------------

Provides a small, extensible SQLite-backed key–value cache suitable for
translation caching and similar workloads. Includes a mixin for stable key
generation.
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import Optional

from modules.fso_utils.core.policy import FSOOpsPolicy, ExistencePolicy
from modules.fso_utils.core.ops import FSOOps


class KVKeyMixin:
    """Helper for generating stable cache keys from arbitrary parts."""

    @staticmethod
    def make_key(*parts: str) -> str:
        h = hashlib.sha256()
        for p in parts:
            h.update((p or "").encode("utf-8", errors="ignore"))
            h.update(b"\0")
        return h.hexdigest()


class SQLiteKVStore(KVKeyMixin):
    """Simple SQLite-based key-value store with a flexible schema.

    The default schema is a ``cache`` table with columns:
    (key TEXT PRIMARY KEY, src TEXT, tgt TEXT, target_lang TEXT, model TEXT).
    Additional columns may be added by providing a custom DDL.
    """

    def __init__(self, path: Path | str, *, table: str = "cache", ddl: Optional[str] = None):
        self.path = Path(path)
        self.table = table
        self.ddl = ddl or (
            f"""
            CREATE TABLE IF NOT EXISTS {table} (
                key TEXT PRIMARY KEY,
                src TEXT NOT NULL,
                tgt TEXT NOT NULL,
                target_lang TEXT NOT NULL,
                model TEXT NOT NULL
            )
            """
        )
        self._con: Optional[sqlite3.Connection] = None

    def open(self) -> "SQLiteKVStore":
        # Ensure path (and parent dir) exist according to policy
        ops = FSOOps(self.path, policy=FSOOpsPolicy(as_type="file", exist=ExistencePolicy(create_if_missing=True)))
        con = sqlite3.connect(str(ops.path))
        con.execute(self.ddl)
        self._con = con
        return self

    def close(self) -> None:
        if self._con is not None:
            self._con.close()
            self._con = None

    # Context manager support
    def __enter__(self) -> "SQLiteKVStore":
        return self.open()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # Basic operations
    @property
    def con(self) -> sqlite3.Connection:
        if self._con is None:
            raise RuntimeError("Database is not open")
        return self._con

    def get(self, key: str) -> Optional[str]:
        cur = self.con.execute(f"SELECT tgt FROM {self.table} WHERE key=?", (key,))
        row = cur.fetchone()
        return row[0] if row else None

    def put(self, key: str, *, src: str, tgt: str, target_lang: str, model: str) -> None:
        self.con.execute(
            f"INSERT OR REPLACE INTO {self.table}(key, src, tgt, target_lang, model) VALUES(?,?,?,?,?)",
            (key, src, tgt, target_lang, model),
        )
        self.con.commit()
