# -*- coding: utf-8 -*-
"""ItemSaver - FSONamePolicy 기반 파일 저장
================================================

ItemPostProcessor가 생성한 ItemList를 파일로 저장합니다.

책임:
- ItemList.directory, name (FSONamePolicy), ops (FSOOpsPolicy)에 따라 파일 저장
- URL 다운로드 (image, file)
- 텍스트 저장 (text)
- 저장 결과 반환 (ItemSaveSummary)

Naming:
- SyncItemSaver: 동기 버전
- AsyncItemSaver: 비동기 버전 (향후)
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .fetcher import SyncHTTPFetcher
from crawl_utils.core.interfaces import CrawlSaver

from crawl_utils.core.policy import ItemList, ItemSaveResult, ItemSaveSummary
from fso_utils.core.policy import FSONamePolicy


class SyncItemSaver(CrawlSaver):
    def __init__(self):
        """ItemSaver 초기화"""
        pass

    def save_items(self, items: Sequence[ItemList], fetcher=None) -> ItemSaveSummary:
        """ItemList 리스트를 파일로 저장
        
        Args:
            items: 저장할 ItemList 리스트
            fetcher: HTTP fetcher (기본값: SyncHTTPFetcher)
        
        Returns:
            ItemSaveSummary: kind별 저장 결과
        """
        fetcher = fetcher or SyncHTTPFetcher()
        results: Dict[str, List[ItemSaveResult]] = {"image": [], "text": [], "file": []}

        print(f"[DEBUG ItemSaver] Saving {len(items)} items")  # 🔍 디버깅
        
        for idx, item in enumerate(items):
            print(f"[DEBUG ItemSaver] Item {idx}: kind={item.kind}, directory={item.directory}, value={str(item.value)[:100]}...")  # 🔍
            
            bucket = results.setdefault(item.kind, [])
            
            # directory 확인
            if not item.directory:
                print(f"[DEBUG ItemSaver] Item {idx}: No directory, skipping")  # 🔍
                bucket.append(ItemSaveResult(Path(), item, status="skipped", detail="No directory"))
                continue

            try:
                path = self._create_path_from_item(item)
                print(f"[DEBUG ItemSaver] Item {idx}: Saving to {path}")  # 🔍
                
                if item.kind == "image":
                    if isinstance(item.value, str):
                        content = fetcher.fetch_bytes(item.value)  # type: ignore
                        path.write_bytes(content)
                    else:
                        path.write_bytes(item.value)
                elif item.kind == "text":
                    path.write_text(str(item.value), encoding="utf-8")
                else:
                    if isinstance(item.value, str):
                        content = fetcher.fetch_bytes(item.value)  # type: ignore
                        path.write_bytes(content)
                    else:
                        path.write_bytes(item.value)
                
                bucket.append(ItemSaveResult(path, item, status="saved"))
            
            except Exception as exc:
                bucket.append(ItemSaveResult(Path(), item, status="failed", detail=str(exc)))

        return ItemSaveSummary(results)

    def _create_path_from_item(self, item: ItemList) -> Path:
        """ItemList에서 경로 생성 (FSONamePolicy 완전 구현)
        
        ItemList 필드:
        - directory: Optional[Path]
        - name: FSONamePolicy (FSO 모듈의 FSONamePolicy)
        - ops: FSOOpsPolicy
        - value: 실제 값 (URL, text, bytes)
        - record_index: 레코드 인덱스 (1-based)
        - item_index: 아이템 인덱스 (1-based)
        
        FSONamePolicy 필드 (예시):
        - prefix: str = ""
        - name: str = ""
        - suffix: str = ""
        - tail: str = ""
        - tail_mode: str = "none"  # "none", "counter", "date", "datetime"
        - delimiter: str = "_"
        - extension: str = ""
        """
        # 1. 디렉토리 결정 및 생성
        directory = item.directory if item.directory else Path("output")
        directory.mkdir(parents=True, exist_ok=True)
        
        # 2. FSONamePolicy에서 파일명 생성
        filename = self._build_filename_from_fso_policy(item)
        
        # 3. 경로 생성
        path = directory / filename
        
        # 4. ensure_unique 처리
        if hasattr(item.name, 'ensure_unique') and item.name.ensure_unique:
            path = self._ensure_unique_path(path)
        
        return path

    def _build_filename_from_fso_policy(self, item: ItemList) -> str:
        """FSONamePolicy로 파일명 생성
        
        구성: {prefix}{delimiter}{name}{delimiter}{suffix}{delimiter}{tail}.{extension}
        
        Args:
            item: ItemList (name 필드가 FSONamePolicy)
        
        Returns:
            파일명 (확장자 포함)
        """
        name_policy: FSONamePolicy = item.name
        
        parts = []
        delimiter = getattr(name_policy, 'delimiter', '_')
        
        # 1. prefix
        prefix = getattr(name_policy, 'prefix', '')
        if prefix:
            parts.append(prefix)
        
        # 2. name (필수)
        name = getattr(name_policy, 'name', '')
        if not name:
            # name이 없으면 record/item index 사용
            name = f"item_{item.record_index}_{item.item_index}"
        parts.append(name)
        
        # 3. suffix
        suffix = getattr(name_policy, 'suffix', '')
        if suffix:
            parts.append(suffix)
        
        # 4. tail
        tail = getattr(name_policy, 'tail', '')
        if tail:
            parts.append(tail)
        
        # 5. tail_mode (자동 꼬리말)
        tail_mode = getattr(name_policy, 'tail_mode', 'none')
        if tail_mode == 'counter':
            parts.append(str(item.item_index))
        elif tail_mode == 'date':
            from datetime import datetime
            parts.append(datetime.now().strftime('%Y%m%d'))
        elif tail_mode == 'datetime':
            from datetime import datetime
            parts.append(datetime.now().strftime('%Y%m%d_%H%M%S'))
        
        # 6. 조합
        stem = delimiter.join(parts)
        
        # 7. extension
        extension = getattr(name_policy, 'extension', '')
        if not extension:
            extension = self._infer_extension(item)
        else:
            extension = extension.lstrip('.')
        
        return f"{stem}.{extension}"

    def _ensure_unique_path(self, path: Path) -> Path:
        """경로가 이미 존재하면 숫자를 붙여 유일하게 만듦
        
        예: file.txt → file_1.txt → file_2.txt
        """
        if not path.exists():
            return path
        
        stem = path.stem
        suffix = path.suffix
        parent = path.parent
        
        counter = 1
        while True:
            new_path = parent / f"{stem}_{counter}{suffix}"
            if not new_path.exists():
                return new_path
            counter += 1

    def _infer_extension(self, item: ItemList) -> str:
        """값에서 확장자 추론"""
        # URL에서 확장자 추출 시도
        if isinstance(item.value, str) and "." in item.value:
            ext = item.value.split(".")[-1].split("?")[0].lower()
            if len(ext) <= 5 and ext.isalnum():
                return ext
        
        # kind 기본값
        return {"image": "jpg", "text": "txt", "file": "bin"}.get(item.kind, "dat")


class AsyncItemSaver:
    """비동기 ItemSaver (향후 구현)"""
    pass


__all__ = ["SyncItemSaver", "AsyncItemSaver"]
