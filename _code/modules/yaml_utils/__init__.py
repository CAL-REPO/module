# -*- coding: utf-8 -*-
# yaml_utils/__init__.py
# description: YAML 파싱·덤프·파일 입출력 통합 유틸리티 패키지

from __future__ import annotations

"""
yaml_utils — YAML 입출력 및 정책 기반 파서/덤퍼 유틸리티

Public API
-----------
- Policy
  - YamlParserPolicy
  - YamlDumperPolicy

- Core
  - YamlParser
  - YamlDumper
  - YamlFileIO
"""

# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------
from .policy import (
    YamlParserPolicy,
    YamlDumperPolicy,
)

# ---------------------------------------------------------------------------
# Core Components
# ---------------------------------------------------------------------------
from .parser import YamlParser
from .dumper import YamlDumper
from .file_io import YamlFileIO

# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------
def yaml_parser(
    *,
    enable_env: bool = True,
    enable_include: bool = True,
    enable_placeholder: bool = True,
    enable_reference: bool = False,
    safe_mode: bool = True,
    encoding: str = "utf-8",
) -> YamlParser:
    """YamlParser 생성 헬퍼"""
    from .policy import YamlParserPolicy
    policy = YamlParserPolicy(
        enable_env=enable_env,
        enable_include=enable_include,
        enable_placeholder=enable_placeholder,
        enable_reference=enable_reference,
        safe_mode=safe_mode,
        encoding=encoding,
    )  # pyright: ignore[reportCallIssue]
    return YamlParser(policy) 

def yaml_dumper(
    *,
    encoding: str = "utf-8",
    sort_keys: bool = False,
    indent: int = 2,
    default_flow_style: bool = False,
    allow_unicode: bool = True,
    safe_mode: bool = True,
) -> YamlDumper:
    """YamlDumper 생성 헬퍼"""
    from .policy import YamlDumperPolicy
    policy = YamlDumperPolicy(
        encoding=encoding,
        sort_keys=sort_keys,
        indent=indent,
        default_flow_style=default_flow_style,
        allow_unicode=allow_unicode,
        safe_mode=safe_mode,
    )
    return YamlDumper(policy)

def yaml_fileio(
    path: str,
    *,
    parser_policy: YamlParserPolicy | None = None,
    dumper_policy: YamlDumperPolicy | None = None,
) -> YamlFileIO:
    """YamlFileIO 생성 헬퍼"""
    return YamlFileIO(path, parser_policy=parser_policy, dumper_policy=dumper_policy)

# ---------------------------------------------------------------------------
# 공개 인터페이스
# ---------------------------------------------------------------------------
__all__ = [
    # Policy
    "YamlParserPolicy", "YamlDumperPolicy",
    # Core
    "YamlParser", "YamlDumper", "YamlFileIO",
    # Factory helpers
    "yaml_parser", "yaml_dumper", "yaml_fileio",
]
