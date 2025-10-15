# -*- coding: utf-8 -*-
# logs_utils/services/manager.py
# LogManager with ConfigLoader pattern and loguru Sink integration

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Union, TYPE_CHECKING

from pydantic import BaseModel
from loguru import logger

if TYPE_CHECKING:
    from cfg_utils import ConfigLoader, ConfigPolicy
    from logs_utils.core.policy import LogPolicy


class LogManager:
    """Log Manager with ConfigLoader pattern
    
    loguru를 사용한 로깅 관리자입니다.
    ConfigLoader 패턴을 따라 YAML, dict, Policy 인스턴스 등으로 초기화할 수 있습니다.
    
    Example:
        >>> # dict로 생성
        >>> manager = LogManager({"name": "myapp", "sinks": [{"sink_type": "console"}]})
        >>> manager.logger.info("Hello")
        
        >>> # YAML에서 로드
        >>> manager = LogManager("configs/logging.yaml")
        
        >>> # Policy 직접 전달
        >>> from logs_utils import LogPolicy, SinkPolicy
        >>> policy = LogPolicy(name="myapp", sinks=[SinkPolicy(sink_type="console")])
        >>> manager = LogManager(policy)
    """
    
    def __init__(
        self,
        cfg_like: Union[BaseModel, Path, str, dict, list, None] = None,
        *,
        policy_overrides: Optional[dict] = None,
        **overrides: Any
    ):
        """LogManager 초기화
        
        Args:
            cfg_like: 설정 소스
                - BaseModel: LogPolicy 인스턴스
                - str/Path: YAML 파일 경로
                - dict: 설정 딕셔너리
                - list: 여러 YAML 파일
                - None: 기본 설정
            policy_overrides: ConfigPolicy 필드 개별 오버라이드 (merge_mode, yaml.source_paths 등)
            **overrides: 런타임 오버라이드
        """
        self.config = self._load_config(cfg_like, policy_overrides=policy_overrides, **overrides)
        self._handler_ids: list[int] = []
        self._configure_logger()
        
        # ✨ bind()로 service context 추가된 logger 생성
        self._bound_logger = logger.bind(service=self.config.name, **self.config.context)
        
        # ✨ context-bound logger 생성 (service별 격리)
        self._logger = logger.bind(service=self.config.name, **self.config.context)
    
    def _load_config(
        self,
        cfg_like: Union[BaseModel, Path, str, dict, list, None],
        *,
        policy_overrides: Optional[dict] = None,
        **overrides: Any
    ) -> "LogPolicy":
        """LogPolicy 로드"""
        from logs_utils.core.policy import LogPolicy
        
        # ConfigLoader.load() 사용 (간소화)
        try:
            from cfg_utils import ConfigLoader
            
            if cfg_like is None:
                default_path = Path(__file__).parent.parent / "configs" / "logging.yaml"
                if policy_overrides is None:
                    policy_overrides = {}
                
                # 데이터 파일 + 섹션 지정
                policy_overrides.setdefault("yaml.source_paths", {
                    "path": str(default_path),
                    "section": "logging"
                })
            
            return ConfigLoader.load(
                cfg_like,
                model=LogPolicy,
                policy_overrides=policy_overrides,
                **overrides
            )
        except ImportError:
            # cfg_utils가 없으면 기본 설정
            return LogPolicy(name="app", **overrides)
    
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
