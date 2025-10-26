# -*- coding: utf-8 -*-
# crawl_utils/services/Item_Post_Processor.py
# ItemPostProcessor v7.0 - KeyPath 기반 규칙 처리 + Override 지원

"""
ItemPostProcessor v7.0
======================

KeyPath 기반 규칙 처리 및 ItemList 생성.

주요 개선 (v7.0):
1. KeyPath 기반 값 추출 (policy.source)
2. 배열 인덱스 지원 ([0], [1], [*])
3. 중간 경로 와일드카드 지원 (sku__options[*]__name)
4. Jinja2 제거 → KeyPath Override로 대체
5. **overrides로 런타임 값 주입

데이터 흐름:
    Extractor → List[Dict[str, Any]]
        ↓ ItemPostProcessor.process()
    List[ItemList] (규칙별 처리)
        ↓ PostProcessor.save_items()
    ItemSaveSummary (저장 결과)

Override 우선순위:
    1. 정책 기본값 (modules/**/configs/*.yaml)
    2. YAML 데이터 (configs/**/*.yaml)
    3. Python Preset (presets/sites/*.py)
    4. Runtime Override (**overrides → KeyPath)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence
from pathlib import Path

from keypath_utils import KeyPathAccessor
from type_utils.services.inferencer import TypeInferencer
from type_utils.services.extension import ExtensionDetector

from ..core.policy import ItemPostProcessPolicy, ItemList, ItemKind
from modules.path_utils.os_paths import OSPath


class ItemPostProcessor:
    """ItemPostProcessor v7.0 - KeyPath 기반 규칙 처리 + Override
    
    규칙 기반 처리:
    - CrawlPolicy.save: List[ItemPostProcessPolicy] 규칙 적용
    - KeyPath로 값 추출 (product__images, sku__options[*]__name 등)
    - Python Preset으로 정적 설정
    - KeyPath Override로 런타임 동적 값 주입
    
    Examples:
        >>> # 규칙 정의 (Python Preset 또는 YAML)
        >>> rules = [
        ...     ItemPostProcessPolicy(
        ...         kind="image",
        ...         source="product__images",
        ...         directory=Path("output/images")
        ...     )
        ... ]
        >>> 
        >>> # 처리 실행
        >>> processor = ItemPostProcessor(rules=rules)
        >>> items = processor.process(
        ...     extracted_data=[{"product": {"images": ["url1", "url2"]}}]
        ... )
        >>> 
        >>> # Override 적용 (SyncCrawl에서)
        >>> # sync_crawl__save__0__directory="output/CAPEA-001/images"
    """
    
    def __init__(self, rules: List[ItemPostProcessPolicy]):
        """
        Args:
            rules: ItemPostProcessPolicy 규칙 리스트 (CrawlPolicy.save)
        """
        self.rules = rules
        self.inferencer = TypeInferencer()
        self.detector = ExtensionDetector()
    
    def process(
        self,
        extracted_data: Sequence[Dict[str, Any]]
    ) -> List[ItemList]:
        """추출 데이터를 규칙에 따라 ItemList로 변환
        
        Args:
            extracted_data: Extractor에서 추출한 데이터 리스트
        
        Returns:
            ItemList 리스트 (규칙별 × 레코드별)
        
        Examples:
            >>> extracted = [
            ...     {"product": {"title": "상품1", "images": ["url1", "url2"]}},
            ...     {"product": {"title": "상품2", "images": ["url3"]}}
            ... ]
            >>> items = processor.process(extracted_data=extracted)
            >>> len(items)  # 2 records × 1 rule × images = 3
            3
        """
        items: List[ItemList] = []
        
        for record_index, record in enumerate(extracted_data, start=1):
            # 각 규칙 적용
            for rule in self.rules:
                items_from_rule = self._process_rule(
                    rule=rule,
                    record=record,
                    record_index=record_index
                )
                items.extend(items_from_rule)
        
        return items
    
    def _process_rule(
        self,
        rule: ItemPostProcessPolicy,
        record: Dict[str, Any],
        record_index: int
    ) -> List[ItemList]:
        """단일 규칙 처리
        
        배열 KeyPath 지원:
        - "product__images" → 배열이면 자동 explode
        - "sku__options[*]__name" → 중간 경로 [*] 자동 순회
        - "items[0]__title" → 특정 인덱스 접근
        
        Args:
            rule: ItemPostProcessPolicy 규칙
            record: 추출된 레코드
            record_index: 레코드 인덱스 (1-based)
            runtime_context: 런타임 컨텍스트
            env_context: 환경 컨텍스트
        
        Returns:
            ItemList 리스트 (단일 값 또는 explode된 리스트)
        """
        # ✅ source에 [*] 패턴이 있는지 확인
        if "[*]" in rule.source:
            return self._process_wildcard_path(
                rule=rule,
                record=record,
                record_index=record_index
            )
        
        # 일반 KeyPath 처리
        accessor = KeyPathAccessor(record)
        value = accessor.get(rule.source)
        
        if value is None:
            # ✅ 배열 내 객체의 필드 접근 시도 (skuOptions__url → [obj.url for obj in skuOptions])
            # source를 parts로 분리
            parts = rule.source.split("__")
            if len(parts) >= 2:
                # 마지막 부분을 제외한 경로로 배열 추출 시도
                array_path = "__".join(parts[:-1])
                field_name = parts[-1]
                
                array_value = accessor.get(array_path)
                if isinstance(array_value, list) and array_value:
                    # 배열 내 각 객체에서 필드 추출
                    extracted_values = []
                    for item in array_value:
                        if isinstance(item, dict) and field_name in item:
                            extracted_values.append(item[field_name])
                    
                    if extracted_values:
                        return self._explode_list(
                            rule=rule,
                            values=extracted_values,
                            record=record,
                            record_index=record_index
                        )
            
            return []
        
        # ✅ 값이 리스트면 explode (각 item을 개별 ItemList로)
        if isinstance(value, list):
            return self._explode_list(
                rule=rule,
                values=value,
                record=record,
                record_index=record_index
            )
        else:
            # 단일 값
            return [self._create_item(
                rule=rule,
                value=value,
                record=record,
                record_index=record_index,
                item_index=1
            )]
    
    def _process_wildcard_path(
        self,
        rule: ItemPostProcessPolicy,
        record: Dict[str, Any],
        record_index: int
    ) -> List[ItemList]:
        """중간 경로 [*] 패턴 처리
        
        Examples:
            >>> # sku__options[*]__name
            >>> # → options 배열의 각 요소에서 name 추출
            >>> # → ["Color", "Size", "Material"]
            
            >>> # product__variants[*]__images[*]
            >>> # → variants 배열 각 요소의 images 배열 전체 추출
        
        Args:
            rule: ItemPostProcessPolicy 규칙
            record: 추출된 레코드
            record_index: 레코드 인덱스
            runtime_context: 런타임 컨텍스트
            env_context: 환경 컨텍스트
        
        Returns:
            ItemList 리스트
        """
        from keypath_utils.services.normalizer import KeyPathNormalizer
        from keypath_utils.core.policy import KeyPathNormalizePolicy
        
        # KeyPath 정규화 (enable_list_index=True)
        policy = KeyPathNormalizePolicy(
            sep="__",
            enable_list_index=True,
            recursive=False,
            strict=False
        )
        normalizer = KeyPathNormalizer(policy)
        segments = normalizer.apply(rule.source)
        
        # [*] 위치 찾기
        wildcard_indices = [i for i, seg in enumerate(segments) if seg == "[*]"]
        
        if not wildcard_indices:
            # [*]가 없으면 일반 처리로 fallback
            accessor = KeyPathAccessor(record)
            value = accessor.get(rule.source)
            if value is None:
                return []
            if isinstance(value, list):
                return self._explode_list(
                    rule, value, record, record_index
                )
            return [self._create_item(
                rule, value, record, record_index, 1
            )]
        
        # ✅ 재귀적으로 배열 순회
        results = self._traverse_wildcard(
            segments=segments,
            wildcard_indices=wildcard_indices,
            current_data=record,
            current_segment=0
        )
        
        # ItemList로 변환
        items = []
        for item_index, value in enumerate(results, start=1):
            item = self._create_item(
                rule=rule,
                value=value,
                record=record,
                record_index=record_index,
                item_index=item_index
            )
            items.append(item)
        
        return items
    
    def _traverse_wildcard(
        self,
        segments: List[str],
        wildcard_indices: List[int],
        current_data: Any,
        current_segment: int
    ) -> List[Any]:
        """재귀적으로 [*] 패턴 순회
        
        Args:
            segments: 정규화된 경로 세그먼트
            wildcard_indices: [*] 위치 인덱스 리스트
            current_data: 현재 데이터
            current_segment: 현재 세그먼트 인덱스
        
        Returns:
            추출된 값 리스트
        """
        # 모든 세그먼트를 처리했으면 현재 데이터 반환
        if current_segment >= len(segments):
            return [current_data]
        
        seg = segments[current_segment]
        
        # [*] 패턴
        if seg == "[*]":
            if not isinstance(current_data, list):
                return []
            
            results = []
            # 배열의 각 요소에 대해 다음 세그먼트 처리
            for item in current_data:
                sub_results = self._traverse_wildcard(
                    segments, wildcard_indices, item, current_segment + 1
                )
                results.extend(sub_results)
            return results
        
        # [숫자] 패턴
        elif seg.startswith("[") and seg.endswith("]"):
            if not isinstance(current_data, list):
                return []
            try:
                index = int(seg[1:-1])
                if 0 <= index < len(current_data):
                    return self._traverse_wildcard(
                        segments, wildcard_indices,
                        current_data[index], current_segment + 1
                    )
            except ValueError:
                pass
            return []
        
        # 일반 dict 키
        else:
            if isinstance(current_data, dict) and seg in current_data:
                return self._traverse_wildcard(
                    segments, wildcard_indices,
                    current_data[seg], current_segment + 1
                )
            return []
    
    def _explode_list(
        self,
        rule: ItemPostProcessPolicy,
        values: List[Any],
        record: Dict[str, Any],
        record_index: int
    ) -> List[ItemList]:
        """리스트 값을 개별 ItemList로 분리
        
        Args:
            rule: ItemPostProcessPolicy 규칙
            values: 값 리스트
            record: 추출된 레코드
            record_index: 레코드 인덱스
        
        Returns:
            ItemList 리스트 (item_index는 1-based 자동 증가)
        """
        items = []
        for item_index, value in enumerate(values, start=1):
            item = self._create_item(
                rule=rule,
                value=value,
                record=record,
                record_index=record_index,
                item_index=item_index
            )
            items.append(item)
        return items
    
    def _create_item(
        self,
        rule: ItemPostProcessPolicy,
        value: Any,
        record: Dict[str, Any],
        record_index: int,
        item_index: int
    ) -> ItemList:
        """ItemList 생성 (Policy 직접 사용)
        
        Args:
            rule: ItemPostProcessPolicy 규칙
            value: 추출된 값
            record: 추출된 레코드
            record_index: 레코드 인덱스
            item_index: 아이템 인덱스
        
        Returns:
            ItemList
        """
        # directory 환경 변수 해석
        import os
        directory = rule.directory or Path(OSPath.downloads())
        
        # 문자열이면 환경 변수 해석
        if isinstance(directory, str):
            # {{modules_dir}} 같은 변수를 해석
            directory_str = directory
            if '{{' in directory_str:
                # {{modules_dir}} → M:\CALife\CAShop - 구매대행\_code\modules
                import re
                for match in re.finditer(r'\{\{(.+?)\}\}', directory_str):
                    var_name = match.group(1)
                    var_value = os.environ.get(var_name, '')
                    if not var_value and var_name == 'modules_dir':
                        # Fallback: 현재 모듈 경로에서 추론
                        var_value = str(Path(__file__).resolve().parent.parent.parent)
                    directory_str = directory_str.replace(match.group(0), var_value)
            
            # 슬래시를 백슬래시로 변환 (Windows)
            directory_str = directory_str.replace('/', '\\')
            directory = Path(directory_str)
        
        # ItemList 생성 (Policy 값 직접 사용)
        item = ItemList(
            kind=rule.kind,
            value=value,
            directory=directory,
            name=rule.name,
            ops=rule.ops,
            record_index=record_index,
            item_index=item_index
        )
        
        return item


__all__ = ["ItemPostProcessor"]

