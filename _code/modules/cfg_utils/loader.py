# -*- coding: utf-8 -*-
# cfg_utils/loader.py
# ConfigLoader — 정책 기반 설정 병합 및 모델 변환기

from __future__ import annotations
from pathlib import Path
from typing import Any, Sequence, Type, TypeVar, Union, Optional
from pydantic import BaseModel, ValidationError

from modules.structured_io.formats.yaml_io import YamlParser
from keypath_utils import KeyPathDict
from .normalizer import ConfigNormalizer
from .policy import ConfigPolicy

T = TypeVar("T", bound=BaseModel)


class ConfigLoader:
    """
    통합 설정 로더
    -----------------
    - BaseModel / YAML / dict / runtime overrides 병합
    - KeyPathDict 기반 구조적 병합
    - ConfigPolicy에 따른 deep/shallow 병합 방식 적용
    """

    def __init__(
        self,
        cfg_like: Union[str, Path, dict, BaseModel, Sequence[str | Path]],
        *,
        policy: Optional[ConfigPolicy] = None,
    ):
        self.policy = policy or ConfigPolicy()
        self.parser = YamlParser(policy=self.policy.yaml_policy)
        self.normalizer = ConfigNormalizer(self.policy)
        self.cfg_like = cfg_like

        # 내부 데이터 컨테이너
        self._data = KeyPathDict()
        self._load_and_merge()

    # ------------------------------------------------------------------
    # Core Loading Logic
    # ------------------------------------------------------------------
    def _load_and_merge(self) -> None:
        """입력 유형에 따라 로딩 및 병합"""
        deep = self.policy.merge_mode == "deep"

        # ① BaseModel 기본값 병합
        if isinstance(self.cfg_like, BaseModel):
            self._data.merge(self.cfg_like.model_dump(), deep=deep)

        # ② YAML 파일 or 리스트
        elif isinstance(self.cfg_like, (str, Path)):
            path = Path(self.cfg_like)
            text = path.read_text(encoding=self.parser.policy.encoding)
            yaml_data = self.parser.parse(text, base_path=path)
            self._data.merge(yaml_data, deep=deep)

        elif isinstance(self.cfg_like, Sequence):
            for p in self.cfg_like:
                path = Path(p)
                text = path.read_text(encoding=self.parser.policy.encoding)
                yaml_data = self.parser.parse(text, base_path=path)
                self._data.merge(yaml_data, deep=deep)

        # ③ dict 직접 입력
        elif isinstance(self.cfg_like, dict):
            self._data.merge(self.cfg_like, deep=deep)

        else:
            raise TypeError(f"Unsupported config input: {type(self.cfg_like)}")

        # ④ 후처리 (reference/drop 등)
        normalized = self.normalizer.apply(self._data.data)
        self._data = KeyPathDict(normalized)

    # ------------------------------------------------------------------
    # Overrides
    # ------------------------------------------------------------------
    def merge_overrides(self, overrides: dict[str, Any]) -> None:
        """런타임 override를 병합 (정책 기반 deep/shallow 반영)"""
        deep = self.policy.merge_mode == "deep"
        self._data.merge(overrides, deep=deep)

    def override_path(self, path: str, value: Any) -> None:
        """단일 경로 기반 강제 override"""
        self._data.override(path, value)

    # ------------------------------------------------------------------
    # Output Transform
    # ------------------------------------------------------------------
    def as_dict(self, section: Optional[str] = None, **overrides: Any) -> dict[str, Any]:
        """최종 병합 dict 반환
        
        Section 우선순위:
        1. 명시적 section 파라미터 (section이 있으면 추출)
        2. root (section이 없으면 root 전체 반환)
        
        Args:
            section: Optional section name to extract
            **overrides: Runtime overrides
            
        Returns:
            Configuration dictionary
        """
        data = self._data.data.copy()
        
        # Extract section if specified (section or root)
        if section:
            if section not in data:
                # Section not found, check if it's trying to use root
                # For backwards compatibility, if section is not found, 
                # we could return root, but explicit is better
                raise KeyError(f"[ConfigLoader] Section '{section}' not found in config")
            data = data[section]
        # else: use root data as-is
        
        # Apply overrides
        if overrides:
            deep = self.policy.merge_mode == "deep"
            temp = KeyPathDict(data)
            temp.merge(overrides, deep=deep)
            return temp.data
        return data
    
    def get_section(self, section: str) -> dict[str, Any]:
        """섹션 추출 (별칭 메서드)
        
        Args:
            section: Section name to extract
            
        Returns:
            Section data as dictionary
        """
        return self.as_dict(section=section)
    
    def has_section(self, section: str) -> bool:
        """섹션 존재 여부 확인
        
        Args:
            section: Section name to check
            
        Returns:
            True if section exists, False otherwise
        """
        return section in self._data.data and isinstance(self._data.data[section], dict)
    
    def get_root(self) -> dict[str, Any]:
        """Root 데이터 전체 반환 (별칭 메서드)
        
        Returns:
            Root configuration dictionary
        """
        return self.as_dict(section=None)

    def as_model(self, model: Type[T], section: Optional[str] = None, **overrides: Any) -> T:
        """최종 모델 변환
        
        Section 우선순위:
        1. 명시적 section 파라미터
        2. 자동 감지된 section (모델명 기반)
        3. root (section이 없으면 root에서 바로 로드)
        
        Args:
            model: Pydantic model class
            section: Optional section name to extract from config
                    If not provided, auto-detects from model name or uses root
            **overrides: Runtime overrides
            
        Returns:
            Validated model instance
        """
        data = self.as_dict(**overrides)
        
        # Section selection logic
        if section:
            # 1. Explicit section provided
            if section not in data:
                raise KeyError(f"[ConfigLoader] Section '{section}' not found in config")
            data = data[section]
        else:
            # 2. Auto-detect section from model name
            model_name = model.__name__.lower()
            candidates = []
            
            # Handle common naming patterns
            if model_name.endswith("policy"):
                # ImageLoaderPolicy -> imageloader, loader
                base = model_name[:-6]  # Remove "policy"
                candidates.append(base)
                if base.startswith("image"):
                    candidates.append(base[5:])  # Remove "image" prefix
            if model_name.endswith("config"):
                candidates.append(model_name[:-6])
            
            candidates.append(model_name)
            
            # Try to find matching section
            section_found = False
            for key in candidates:
                if key and isinstance(data.get(key), dict):
                    data = data[key]
                    section_found = True
                    break
            
            # 3. If no section found, use root data as-is
            # This allows YAML files without sections to work directly
            if not section_found:
                pass  # Use root data directly
        
        # ensure dict keys are strings
        data = {str(k): v for k, v in data.items()}
        try:
            return model(**data)
        except ValidationError as e:
            raise TypeError(f"[ConfigLoader] Failed to load config as model '{model.__name__}': {e}")
