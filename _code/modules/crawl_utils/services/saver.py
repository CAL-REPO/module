# -*- coding: utf-8 -*-
# crawl_utils/services/saver.py
# Saver: 정규화된 아이템을 파일로 저장 (Async + Sync 통합)

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from fso_utils.core.path_builder import FSOPathBuilder
from fso_utils.core.policy import FSONamePolicy, FSOOpsPolicy, ExistencePolicy

from .fetcher import HTTPFetcher, SyncHTTPFetcher
from crawl_utils.core.interfaces import CrawlSaver, ResourceFetcher
from crawl_utils.core.models import NormalizedItem, SavedArtifact, SaveSummary
from ..core.policy import StoragePolicy


class FileSaver(CrawlSaver):
    """
    정규화된 아이템을 파일로 저장하는 CrawlSaver 구현체.
    
    NormalizedItem의 kind (image/text/file)에 따라 적절한 저장 방식을 자동 결정:
    - image: URL에서 다운로드 또는 bytes 저장
    - text: 텍스트 파일로 저장
    - file: 바이너리 파일로 저장
    
    StoragePolicy에 정의된 경로 규칙과 파일명 패턴을 적용한다.
    """

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
            delimiter="_",
            tail_mode=None,
            date_format="%Y-%m-%d",
            counter_width=3,
            auto_expand=True,
            sanitize=True,
            case="keep",
        )
        ops_policy = FSOOpsPolicy(
            as_type="file",
            exist=ExistencePolicy(
                must_exist=False,
                create_if_missing=True,
                overwrite=False,
            ),
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


# ============================================================================
# Sync FileSaver: 동기 버전
# ============================================================================


class SyncFileSaver:
    """
    Synchronous FileSaver using direct file I/O.
    
    정규화된 아이템을 파일로 저장하는 동기 버전입니다.
    asyncio.to_thread() 없이 직접 파일 I/O를 수행합니다.
    """

    def __init__(self, policy: StoragePolicy):
        self.policy = policy

    def save_many(
        self,
        items: Sequence[NormalizedItem],
        fetcher: Optional['SyncHTTPFetcher'] = None,
    ) -> SaveSummary:
        """Save multiple items synchronously."""
        fetcher = fetcher or SyncHTTPFetcher()
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
                    self._save_image(path, item, fetcher)
                elif item.kind == "text":
                    self._save_text(path, item)
                else:
                    self._save_binary(path, item, fetcher)
                bucket.append(SavedArtifact(path, item, status="saved"))
            except Exception as exc:  # pragma: no cover - IO heavy
                bucket.append(SavedArtifact(path, item, status="failed", detail=str(exc)))

        return SaveSummary(results)

    def _create_builder(self, target_policy, item: NormalizedItem) -> FSOPathBuilder:
        """Create path builder (same as async version)."""
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
            delimiter="_",
            tail_mode=None,
            date_format="%Y-%m-%d",
            counter_width=3,
            auto_expand=True,
            sanitize=True,
            case="keep",
        )
        ops_policy = FSOOpsPolicy(
            as_type="file",
            exist=ExistencePolicy(
                must_exist=False,
                create_if_missing=True,
                overwrite=False,
            ),
        )
        return FSOPathBuilder(base_dir=base_dir, name_policy=name_policy, ops_policy=ops_policy)

    def _save_image(self, path: Path, item: NormalizedItem, fetcher: 'SyncHTTPFetcher') -> None:
        """Save image synchronously (no asyncio.to_thread)."""
        data = self._resolve_bytes(item, fetcher)
        path.write_bytes(data)  # Direct file I/O

    def _save_text(self, path: Path, item: NormalizedItem) -> None:
        """Save text synchronously (no asyncio.to_thread)."""
        text = item.value if isinstance(item.value, str) else str(item.value)
        path.write_text(text, encoding="utf-8")  # Direct file I/O

    def _save_binary(self, path: Path, item: NormalizedItem, fetcher: 'SyncHTTPFetcher') -> None:
        """Save binary synchronously (no asyncio.to_thread)."""
        data = self._resolve_bytes(item, fetcher)
        path.write_bytes(data)  # Direct file I/O

    def _resolve_bytes(self, item: NormalizedItem, fetcher: 'SyncHTTPFetcher') -> bytes:
        """Resolve bytes from item (sync version)."""
        if isinstance(item.value, (bytes, bytearray)):
            return bytes(item.value)
        if isinstance(item.value, str) and item.value.lower().startswith(("http://", "https://")):
            return fetcher.fetch_bytes(item.value)  # Sync fetch
        if isinstance(item.value, str):
            return item.value.encode("utf-8")
        raise TypeError(f"Unsupported value for binary content: {type(item.value)!r}")

    @staticmethod
    def _default_extension(kind: str) -> str:
        return {"image": "jpg", "text": "txt"}.get(kind, "bin")
