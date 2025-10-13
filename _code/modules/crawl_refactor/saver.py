# -*- coding: utf-8 -*-
# crawl_refactor/saver.py

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from fso_utils.path_builder import FSOPathBuilder
from fso_utils.policy import FSONamePolicy, FSOOpsPolicy, ExistencePolicy

from .fetcher import HTTPFetcher
from .interfaces import CrawlSaver, ResourceFetcher
from .models import NormalizedItem, SavedArtifact, SaveSummary
from .policy import StoragePolicy


class StorageDispatcher(CrawlSaver):
    """Persist normalized items using StoragePolicy rules."""

    def __init__(self, policy: StoragePolicy):
        self.policy = policy

    async def save_many(
        self,
        items: Sequence[NormalizedItem],
        fetcher: Optional[ResourceFetcher] = None,
    ) -> SaveSummary:
        fetcher = fetcher or HTTPFetcher()
        results: Dict[str, List[SavedArtifact]] = {"image": [], "text": [], "file": []}

        for item in items:
            bucket = results.setdefault(item.kind, [])
            target_policy = self.policy.target_for(item.kind)
            if not target_policy:
                bucket.append(SavedArtifact(Path(), item, status="skipped", detail="No storage rule for kind"))
                continue

            builder = self._create_builder(target_policy, item)
            path = builder()

            try:
                if item.kind == "image":
                    await self._save_image(path, item, fetcher)
                elif item.kind == "text":
                    await self._save_text(path, item)
                else:
                    await self._save_binary(path, item, fetcher)
                bucket.append(SavedArtifact(path, item, status="saved"))
            except Exception as exc:  # pragma: no cover - IO heavy
                bucket.append(SavedArtifact(path, item, status="failed", detail=str(exc)))

        return SaveSummary(results)

    def _create_builder(self, target_policy, item: NormalizedItem) -> FSOPathBuilder:
        base_dir = target_policy.base_dir / (target_policy.sub_dir or item.kind)
        extension = (item.extension or target_policy.extension or self._default_extension(item.kind)).lstrip(".")
        stem = item.name_hint or target_policy.name_template.format(
            section=item.section,
            index=item.item_index,
            record=item.record_index,
            kind=item.kind,
        )

        name_policy = FSONamePolicy(
            as_type="file",
            name=stem,
            extension=extension,
            ensure_unique=target_policy.ensure_unique,
        )
        ops_policy = FSOOpsPolicy(
            as_type="file",
            exist=ExistencePolicy(create_if_missing=True),
        )
        return FSOPathBuilder(base_dir=base_dir, name_policy=name_policy, ops_policy=ops_policy)

    async def _save_image(self, path: Path, item: NormalizedItem, fetcher: ResourceFetcher) -> None:
        data = await self._resolve_bytes(item, fetcher)
        await asyncio.to_thread(path.write_bytes, data)

    async def _save_text(self, path: Path, item: NormalizedItem) -> None:
        text = item.value if isinstance(item.value, str) else str(item.value)
        await asyncio.to_thread(path.write_text, text, encoding="utf-8")

    async def _save_binary(self, path: Path, item: NormalizedItem, fetcher: ResourceFetcher) -> None:
        data = await self._resolve_bytes(item, fetcher)
        await asyncio.to_thread(path.write_bytes, data)

    async def _resolve_bytes(self, item: NormalizedItem, fetcher: ResourceFetcher) -> bytes:
        if isinstance(item.value, (bytes, bytearray)):
            return bytes(item.value)
        if isinstance(item.value, str) and item.value.lower().startswith(("http://", "https://")):
            return await fetcher.fetch_bytes(item.value)
        if isinstance(item.value, str):
            return item.value.encode("utf-8")
        raise TypeError(f"Unsupported value for binary content: {type(item.value)!r}")

    @staticmethod
    def _default_extension(kind: str) -> str:
        return {"image": "jpg", "text": "txt"}.get(kind, "bin")
