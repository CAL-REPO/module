# -*- coding: utf-8 -*-
# xl_utils/policy.py
# xlwings 관련 모든 정책 정의 및 검증
# translate_utils.core.policy 패턴 적용: cfg_utils/logs_utils 통합

from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Union, Literal
from pathlib import Path

from cfg_utils import ConfigLoader
from structured_io import BaseParserPolicy
from logs_utils import LogPolicy
from fso_utils import FSOOpsPolicy, ExistencePolicy


class SheetConfig(BaseModel):
    """Sheet configuration with column alias support.
    
    Attributes:
        sheet_name: Sheet name or index (str/int)
        column_alias: Column alias preset name or dict
            - str: Preset name (e.g., "PRODUCT_LIST")
            - dict: Custom alias mapping {key: [alias1, alias2, ...]}
            - None: No alias mapping
    
    Example:
        >>> # Using preset
        >>> SheetConfig(sheet_name="Sheet1", column_alias="PRODUCT_LIST")
        
        >>> # Using custom dict
        >>> SheetConfig(
        ...     sheet_name="Data",
        ...     column_alias={"date": ["날짜", "date"], "cas": ["cas", "cas no"]}
        ... )
    """
    sheet_name: Union[str, int] = Field(default="Sheet1", description="Sheet name or index")
    column_alias: Optional[Union[str, Dict[str, List[str]]]] = Field(
        default=None,
        description="Column alias preset name or custom dict"
    )
    
    def get_column_aliases(self) -> Dict[str, List[str]]:
        """Get resolved column alias dictionary.
        
        Returns:
            Column alias dict {key: [alias1, alias2, ...]}
        
        Example:
            >>> config = SheetConfig(column_alias="PRODUCT_LIST")
            >>> aliases = config.get_column_aliases()
            >>> print(aliases["cas"])
            ['cas', 'cas no', 'casno', ...]
        """
        if self.column_alias is None:
            return {}
        
        # Preset name (str)
        if isinstance(self.column_alias, str):
            from xl_utils.presets import get_preset
            return get_preset(self.column_alias)
        
        # Custom dict
        return self.column_alias


class SourceConfig(BaseModel):
    """Source Excel file and sheet configuration.
    
    Attributes:
        file_path: Excel file path
        sheet: Sheet configuration (sheet_name + column_alias)
    """
    file_path: str = Field(default="", description="Excel file path")
    sheet: Union[str, int, SheetConfig] = Field(
        default_factory=lambda: SheetConfig(),
        description="Sheet config (str/int or SheetConfig)"
    )
    
    @field_validator('sheet', mode='before')
    @classmethod
    def normalize_sheet(cls, v):
        """Normalize sheet value to SheetConfig.
        
        Args:
            v: str, int, dict, or SheetConfig
        
        Returns:
            SheetConfig instance
        """
        if isinstance(v, SheetConfig):
            return v
        
        # str or int -> SheetConfig(sheet_name=v)
        if isinstance(v, (str, int)):
            return SheetConfig(sheet_name=v)
        
        # dict -> SheetConfig(**v)
        if isinstance(v, dict):
            return SheetConfig(**v)
        
        return v
    
    def get_sheet_name(self) -> Union[str, int]:
        """Get sheet name from sheet config."""
        if isinstance(self.sheet, SheetConfig):
            return self.sheet.sheet_name
        return self.sheet
    
    def get_column_aliases(self) -> Dict[str, List[str]]:
        """Get column aliases from sheet config."""
        if isinstance(self.sheet, SheetConfig):
            return self.sheet.get_column_aliases()
        return {}


class XwAppPolicy(BaseModel):
    """Excel Application 실행 정책"""
    visible: bool = Field(True, description="Excel 창 표시 여부")
    display_alerts: bool = Field(False, description="경고창 표시 여부")
    screen_updating: bool = Field(True, description="화면 갱신 허용 여부")
    add_book: bool = Field(False, description="App 생성 시 기본 Workbook 추가 여부")


# =============================================================================
# 통합 정책 (New)
# =============================================================================

class SavePolicy(BaseModel):
    """통합 저장 정책 - 저장 전략을 한 곳에서 관리
    
    기존 산재된 저장 옵션 통합:
    - XwLifecyclePolicy.save_on_exit
    - XwWbPolicy.auto_save
    - XwWsPolicy.auto_save_on_write
    
    Attributes:
        strategy: 저장 시점 전략
            - manual: 수동 저장만
            - on_write: 셀 쓰기마다 저장
            - on_close: 워크북 닫을 때 저장
            - on_exit: 앱 종료 시 저장 (기본값)
        target: 저장 대상
            - current_wb: 현재 워크북만
            - all_wb: 모든 워크북
        backup: 저장 시 백업 파일 생성 여부
        save_attached_instance: 기존 Excel 인스턴스도 저장할지
    """
    strategy: Literal["manual", "on_write", "on_close", "on_exit"] = Field(
        "on_exit",
        description="저장 시점 전략"
    )
    target: Literal["current_wb", "all_wb"] = Field(
        "current_wb",
        description="저장 대상 범위"
    )
    backup: bool = Field(False, description="백업 파일 생성 여부")
    save_attached_instance: bool = Field(False, description="기존 Excel 인스턴스 저장 여부")


