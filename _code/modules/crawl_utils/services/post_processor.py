# -*- coding: utf-8 -*-
"""crawl_utils/services/post_processor.py

PostProcessor Service - Extract 결과 후처리 통합

책임:
1. JS 추출 결과에서 KeyPath 기반 데이터 추출
2. 템플릿 렌더링 (dynamic_subdir, fso_name_policy)
3. SmartNormalizer 또는 DataNormalizer로 정규화
4. SyncFileSaver로 파일 저장

사용 예시:
```python
from crawl_utils.services.post_processor import SyncPostProcessor
from crawl_utils.core.policy import PostProcessorPolicy

policy = PostProcessorPolicy(
    target_dir=Path("output/crawl"),
    use_smart_normalizer=True,
    rules=[
        PostProcessorRule(
            kind="image",
            source="product.images",
            dynamic_subdir="{{cas_no}}/images",
            fso_name_policy={"prefix": "{{item.title}}", "extension": "jpg"}
        )
    ]
)

processor = SyncPostProcessor(policy)

extracted_data = {
    "product": {
        "title": "Sample Product",
        "images": ["https://example.com/img1.jpg", "https://example.com/img2.jpg"]
    }
}

runtime_context = {"cas_no": "CAS12345"}
save_summary = processor.process(extracted_data, runtime_context)

print(f"Saved: {len(save_summary.flatten())} files")
```
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from pathlib import Path

from ..core.models import NormalizedItem, SaveSummary
from .smart_normalizer import SmartNormalizer
from .normalizer import DataNormalizer
from .saver import SyncFileSaver

if TYPE_CHECKING:
    from ..core.policy import PostProcessorPolicy, PostProcessorRule, StoragePolicy


class SyncPostProcessor:
    """PostProcessor Service - Extract 결과 후처리 통합
    
    Extract 단계에서 추출한 Dict를 NormalizedItem으로 변환하고 파일로 저장합니다.
    
    주요 기능:
    - KeyPath 기반 데이터 추출 (source 필드, dot notation)
    - 템플릿 렌더링 ({{item.field}}, {{runtime_var}})
    - SmartNormalizer (자동 타입 추론) 또는 DataNormalizer (Rule 기반)
    - SyncFileSaver로 파일 저장 (FSOPathBuilder 활용)
    
    Attributes:
        policy: PostProcessorPolicy
        normalizer: SmartNormalizer 또는 DataNormalizer
        saver: SyncFileSaver
    """
    
    def __init__(self, policy: 'PostProcessorPolicy'):
        """Initialize PostProcessor with policy.
        
        Args:
            policy: PostProcessorPolicy (규칙, 저장 경로 등)
        """
        self.policy = policy
        
        # Normalizer 선택
        if policy.use_smart_normalizer:
            self.normalizer = SmartNormalizer()
        else:
            # DataNormalizer는 NormalizationPolicy 필요
            # 현재는 SmartNormalizer 우선 사용
            self.normalizer = SmartNormalizer()
        
        # FileSaver 초기화
        # TODO: StoragePolicy를 PostProcessorPolicy에서 생성
        # 현재는 간단히 target_dir만 사용
        from ..core.policy import StoragePolicy, StorageTargetPolicy
        
        # 기본 StoragePolicy 생성
        storage_policy = StoragePolicy(
            image=StorageTargetPolicy(
                base_dir=policy.target_dir,
                sub_dir="images",
                name_template="{section}_{index}",
                extension="jpg",
                ensure_unique=True
            ),
            text=StorageTargetPolicy(
                base_dir=policy.target_dir,
                sub_dir="texts",
                name_template="{section}_{index}",
                extension="txt",
                ensure_unique=True
            ),
            file=StorageTargetPolicy(
                base_dir=policy.target_dir,
                sub_dir="files",
                name_template="{section}_{index}",
                extension="bin",
                ensure_unique=True
            )
        )
        
        self.saver = SyncFileSaver(storage_policy)
    
    def process(
        self,
        extracted_data: Dict[str, Any],
        runtime_context: Optional[Dict[str, Any]] = None
    ) -> SaveSummary:
        """Extract → Normalize → Save Pipeline
        
        Args:
            extracted_data: JS Extractor 결과 (Dict)
            runtime_context: 런타임 컨텍스트 (cas_no, batch_id 등)
        
        Returns:
            SaveSummary (저장 결과)
        
        Example:
            >>> extracted_data = {"images": ["url1.jpg", "url2.jpg"], "title": "Product"}
            >>> runtime_context = {"cas_no": "CAS123"}
            >>> summary = processor.process(extracted_data, runtime_context)
            >>> print(f"Saved: {len(summary.flatten())} files")
        """
        runtime_context = runtime_context or {}
        all_items: List[NormalizedItem] = []
        
        for rule in self.policy.rules:
            # 1. KeyPath로 데이터 추출
            value = self._extract_by_keypath(extracted_data, rule.source)
            if value is None and not rule.allow_empty:
                continue
            
            # 2. 템플릿 렌더링 (dynamic_subdir, fso_name_policy)
            rendered_rule = self._render_templates(rule, extracted_data, runtime_context)
            
            # 3. NormalizedItem 생성
            normalized = self._create_normalized_items(
                value=value,
                rule=rendered_rule,
                runtime_context=runtime_context
            )
            all_items.extend(normalized)
        
        # 4. 파일 저장
        if not all_items:
            # 저장할 아이템이 없으면 빈 SaveSummary 반환
            return SaveSummary(artifacts={})
        
        return self.saver.save_many(all_items)
    
    def _extract_by_keypath(self, data: Dict, keypath: str) -> Any:
        """KeyPath로 nested dict 추출 (dot notation)
        
        Args:
            data: 추출 대상 딕셔너리
            keypath: 키 경로 (예: "product.images", "details.price")
        
        Returns:
            추출된 값 (없으면 None)
        
        Example:
            >>> data = {"product": {"images": ["url1", "url2"]}}
            >>> self._extract_by_keypath(data, "product.images")
            ["url1", "url2"]
        """
        # keypath_utils가 있으면 사용, 없으면 간단한 구현
        try:
            from keypath_utils import get_keypath
            return get_keypath(data, keypath, default=None)
        except ImportError:
            # Fallback: 간단한 dot notation 파싱
            keys = keypath.split(".")
            current = data
            
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return None
            
            return current
    
    def _render_templates(
        self,
        rule: 'PostProcessorRule',
        extracted_data: Dict,
        runtime_context: Dict
    ) -> 'PostProcessorRule':
        """템플릿 렌더링 ({{item.title}}, {{cas_no}} 등)
        
        Template 변수:
        - {{item.*}}: extracted_data 필드 (예: {{item.title}})
        - {{*}}: runtime_context 필드 (예: {{cas_no}})
        
        Args:
            rule: PostProcessorRule (원본)
            extracted_data: JS 추출 결과
            runtime_context: 런타임 컨텍스트
        
        Returns:
            렌더링된 PostProcessorRule (복사본)
        """
        # Rule 복사 (원본 변경 방지)
        import copy
        rendered_rule = copy.deepcopy(rule)
        
        # 템플릿 컨텍스트 구성
        context = {
            "item": extracted_data,
            **runtime_context
        }
        
        # dynamic_subdir 렌더링
        if rendered_rule.dynamic_subdir:
            rendered_rule.dynamic_subdir = self._render_string(
                rendered_rule.dynamic_subdir,
                context
            )
        
        # fso_name_policy 내부 템플릿 렌더링
        if rendered_rule.fso_name_policy:
            rendered_policy = {}
            for key, value in rendered_rule.fso_name_policy.items():
                if isinstance(value, str):
                    rendered_policy[key] = self._render_string(value, context)
                else:
                    rendered_policy[key] = value
            
            rendered_rule.fso_name_policy = rendered_policy
        
        return rendered_rule
    
    def _render_string(self, template: str, context: Dict) -> str:
        """문자열 템플릿 렌더링
        
        지원 형식:
        - {{variable}}: context["variable"]
        - {{item.field}}: context["item"]["field"]
        
        Args:
            template: 템플릿 문자열
            context: 템플릿 변수 딕셔너리
        
        Returns:
            렌더링된 문자열
        """
        # {{...}} 패턴 찾기
        pattern = r'\{\{([^}]+)\}\}'
        
        def replace_var(match):
            var_path = match.group(1).strip()
            
            # dot notation 지원 (예: item.title → context["item"]["title"])
            keys = var_path.split(".")
            value = context
            
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    # 변수 없음
                    if self.policy.template_safe_mode:
                        return ""  # 빈 문자열 반환
                    else:
                        raise KeyError(f"Template variable not found: {var_path}")
            
            return str(value)
        
        try:
            return re.sub(pattern, replace_var, template)
        except KeyError as e:
            if self.policy.template_safe_mode:
                return template  # 원본 반환
            raise ValueError(f"Template rendering failed: {e}")
    
    def _create_normalized_items(
        self,
        value: Any,
        rule: 'PostProcessorRule',
        runtime_context: Dict
    ) -> List[NormalizedItem]:
        """NormalizedItem 생성
        
        Args:
            value: 추출된 값 (단일 값 또는 리스트)
            rule: PostProcessorRule (렌더링 완료)
            runtime_context: 런타임 컨텍스트
        
        Returns:
            NormalizedItem 리스트
        """
        items: List[NormalizedItem] = []
        
        # 값이 리스트면 각 항목을 개별 NormalizedItem으로
        if isinstance(value, list):
            values = value
        else:
            values = [value]
        
        for idx, val in enumerate(values, start=1):
            if val is None and not rule.allow_empty:
                continue
            
            # NormalizedItem 생성
            item = NormalizedItem(
                kind=rule.kind,  # type: ignore  # PostProcessorRule.kind는 str이지만 ItemKind와 호환
                value=val,
                section=rule.dynamic_subdir or rule.static_section or "default",
                name_hint=None,  # FSOPathBuilder가 fso_name_policy로 생성
                extension=rule.fso_name_policy.get("extension") if rule.fso_name_policy else None,
                metadata={
                    "rule_source": rule.source,
                    **runtime_context
                },
                record_index=1,
                item_index=idx
            )
            
            items.append(item)
        
        return items


__all__ = ["SyncPostProcessor"]
