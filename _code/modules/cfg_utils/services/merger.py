"""
modules.cfg_utils.services.merger
================================

Define Merger interface and implementations for different config input types.

SRP 준수: 각 Merger는 특정 타입의 병합만 담당
- BaseMerger: 추상 병합 인터페이스
- DictMerger: 딕셔너리 병합 (단순 병합만 담당, 정규화는 normalizer에서)
- ModelMerger: BaseModel 병합 (helpers.model_to_dict 사용)
- PathMerger: 파일/경로 병합 (helpers.load_source 사용)
- SequenceMerger: 시퀀스 순회 및 각 항목 병합 위임
- MergerFactory: 타입 기반 Merger 선택

중복 제거:
- PathMerger: helpers.load_source 재사용 (파일 읽기/파싱 중복 제거)
- ModelMerger: helpers.model_to_dict 재사용
- DictMerger: None 제거 로직 제거 (normalizer에서 처리)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Sequence

from pydantic import BaseModel

from modules.keypath_utils import KeyPathDict

# Avoid circular import at runtime; use forward reference for type hints
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from modules.cfg_utils.services.config_loader import ConfigLoader


class BaseMerger(ABC):
    """Abstract base for config mergers."""
    def __init__(self, loader: ConfigLoader) -> None:
        self.loader = loader

    @abstractmethod
    def merge(self, source: Any, data: KeyPathDict, deep: bool) -> None:
        """Merge the given source into the provided KeyPathDict."""
        ...


class DictMerger(BaseMerger):
    """Merge plain dicts into the config data.
    
    SRP 준수: 딕셔너리 병합만 담당, None 제거는 선택적
    """
    def merge(self, source: dict[str, Any], data: KeyPathDict, deep: bool) -> None:
        # 단순히 병합만 수행 (None 제거는 normalizer에서 처리)
        data.merge(source, deep=deep)


class ModelMerger(BaseMerger):
    """Merge Pydantic BaseModel into config data.
    
    SRP 준수: BaseModel을 dict로 변환 후 병합
    """
    def merge(self, source: BaseModel, data: KeyPathDict, deep: bool) -> None:
        from modules.cfg_utils.services.helpers import model_to_dict
        
        # helpers.model_to_dict 사용 (None 제거 옵션)
        converted = model_to_dict(source, drop_none=True)
        data.merge(converted, deep=deep)


class PathMerger(BaseMerger):
    """Merge content from YAML path or raw string via YamlParser.
    
    SRP 준수: 파일 읽기/파싱 로직은 helpers.load_source로 위임
    """
    def merge(self, source: str | Path, data: KeyPathDict, deep: bool) -> None:
        from modules.cfg_utils.services.helpers import load_source
        
        # helpers.load_source 사용 (중복 제거)
        parsed = load_source(source, self.loader.parser)
        if parsed:  # 빈 dict가 아니면 병합
            data.merge(parsed, deep=deep)


class SequenceMerger(BaseMerger):
    """Merge each item in a sequence of sources.
    
    SRP 준수: 시퀀스 순회 및 각 항목 병합 위임
    """
    def merge(self, source: Sequence[Any], data: KeyPathDict, deep: bool) -> None:
        # 각 항목마다 적절한 Merger 선택 후 병합
        for item in source:
            merger = MergerFactory.get(item, self.loader)
            merger.merge(item, data, deep)


class MergerFactory:
    """Select appropriate Merger based on source type."""
    @staticmethod
    def get(source: Any, loader: ConfigLoader) -> BaseMerger:
        if isinstance(source, dict):
            return DictMerger(loader)
        if isinstance(source, BaseModel):
            return ModelMerger(loader)
        if isinstance(source, (str, Path)):
            return PathMerger(loader)
        # Sequence but not string/bytes
        if isinstance(source, Sequence) and not isinstance(source, (str, bytes)):
            return SequenceMerger(loader)
        raise TypeError(f"Unsupported config input for merging: {type(source)}")
