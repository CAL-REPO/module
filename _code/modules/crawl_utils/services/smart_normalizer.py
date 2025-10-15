# -*- coding: utf-8 -*-
# crawl_utils/services/smart_normalizer.py
# 자동 타입 추론 기반 Smart Normalizer

"""
Smart Normalizer
================

type_utils를 사용하여 Rule 없이 자동으로 Dict를 NormalizedItem으로 변환.

기존 DataNormalizer와의 차이점:
- Rule 불필요: 타입 자동 추론
- 간단한 사용: Dict만 전달하면 됨
- 유연성: 키 이름, 값 타입으로 자동 판별
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from type_utils import TypeInferencer, FileType
from type_utils.core.policy import InferencePolicy

from ..core.models import NormalizedItem, ItemKind


class SmartNormalizer:
    """
    자동 타입 추론 기반 Normalizer.
    
    type_utils의 TypeInferencer를 사용하여 값의 타입을 자동 추론하고,
    Rule 없이 Dict를 NormalizedItem 리스트로 변환.
    
    주요 기능:
    - 값 타입 자동 추론 (image/video/audio/document/text/file)
    - 키 이름 기반 타입 힌트 (예: "images" → image)
    - 리스트 값 자동 explode
    - 파일명 자동 생성 (section + key + index)
    - 확장자 자동 추론
    
    Examples:
        >>> normalizer = SmartNormalizer()
        >>> data = {
        ...     "images": ["https://img.com/1.jpg", "https://img.com/2.png"],
        ...     "title": "Product Name",
        ...     "price": "10,000원"
        ... }
        >>> items = normalizer.normalize(data, section="product_123")
        >>> len(items)
        4
        >>> items[0].kind
        'image'
        >>> items[2].kind
        'text'
    """
    
    def __init__(
        self,
        *,
        policy: Optional[InferencePolicy] = None,
        section_prefix: Optional[str] = None,
        name_delimiter: str = "_"
    ):
        """
        Args:
            policy: type_utils InferencePolicy. None이면 기본 정책 사용.
            section_prefix: 섹션명 접두사 (예: "product_")
            name_delimiter: 파일명 구분자
        """
        self.inferencer = TypeInferencer(policy) if policy else TypeInferencer()
        self.section_prefix = section_prefix
        self.name_delimiter = name_delimiter
    
    def normalize(
        self,
        extracted: Dict[str, Any],
        *,
        section: str = "default",
        name_prefix: Optional[str] = None,
        record_index: int = 1
    ) -> List[NormalizedItem]:
        """
        Dict를 NormalizedItem 리스트로 자동 변환.
        
        Args:
            extracted: JS Extractor 등에서 추출한 Dict
            section: 섹션 이름 (파일 그룹화)
            name_prefix: 파일명 접두사
            record_index: 레코드 인덱스 (여러 상품 처리 시)
        
        Returns:
            NormalizedItem 리스트
        
        Examples:
            >>> normalizer = SmartNormalizer()
            >>> data = {
            ...     "images": ["https://img.com/1.jpg", "https://img.com/2.jpg"],
            ...     "title": "상품명",
            ... }
            >>> items = normalizer.normalize(data, section="product_001")
            >>> len(items)
            3
            >>> [item.kind for item in items]
            ['image', 'image', 'text']
        """
        items: List[NormalizedItem] = []
        
        # 섹션 정규화
        if self.section_prefix:
            section = f"{self.section_prefix}{section}"
        
        for key, value in extracted.items():
            # None/빈 값 제외
            if value is None:
                continue
            
            # 리스트/튜플 처리 (explode)
            if isinstance(value, (list, tuple)):
                for idx, item in enumerate(value, 1):
                    if item is None:
                        continue
                    
                    normalized = self._normalize_single(
                        key=key,
                        value=item,
                        section=section,
                        name_prefix=name_prefix,
                        record_index=record_index,
                        item_index=idx
                    )
                    if normalized:
                        items.append(normalized)
            else:
                # 단일 값
                normalized = self._normalize_single(
                    key=key,
                    value=value,
                    section=section,
                    name_prefix=name_prefix,
                    record_index=record_index,
                    item_index=1
                )
                if normalized:
                    items.append(normalized)
        
        return items
    
    def normalize_many(
        self,
        records: List[Dict[str, Any]],
        *,
        section_template: str = "record_{index}",
        name_prefix: Optional[str] = None
    ) -> List[NormalizedItem]:
        """
        여러 Dict를 일괄 변환 (검색 결과 등).
        
        Args:
            records: Dict 리스트
            section_template: 섹션명 템플릿 (예: "product_{index}")
            name_prefix: 파일명 접두사
        
        Returns:
            NormalizedItem 리스트
        
        Examples:
            >>> normalizer = SmartNormalizer()
            >>> records = [
            ...     {"title": "상품1", "image": "https://img.com/1.jpg"},
            ...     {"title": "상품2", "image": "https://img.com/2.jpg"},
            ... ]
            >>> items = normalizer.normalize_many(records, section_template="product_{index}")
            >>> len(items)
            4
        """
        all_items: List[NormalizedItem] = []
        
        for idx, record in enumerate(records, 1):
            section = section_template.format(index=idx)
            items = self.normalize(
                record,
                section=section,
                name_prefix=name_prefix,
                record_index=idx
            )
            all_items.extend(items)
        
        return all_items
    
    # ----------------------------------------------------------------
    # Private Methods
    # ----------------------------------------------------------------
    
    def _normalize_single(
        self,
        key: str,
        value: Any,
        section: str,
        name_prefix: Optional[str],
        record_index: int,
        item_index: int
    ) -> Optional[NormalizedItem]:
        """단일 값을 NormalizedItem으로 변환"""
        
        # 빈 문자열 제외
        if isinstance(value, str) and not value.strip():
            return None
        
        # 1. 키 이름에서 타입 힌트 추출
        hint = self._hint_from_key(key)
        
        # 2. 타입 자동 추론
        file_type: FileType = self.inferencer.infer(value, hint=hint)
        
        # 3. FileType (7종) → ItemKind (3종) 변환
        kind: ItemKind = self._to_item_kind(file_type)
        
        # 4. 확장자 추론
        extension = self.inferencer.infer_extension(value, kind=file_type)
        
        # 5. 파일명 생성
        name_hint = self._build_name(
            key=key,
            prefix=name_prefix,
            item_index=item_index if item_index > 1 else None
        )
        
        # 6. NormalizedItem 생성
        return NormalizedItem(
            kind=kind,
            value=value,
            section=section,
            name_hint=name_hint,
            extension=extension,
            metadata={
                "source_key": key,
                "inferred_type": file_type,
                "auto_normalized": True
            },
            record_index=record_index,
            item_index=item_index
        )
    
    def _hint_from_key(self, key: str) -> Optional[str]:
        """
        키 이름에서 타입 힌트 추출.
        
        Examples:
            "images" → "image"
            "photos" → "image"
            "title" → "text"
            "video_url" → "video"
        """
        key_lower = key.lower()
        
        # 이미지 키워드
        if any(word in key_lower for word in ["image", "img", "photo", "pic", "icon", "thumbnail", "thumb"]):
            return "image"
        
        # 비디오 키워드
        if any(word in key_lower for word in ["video", "movie", "clip"]):
            return "video"
        
        # 오디오 키워드
        if any(word in key_lower for word in ["audio", "sound", "music", "mp3"]):
            return "audio"
        
        # 문서 키워드
        if any(word in key_lower for word in ["document", "doc", "pdf", "file", "attachment"]):
            return "document"
        
        # 압축 파일 키워드
        if any(word in key_lower for word in ["archive", "zip", "download"]):
            return "archive"
        
        # 텍스트 키워드
        if any(word in key_lower for word in [
            "text", "title", "name", "desc", "description", 
            "content", "price", "label", "tag", "category"
        ]):
            return "text"
        
        # 알 수 없음
        return None
    
    def _to_item_kind(self, file_type: FileType) -> ItemKind:
        """
        FileType (7종) → ItemKind (3종) 매핑.
        
        매핑 규칙:
        - image → image
        - text → text
        - video/audio/document/archive/file/unknown → file
        """
        if file_type == "image":
            return "image"
        elif file_type == "text":
            return "text"
        else:
            # video, audio, document, archive, file, unknown → file
            return "file"
    
    def _build_name(
        self,
        key: str,
        prefix: Optional[str],
        item_index: Optional[int]
    ) -> str:
        """
        파일명 생성.
        
        패턴: [prefix_]key[_index]
        
        Examples:
            key="images", prefix="nike", index=1 → "nike_images_001"
            key="title", prefix=None, index=None → "title"
        """
        parts = []
        
        # 접두사
        if prefix:
            parts.append(prefix)
        
        # 키 이름
        parts.append(key)
        
        # 인덱스 (2개 이상일 때만)
        if item_index is not None:
            parts.append(f"{item_index:03d}")
        
        return self.name_delimiter.join(parts)


__all__ = [
    "SmartNormalizer",
]
