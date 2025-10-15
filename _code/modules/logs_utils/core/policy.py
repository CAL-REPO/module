# -*- coding: utf-8 -*-
# logs_utils/core/policy.py

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator


LogLevel = Literal["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"]


class SinkPolicy(BaseModel):
    """loguru Sink 설정 정책"""
    sink_type: Literal["file", "console"] = "console"
    filepath: Optional[Path] = None
    level: LogLevel = "INFO"
    format: str = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    rotation: Optional[Union[str, int]] = "10 MB"
    retention: Optional[Union[str, int]] = "7 days"
    compression: Optional[str] = None
    enqueue: bool = True
    serialize: bool = False
    backtrace: bool = True
    diagnose: bool = True
    colorize: bool = True
    catch: bool = True
    
    @field_validator("filepath")
    @classmethod
    def validate_filepath(cls, v: Optional[Path], info) -> Optional[Path]:
        """file sink인 경우 filepath 필수"""
        data = info.data
        if data.get("sink_type") == "file" and v is None:
            raise ValueError("filepath is required when sink_type='file'")
        if v is not None and not isinstance(v, Path):
            return Path(v)
        return v
    
    def to_sink_kwargs(self) -> dict[str, Any]:
        """loguru logger.add()에 전달할 kwargs 생성"""
        kwargs: dict[str, Any] = {
            "level": self.level,
            "format": self.format,
            "enqueue": self.enqueue,
            "serialize": self.serialize,
            "backtrace": self.backtrace,
            "diagnose": self.diagnose,
            "catch": self.catch,
        }
        
        if self.sink_type == "file":
            kwargs["sink"] = str(self.filepath)
            kwargs["rotation"] = self.rotation
            kwargs["retention"] = self.retention
            if self.compression:
                kwargs["compression"] = self.compression
        elif self.sink_type == "console":
            import sys
            kwargs["sink"] = sys.stderr
            kwargs["colorize"] = self.colorize
        
        return kwargs


class LogPolicy(BaseModel):
    """로깅 정책"""
    name: str = "app"
    level: LogLevel = "INFO"
    sinks: list[SinkPolicy] = Field(default_factory=lambda: [SinkPolicy()])
    context: dict[str, Any] = Field(default_factory=dict)
    
    @field_validator("sinks")
    @classmethod
    def validate_sinks(cls, v: list[SinkPolicy]) -> list[SinkPolicy]:
        """최소 하나 이상의 Sink 필요"""
        if not v:
            return [SinkPolicy(sink_type="console")]
        return v
    
    def get_file_sinks(self) -> list[SinkPolicy]:
        """파일 Sink만 필터링"""
        return [s for s in self.sinks if s.sink_type == "file"]
    
    def get_console_sinks(self) -> list[SinkPolicy]:
        """콘솔 Sink만 필터링"""
        return [s for s in self.sinks if s.sink_type == "console"]
    
    def ensure_directories(self) -> None:
        """파일 Sink의 디렉토리 생성"""
        for sink in self.get_file_sinks():
            if sink.filepath:
                sink.filepath.parent.mkdir(parents=True, exist_ok=True)
