# -*- coding: utf-8 -*-
"""ItemSaver - CrawlItem 파일 저장
================================================

책임:
- CrawlItem를 파일로 저장 (Pipeline 처리 완료된 데이터)
- FSONamePolicy 기반 파일명 생성
- URL 다운로드 (image, file)
- 텍스트 저장 (text)
- 저장 결과 반환 (ItemSaveSummary)

NOT 책임:
- Normalizing (ItemNormalizer 책임)
- KeyPath 처리 (PresetNormalizer 책임)
- merge (Pipeline 책임)
- extension 추론 (Pipeline에서 완료)
- name fallback (Pipeline에서 완료)

안전장치 (Pipeline 실패 시):
- name 없음 → untitled_{record_index}_{item_index}
- extension 없음 → kind별 기본 확장자 (image→jpg, text→txt, file→dat)

설계 원칙:
- 주어진 값 우선 사용 (재추론 없음)
- Pipeline 실패 시에만 fallback
- 단일 책임: 파일 저장만 담당

Naming:
- SyncItemSaver: 동기 버전
- AsyncItemSaver: 비동기 버전 (향후)

Author: GitHub Copilot
Date: 2025-10-27 (v8.1 - fallback 개선)
"""

from pathlib import Path
from typing import Dict, List, Sequence, Optional, Any

# ✅ Fetcher import 제거 (직접 requests 사용)
from crawl_utils.core.interfaces import CrawlSaver

from crawl_utils.core.policy import (
    CrawlItem,
    ItemSaveResult,
    ItemSaveSummary,
    CrawlItemSourcePolicy,
    CrawlItemSavePolicy,
)
import dataclasses
from fso_utils.core.policy import FSONamePolicy