class PerformancePolicy(BaseModel):
    """성능 최적화 정책 - 대용량 데이터 처리 최적화
    
    Attributes:
        screen_updating: 화면 갱신 여부 (False = 빠름, 변화 안 보임)
        display_alerts: 경고창 표시 여부 (False = 빠름)
        calculation: Excel 계산 모드
            - auto: 변경 시마다 자동 재계산 (느림, 정확함)
            - manual: 수동 계산만 (빠름)
            - semiauto: 테이블만 자동 계산
        enable_events: 이벤트 핸들러 활성화
        interactive: 사용자 입력 허용
        clear_clipboard: 종료 시 클립보드 비우기
    """
    screen_updating: bool = Field(True, description="화면 갱신 허용")
    display_alerts: bool = Field(False, description="경고창 표시")
    calculation: Literal["auto", "manual", "semiauto"] = Field(
        "auto",
        description="Excel 계산 모드"
    )
    enable_events: bool = Field(True, description="이벤트 핸들러 활성화")
    interactive: bool = Field(True, description="사용자 입력 허용")
    clear_clipboard: bool = Field(True, description="종료 시 클립보드 비우기")


class ErrorHandlingPolicy(BaseModel):
    """에러 처리 정책 - 복구 전략 정의
    
    Attributes:
        on_file_not_found: 파일 없을 때 동작
            - error: 에러 발생
            - create: 새 파일 생성
            - skip: 무시하고 계속
        on_sheet_not_found: 시트 없을 때 동작
            - error: 에러 발생
            - create: 새 시트 생성
            - first: 첫 번째 시트 사용
        on_save_error: 저장 실패 시 동작
            - error: 에러 발생
            - retry: 재시도
            - ignore: 무시
        retry_count: 재시도 횟수
        retry_delay: 재시도 대기 시간 (초)
    """
    on_file_not_found: Literal["error", "create", "skip"] = Field(
        "error",
        description="파일 없을 때 동작"
    )
    on_sheet_not_found: Literal["error", "create", "first"] = Field(
        "create",
        description="시트 없을 때 동작"
    )
    on_save_error: Literal["error", "retry", "ignore"] = Field(
        "error",
        description="저장 실패 시 동작"
    )
    retry_count: int = Field(3, ge=0, description="재시도 횟수")
    retry_delay: float = Field(1.0, ge=0.0, description="재시도 대기 시간(초)")


class PathValidationPolicy(BaseModel):
    """경로 검증 정책 - fso_utils 통합
    
    fso_utils의 FSOOpsPolicy를 래핑하여 Excel 특화 옵션 추가
    
    Attributes:
        fso: FSOOps 정책 (존재 여부, 생성 여부 등)
        template_path: 템플릿 파일 경로 (파일 생성 시 사용)
        backup_if_exists: 기존 파일 백업 여부
        overwrite: 기존 파일 덮어쓰기 여부
    """
    fso: FSOOpsPolicy = Field(
        default_factory=lambda: FSOOpsPolicy(
            as_type="file",
            exist=ExistencePolicy(
                must_exist=True,
                create_if_missing=False,
                overwrite=False
            )
        ),
        description="fso_utils 정책"
    )
    template_path: Optional[str] = Field(None, description="템플릿 파일 경로")
    backup_if_exists: bool = Field(False, description="기존 파일 백업")
    overwrite: bool = Field(False, description="기존 파일 덮어쓰기")


# =============================================================================
# ExcelLoad Adapter Policy
# =============================================================================

class ExcelLoadPolicy(BaseModel):
    """Adapter Policy (target 없음, 순수 비즈니스 로직)
    
    Excel 파일 접근 및 조작 정책만 포함.
    target은 인자로 받아서 처리합니다.
    
    Attributes:
        name: Policy 식별자 (SectionExtractor 호환)
        
        # ===== 통합 정책 =====
        save: 통합 저장 정책
        performance: 성능 최적화 정책
        error_handling: 에러 처리 정책
        path_validation: 경로 검증 정책 (fso_utils 통합)
        
        # ===== 기본 정책 =====
        xw_app: Excel Application 실행 정책
        
        log: 로깅 설정 (logs_utils LogPolicy)
    
    우선순위 규칙:
        통합 정책이 모든 동작 제어
    """
    name: str = Field(default="excel", description="Policy name for section extraction")
    
    # ===== 통합 정책 =====
    save: SavePolicy = Field(default_factory=SavePolicy)  # type: ignore
    performance: PerformancePolicy = Field(default_factory=PerformancePolicy)  # type: ignore
    error_handling: ErrorHandlingPolicy = Field(default_factory=ErrorHandlingPolicy)  # type: ignore
    path_validation: PathValidationPolicy = Field(default_factory=PathValidationPolicy)  # type: ignore
    
    # ===== 기본 정책 =====
    xw_app: XwAppPolicy = Field(default_factory=XwAppPolicy)  # type: ignore
    
    log: Optional[LogPolicy] = None  # ✨ logging 설정 (Optional)
    
    def should_save(self, event: Literal["write", "close", "exit"]) -> bool:
        """저장 정책에 따라 저장 여부 결정
        
        Args:
            event: 이벤트 타입 ("write", "close", "exit")
        
        Returns:
            저장해야 하면 True
        """
        if self.save.strategy == "manual":
            return False
        elif self.save.strategy == "on_write":
            return event == "write"
        elif self.save.strategy == "on_close":
            return event in ("close", "exit")
        elif self.save.strategy == "on_exit":
            return event == "exit"
        return False


class ExcelLoaderPolicy(BaseModel):
    """EntryPoint Policy (source 포함, source 역할)
    
    source에서 Excel 파일 정보를 가져와 ExcelLoad에 전달합니다.
    
    Attributes:
        name: Policy 식별자 (SectionExtractor 호환)
        source: 소스 Excel 파일 설정
        excel: ExcelLoad adapter 설정 (ExcelLoadPolicy)
    """
    name: str = Field(default="excel_loader", description="Section name in YAML config")
    source: SourceConfig = Field(default_factory=SourceConfig)  # type: ignore
    excel: ExcelLoadPolicy = Field(default_factory=ExcelLoadPolicy)  # type: ignore


