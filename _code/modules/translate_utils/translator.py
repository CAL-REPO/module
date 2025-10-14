# -*- coding: utf-8 -*-
"""
Translation orchestration driven by :class:`TranslatePolicy`.

Manages source acquisition, phrase mapping, optional chunking, caching and
structured output for the DeepL provider.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from modules.data_utils import ListOps, StringOps
from modules.data_utils.db_ops import SQLiteKVStore
from modules.fso_utils import ExistencePolicy, FSOOps, FSOOpsPolicy
from modules.fso_utils.core.io import FileReader
from modules.log_utils import DummyLogger
from modules.structured_io import json_fileio

from .policy import TranslatePolicy
from .provider import DeepLClient


def _read_texts_from_file(path: str) -> List[str]:
    fp = Path(path)
    try:
        reader = FileReader(fp)
        return [line.strip() for line in reader.read_text().splitlines() if line.strip()]
    except FileNotFoundError:
        return []


def _apply_phrase_map(text: str, phrase_map: List[Tuple[str, str]]) -> str:
    out = text
    tuples: List[Tuple[str, str]] = []
    for pair in phrase_map:
        try:
            src, dst = pair[0], pair[1]
        except (IndexError, TypeError):
            continue
        tuples.append((str(src), str(dst)))
    for src, dst in ListOps.dedupe_keep_order(tuples):
        if src:
            out = out.replace(src, dst)
    return out


def _cache_key(src: str, target_lang: str, model: str) -> str:
    return SQLiteKVStore.make_key(src, target_lang, model)


def _translate_batch(client: DeepLClient, texts: List[str], *, target_lang: str, source_lang: str) -> List[str]:
    return client.translate(texts, target_lang=target_lang, source_lang=source_lang)


def translate_with_policy(model: TranslatePolicy, *, logger=None) -> List[str]:
    """Execute translation workflow for a :class:`TranslatePolicy`."""

    logger = logger or DummyLogger()
    provider_name = (model.provider.provider or "deepl").strip().lower()
    if provider_name != "deepl":
        raise ValueError(f"Unsupported translation provider: {model.provider.provider}")

    # Gather input texts
    texts = list(model.source.text)
    file_parent: Path | None = None
    if model.source.file_path:
        try:
            file_parent = Path(model.source.file_path).expanduser().resolve().parent
        except Exception:
            file_parent = Path(model.source.file_path).expanduser().parent
        if not texts:
            texts = _read_texts_from_file(model.source.file_path)
    if not texts:
        return []

    client = DeepLClient(api_key=None, timeout=model.provider.timeout, model_type=model.provider.model_type)

    db: SQLiteKVStore | None = None
    results: List[str] = []
    try:
        if model.store.save_db:
            db_dir = Path(model.store.db_dir) if model.store.db_dir else (file_parent or Path.cwd())
            db_path = db_dir / (model.store.db_name or "translate_cache.sqlite3")
            db = SQLiteKVStore(db_path).open()

        for src in texts:
            prepared = _apply_phrase_map(src, model.zh.phrase_map)

            if (
                model.zh.mode == "clause"
                and len(prepared) >= model.zh.min_len
                and StringOps.mostly_zh(prepared)
            ):
                parts = StringOps.chunk_clauses(prepared, max_len=model.zh.max_len)
            else:
                parts = [prepared]

            translated_parts: List[str] = []
            for part in parts:
                key = _cache_key(part, model.provider.target_lang, model.provider.model_type)
                cached: str | None = db.get(key) if db else None
                if cached is not None:
                    translated_parts.append(cached)
                    continue

                translated = _translate_batch(
                    client,
                    [part],
                    target_lang=model.provider.target_lang,
                    source_lang=model.provider.source_lang,
                )[0]

                if db:
                    db.put(
                        key,
                        src=part,
                        tgt=translated,
                        target_lang=model.provider.target_lang,
                        model=model.provider.model_type,
                    )

                translated_parts.append(translated)

            results.append("".join(translated_parts))

        if model.store.save_tr:
            tr_dir = Path(model.store.tr_dir) if model.store.tr_dir else (file_parent or Path.cwd())
            FSOOps(
                tr_dir,
                policy=FSOOpsPolicy(as_type="dir", exist=ExistencePolicy(create_if_missing=True)),
            )
            tr_path = tr_dir / (model.store.tr_name or "translated_text.json")
            mapping = {src: tgt for src, tgt in zip(texts, results)}
            json_fileio(str(tr_path)).write(mapping)
            logger.info("[translate] saved JSON: {}", tr_path)

    finally:
        if db:
            db.close()

    return results


__all__ = ["translate_with_policy"]

