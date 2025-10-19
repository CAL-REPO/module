# -*- coding: utf-8 -*-
"""cfg_utils_v2 - Configuration Management v2.

Adapter/EntryPoint Pattern:
- adapter/: Pure logic (Standalone usable)
  - Config: KeyPath State 기반 설정 로드
- entry_point/: YAML-based (Delegation to adapter)
  - ConfigLoader: YAML 정책 + Config 위임
- service/: Reusable utilities
  - PolicyLoader: 정책 로딩/파싱 전문

Usage:
    >>> # 1. EntryPoint (YAML 정책 사용)
    >>> from cfg_utils import ConfigLoader
    >>> loader = ConfigLoader(config_loader_cfg_path="config_loader.yaml")
    >>> data = loader.to_dict()
    
    >>> # 2. Adapter (Standalone)
    >>> from cfg_utils.adapter import Config
    >>> config = Config(source_policy=SourcePolicy())
    >>> state = config.load(src=("config.yaml", "image"))
    
    >>> # 3. Service (정책 로딩)
    >>> from cfg_utils.service import PolicyLoader
    >>> policy = PolicyLoader.load_from_yaml("config_loader.yaml")
"""

# Core components
from .core import (
    SourceBase,
    SourcePolicy,
    NormalizePolicy,
    MergePolicy,
)

# Adapter (Standalone)
from .adapter import Config

# EntryPoint (YAML-based)
from .entry_point import ConfigLoader

# Service layer
from .services import UnifiedSource

__all__ = [
    # Core
    'SourceBase',
    'SourcePolicy',
    'NormalizePolicy',
    'MergePolicy',
    # Adapter
    'Config',
    # EntryPoint
    'ConfigLoader',
    # Service
    'UnifiedSource',
]

__version__ = '2.0.0'
