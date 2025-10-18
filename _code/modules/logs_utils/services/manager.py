# -*- coding: utf-8 -*-
# logs_utils/services/manager.py
# LogManager with ConfigLoader pattern and loguru Sink integration

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Union, TYPE_CHECKING

from pydantic import BaseModel
from loguru import logger

if TYPE_CHECKING:
    from logs_utils.core.policy import LogPolicy


class LogManager:
    """Log Manager with ConfigLoader v2 pattern
    
    loguru를 사용한 로깅 관리자입니다.
    cfg_utils_v2.ConfigLoader를 사용하여 정책을 로드합니다.
    
    Example:
        >>> # LogPolicy 직접 전달
        >>> from logs_utils import LogPolicy, SinkPolicy
        >>> policy = LogPolicy(name="myapp", sinks=[SinkPolicy(sink_type="console")])
        >>> manager = LogManager(policy)
        
        >>> # YAML에서 로드
        >>> manager = LogManager("configs/logging.yaml")
        
        >>> # dict로 생성
        >>> manager = LogManager({"name": "myapp", "sinks": [{"sink_type": "console"}]})
    """
    
    def __init__(
        self,
        cfg_like: Union[BaseModel, Path, str, dict, None] = None,
        *,
        context: Optional[dict] = None,
        **overrides: Any
    ):
        """LogManager 초기화
        
        Args:
            cfg_like: 설정 소스
                - LogPolicy: LogPolicy 인스턴스 (직접 전달)
                - str/Path: YAML 파일 경로
                - dict: 설정 딕셔너리
                - None: 기본 설정 (logging.yaml)
            context: 추가 context (ConfigLoader 등에서 전달)
            **overrides: 런타임 오버라이드
        """
        self.config = self._load_config(cfg_like, **overrides)
        self._handler_ids: list[int] = []
        
        # 추가 context 병합
        self._extra_context = context or {}
        
        # ✨ enabled=False면 handler 등록 안 함 (loguru가 자동으로 no-op)
        if self.config.enabled:
            self._configure_logger()
        
        # ✨ bind()로 service context + 추가 context 병합
        full_context = {**self.config.context, **self._extra_context}
        self._bound_logger = logger.bind(service=self.config.name, **full_context)
        
        # ✨ context-bound logger 생성 (service별 격리)
        self._logger = self._bound_logger
    
    def _load_config(
        self,
        cfg_like: Union[BaseModel, Path, str, dict, None],
        **overrides: Any
    ) -> "LogPolicy":
        """LogPolicy 로드 (cfg_utils_v2 사용)"""
        from logs_utils.core.policy import LogPolicy
        
        # 1. LogPolicy 인스턴스가 직접 전달된 경우
        if isinstance(cfg_like, LogPolicy):
            return cfg_like
        
        # 2. cfg_utils_v2.ConfigLoader 사용
        try:
            from cfg_utils_v2 import ConfigLoader
            
            # 기본 LogPolicy를 base로 사용
            base_policy = LogPolicy()
            
            # cfg_like가 None이면 기본 logging.yaml 사용
            if cfg_like is None:
                default_path = Path(__file__).parent.parent / "configs" / "logging.yaml"
                override_sources: Any = [(str(default_path), "logging")]
            # str/Path면 YAML 파일
            elif isinstance(cfg_like, (str, Path)):
                override_sources = [(str(cfg_like), None)]
            # dict면 그대로 사용
            elif isinstance(cfg_like, dict):
                override_sources = [(cfg_like, None)]
            else:
                # 기타 경우 기본 정책 사용
                override_sources = []
            
            # ConfigLoader로 병합
            loader = ConfigLoader(
                base_sources=[(base_policy, "logging")],
                override_sources=override_sources if override_sources else None
            )
            
            # overrides 적용
            if overrides:
                for key, value in overrides.items():
                    loader.override(f"logging__{key}", value)
            
            # LogPolicy로 변환
            result = loader.to_model(LogPolicy, section="logging")
            return result  # type: ignore
            
        except ImportError:
            # cfg_utils_v2가 없으면 기본 설정
            default_overrides = {"name": "app"}
            default_overrides.update(overrides)
            return LogPolicy(**default_overrides)
    
    def _configure_logger(self) -> None:
        """loguru logger 설정 (filter 기반 service 격리)"""
        # 디렉토리 생성
        self.config.ensure_directories()
        
        # ❌ logger.remove() 제거 (다른 서비스 핸들러 보존)
        
        # Sink 추가 with service filter
        for sink_policy in self.config.sinks:
            sink_kwargs = sink_policy.to_sink_kwargs()
            
            # ✨ filter 추가: 이 서비스의 로그만 처리
            service_name = self.config.name
            
            def make_filter(svc_name):
                """클로저를 사용하여 service_name 캡처"""
                def service_filter(record):
                    return record["extra"].get("service") == svc_name
                return service_filter
            
            sink_kwargs["filter"] = make_filter(service_name)
            
            handler_id = logger.add(**sink_kwargs)
            self._handler_ids.append(handler_id)
    
    @property
    def logger(self):
        """context-bound logger 인스턴스 반환"""
        return self._bound_logger
    
    def remove_handlers(self) -> None:
        """등록된 핸들러 제거"""
        for handler_id in self._handler_ids:
            try:
                logger.remove(handler_id)
            except ValueError:
                pass
        self._handler_ids.clear()
    
    def __del__(self):
        """소멸자 - 핸들러 정리"""
        try:
            self.remove_handlers()
        except Exception:
            pass
