# -*- coding: utf-8 -*-
# logs_utils/services/factory.py
# Logger factory function following the same pattern as crawl_utils

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Union

from pydantic import BaseModel

from logs_utils.services.manager import LogManager


def create_logger(
    cfg_like: Union[BaseModel, Path, str, dict, list, None] = None,
    *,
    policy: Optional[Any] = None,
    **overrides: Any
) -> LogManager:
    """Logger 팩토리 함수
    
    LogManager를 생성하여 반환합니다.
    ConfigLoader 패턴을 따르며, 다양한 형태의 입력을 지원합니다.
    
    Args:
        cfg_like: 설정 소스
            - BaseModel: LogPolicy 인스턴스
            - str/Path: YAML 파일 경로
            - dict: 설정 딕셔너리
            - list: 여러 YAML 파일
            - None: 기본 설정
        policy: ConfigPolicy 인스턴스
        **overrides: 런타임 오버라이드
    
    Returns:
        LogManager 인스턴스
    
    Example:
        >>> # 간단한 사용
        >>> logger_manager = create_logger({"name": "myapp"})
        >>> logger_manager.logger.info("Hello")
        
        >>> # YAML 파일에서 로드
        >>> logger_manager = create_logger("configs/logging.yaml")
        
        >>> # 런타임 오버라이드
        >>> logger_manager = create_logger(
        ...     "config.yaml",
        ...     name="custom_app",
        ...     level="DEBUG"
        ... )
        
        >>> # Policy 직접 전달
        >>> from logs_utils import LogPolicy, SinkPolicy
        >>> policy = LogPolicy(name="myapp", sinks=[...])
        >>> logger_manager = create_logger(policy)
    """
    return LogManager(cfg_like, policy=policy, **overrides)


# Convenience alias
logger_factory = create_logger