class SyncItemSaver(CrawlSaver):
    """동기 방식 ItemSaver (v8.1 - fallback 개선)
    
    책임:
    - CrawlItem를 파일로 저장
    - FSONamePolicy 기반 파일명 생성
    - URL 다운로드
    
    안전장치 (Pipeline 실패 시):
    - name 없음 → untitled_{record_index}_{item_index}
    - extension 없음 → kind별 기본 확장자
    
    설계 원칙:
    - 주어진 값 우선 사용 (재추론 없음)
    - Pipeline 실패 시에만 fallback
    - 단순 저장만 담당
    
    Examples:
        >>> saver = SyncItemSaver()
        >>> items = [
        ...     CrawlItem(
        ...         kind="image",
        ...         source="https://example.com/image.jpg",
        ...         dir_path=Path("output/images"),
        ...         fso_name=FSONamePolicy(as_type="file", prefix="CAPEA", name="product", extension="jpg"),
        ...         fso_ops=FSOOpsPolicy(as_type="file"),
        ...         record_index=1,
        ...         item_index=1
        ...     )
        ... ]
        >>> summary = saver.save_items(items)
        >>> assert summary["image"][0].status == "saved"
    """
    
    def __init__(self):
        """ItemSaver 초기화"""
        pass

    def save_items(
        self, 
        items: Sequence[CrawlItem], 
        *,
        http_session: Optional[Any] = None
    ) -> ItemSaveSummary:
        """CrawlItem 리스트를 파일로 저장
        
        Args:
            items: 저장할 CrawlItem 리스트 (Pipeline 처리 완료)
            http_session: requests.Session (SessionBridge에서 전달, Cookie 포함)
                         None이면 기본 requests 사용
        
        Returns:
            ItemSaveSummary: kind별 저장 결과
        
        Examples:
            >>> saver = SyncItemSaver()
            >>> items = [...]
            >>> summary = saver.save_items(items, http_session=session_bridge.http_session)
            >>> saved_images = summary["image"]
        """
        # ✅ http_session 직접 사용 (Fetcher 래퍼 제거)
        import requests
        session = http_session or requests.Session()
        
        results: Dict[str, List[ItemSaveResult]] = {"image": [], "text": [], "file": []}
        
        def _to_local_crawlitem(ci: CrawlItem) -> CrawlItem:
            """Create a new CrawlItem instance using the local CrawlItem dataclass
            and pydantic policy model types. This avoids cross-import/class-identity
            issues when ItemNormalizer produced CrawlItem objects from a different
            import path.
            """
            sp = ci.source_policy
            sv = ci.save_policy

            sp_dict = sp.model_dump() if hasattr(sp, 'model_dump') else (sp if isinstance(sp, dict) else {})
            sv_dict = sv.model_dump() if hasattr(sv, 'model_dump') else (sv if isinstance(sv, dict) else {})

            # Build proper policy model instances (local types)
            try:
                sp_model = CrawlItemSourcePolicy(**sp_dict) if isinstance(sp_dict, dict) else sp
            except Exception:
                sp_model = sp

            try:
                sv_model = CrawlItemSavePolicy(**sv_dict) if isinstance(sv_dict, dict) else sv
            except Exception:
                sv_model = sv

            return CrawlItem(source_policy=sp_model, save_policy=sv_model, record_index=ci.record_index, item_index=ci.item_index)

        for idx, item in enumerate(items):
            bucket = results.setdefault(item.kind, [])
            
            # dir_path 확인
            if not item.dir_path:
                bucket.append(ItemSaveResult(Path(), _to_local_crawlitem(item), status="skipped", detail="No dir_path"))
                continue

            try:
                # 파일 경로 생성 (FSONamePolicy 기반)
                path = self._create_path_from_item(item)
                
                # 파일 저장
                if item.kind == "image":
                    if isinstance(item.source, str):
                        # ✅ requests.Session 직접 사용 (Cookie 포함)
                        response = session.get(item.source, timeout=30)
                        response.raise_for_status()
                        content = response.content
                        path.write_bytes(content)  # type: ignore
                    else:
                        path.write_bytes(item.source)
                elif item.kind == "text":
                    path.write_text(str(item.source), encoding="utf-8")
                else:  # file
                    if isinstance(item.source, str):
                        # ✅ requests.Session 직접 사용 (Cookie 포함)
                        response = session.get(item.source, timeout=30)
                        response.raise_for_status()
                        content = response.content
                        path.write_bytes(content)  # type: ignore
                    else:
                        path.write_bytes(item.source)
                
                bucket.append(ItemSaveResult(path, _to_local_crawlitem(item), status="saved"))
            
            except Exception as exc:
                # Use a serializable dict representation of the CrawlItem to satisfy
                # pydantic/dataclass validation in ItemSaveResult
                bucket.append(ItemSaveResult(Path(), _to_local_crawlitem(item), status="failed", detail=str(exc)))

        return ItemSaveSummary(results)

    def _create_path_from_item(self, item: CrawlItem) -> Path:
        """CrawlItem에서 경로 생성 (FSONamePolicy 사용)
        
        Args:
            item: CrawlItem (Pipeline 처리 완료)
        
        Returns:
            Path: 저장할 파일 경로
        
        전제:
        - Pipeline에서 name, extension 처리 완료 가정
        - 처리 실패 시 안전장치 발동
        
        처리 순서:
            1. 디렉토리 생성 (dir_path)
            2. FSONamePolicy 기반 파일명 생성
               - name 없음 → untitled_{record}_{item}
               - extension 없음 → kind별 기본값
            3. ensure_unique 처리 (중복 방지)
        
        Examples:
            >>> item = CrawlItem(
            ...     kind="image",
            ...     source="https://example.com/image.jpg",
            ...     dir_path=Path("output/images"),
            ...     fso_name=FSONamePolicy(as_type="file", prefix="CAPEA", name="product", extension="jpg"),
            ...     fso_ops=FSOOpsPolicy(as_type="file"),
            ...     record_index=1,
            ...     item_index=1
            ... )
            >>> path = saver._create_path_from_item(item)
            >>> # Path("output/images/CAPEA_product.jpg")
        """
        # 1. 디렉토리 결정 및 생성
        directory = item.dir_path if item.dir_path else Path("output")
        directory.mkdir(parents=True, exist_ok=True)
        
        # 2. FSONamePolicy에서 파일명 생성
        filename = self._build_filename_from_fso_policy(item)
        
        # 3. 경로 생성
        path = directory / filename
        
        # 4. ensure_unique 처리
        if hasattr(item.fso_name, 'ensure_unique') and item.fso_name.ensure_unique:
            path = self._ensure_unique_path(path)
        
        return path

    def _build_filename_from_fso_policy(self, item: CrawlItem) -> str:
        """FSONamePolicy로 파일명 생성 (v8.1 - fallback 개선)
        
        구성: {prefix}{delimiter}{name}{delimiter}{suffix}{delimiter}{tail}.{extension}
        
        변경 사항 (v8.1):
        - name fallback → untitled_{record}_{item} (더 명확)
        - extension fallback → kind별 기본 확장자 (image→jpg, text→txt, file→dat)
        
        변경 사항 (v8.0):
        - name fallback 제거 (Pipeline에서 처리 완료)
        - extension 추론 제거 (Pipeline에서 처리 완료)
        - 주어진 값 그대로 사용
        
        Args:
            item: CrawlItem (fso_name 필드가 FSONamePolicy)
        
        Returns:
            파일명 (확장자 포함)
        
        Examples:
            >>> # FSONamePolicy(prefix="CAPEA", name="product", extension="jpg")
            >>> filename = saver._build_filename_from_fso_policy(item)
            >>> # "CAPEA_product.jpg"
            
            >>> # FSONamePolicy(name="", extension="") - Pipeline 실패
            >>> filename = saver._build_filename_from_fso_policy(item)
            >>> # "untitled_1_1.jpg" (record_index=1, item_index=1, kind="image")
        """
        name_policy: FSONamePolicy = item.fso_name
        
        parts = []
        delimiter = getattr(name_policy, 'delimiter', '_')
        
        # 1. prefix
        prefix = getattr(name_policy, 'prefix', '')
        if prefix:
            parts.append(prefix)
        
        # 2. name (필수 - Pipeline에서 처리 완료)
        name = getattr(name_policy, 'name', '')
        if not name:
            # Pipeline 실패 시 안전장치 (record_index, item_index 기반)
            name = f"untitled_{item.record_index}_{item.item_index}"
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
            counter_width = getattr(name_policy, 'counter_width', 3)
            # Format with zero-padding: counter_width=2 → "01", "02", ...
            counter_str = str(item.item_index).zfill(counter_width)
            parts.append(counter_str)
        elif tail_mode == 'date':
            from datetime import datetime
            parts.append(datetime.now().strftime('%Y%m%d'))
        elif tail_mode == 'datetime':
            from datetime import datetime
            parts.append(datetime.now().strftime('%Y%m%d_%H%M%S'))
        
        # 6. 조합
        stem = delimiter.join(parts)
        
        # 7. extension (Pipeline에서 처리 완료)
        extension = getattr(name_policy, 'extension', '')
        if not extension:
            # Pipeline 실패 시 안전장치 (kind 기반 기본 확장자)
            extension_map = {
                "image": "jpg",
                "text": "txt",
                "file": "dat"
            }
            extension = extension_map.get(item.kind, "dat")
        else:
            extension = extension.lstrip('.')
        
        return f"{stem}.{extension}"

    def _ensure_unique_path(self, path: Path) -> Path:
        """경로가 이미 존재하면 숫자를 붙여 유일하게 만듦
        
        예: file.txt → file_1.txt → file_2.txt
        
        Args:
            path: 원본 경로
        
        Returns:
            Path: 유일한 경로
        
        Examples:
            >>> path = Path("output/file.txt")
            >>> unique_path = saver._ensure_unique_path(path)
            >>> # Path("output/file_1.txt") if file.txt exists
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


class AsyncItemSaver:
    """비동기 ItemSaver (향후 구현)"""
    pass


__all__ = ["SyncItemSaver", "AsyncItemSaver"]
