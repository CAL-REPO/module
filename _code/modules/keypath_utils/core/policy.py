# -*- coding: utf-8 -*-
# keypath_utils/core/policy.py
# Pydantic 기반 KeyPath 정책 정의 및 판단 로직

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any, Optional
from data_utils.core.types import KeyPath
from unify_utils.core.policy import UnifyPolicyBase, VarsResolverPolicy


class KeyPathStatePolicy(BaseModel):
    """KeyPathState 동작 정책 관리.
    
    정책 판단 로직을 중앙화하여 SRP 준수 및 확장성 확보.
    각 정책 필드는 KeyPathState의 동작을 제어하며,
    판단 로직은 메서드로 캡슐화되어 테스트 및 확장이 용이함.
    """
    
    allow_override: bool = Field(
        default=True,
        description="None 값 override 허용 여부. True일 경우 None도 설정됨"
    )
    deep_merge: bool = Field(
        default=True,
        description="merge 시 DictOps.deep_update 사용 여부 (기본값)"
    )
    strict_path: bool = Field(
        default=False,
        description="존재하지 않는 path 접근 시 KeyError 발생 여부"
    )
    auto_create_containers: bool = Field(
        default=True,
        description="set/override 시 중간 dict 자동 생성 여부"
    )
    
    # ============================================================
    # 정책 판단 메서드 (Policy Decision Methods)
    # ============================================================
    
    def should_override(self, value: Any) -> bool:
        """Override 수행 여부 판단.
        
        Args:
            value: 설정하려는 값
            
        Returns:
            True if override should proceed
            
        Examples:
            >>> policy = KeyPathStatePolicy(allow_override=True)
            >>> policy.should_override(None)
            True
            >>> policy = KeyPathStatePolicy(allow_override=False)
            >>> policy.should_override(None)
            False
            >>> policy.should_override(123)
            True
        """
        if self.allow_override:
            return True
        return value is not None
    
    def get_merge_mode(self, explicit_deep: Optional[bool] = None) -> bool:
        """Merge mode 결정.
        
        명시적으로 지정된 deep 모드가 우선순위를 가지며,
        없을 경우 정책의 기본값(deep_merge)을 사용.
        
        Args:
            explicit_deep: 명시적으로 지정된 deep 모드 (None이면 정책 기본값 사용)
            
        Returns:
            True for deep merge, False for shallow merge
            
        Examples:
            >>> policy = KeyPathStatePolicy(deep_merge=True)
            >>> policy.get_merge_mode()
            True
            >>> policy.get_merge_mode(explicit_deep=False)
            False
        """
        return explicit_deep if explicit_deep is not None else self.deep_merge
    
    def validate_path_access(self, path: KeyPath, exists: bool) -> None:
        """Path 접근 유효성 검증.
        
        strict_path=True일 경우 존재하지 않는 path 접근 시 KeyError 발생.
        디버깅 및 타입 안정성 향상에 유용.
        
        Args:
            path: 접근하려는 경로
            exists: 경로 존재 여부
            
        Raises:
            KeyError: strict_path=True이고 path가 존재하지 않는 경우
            
        Examples:
            >>> policy = KeyPathStatePolicy(strict_path=True)
            >>> policy.validate_path_access("nonexistent__path", exists=False)
            Traceback (most recent call last):
                ...
            KeyError: "Path not found: 'nonexistent.path'"
            
            >>> policy = KeyPathStatePolicy(strict_path=False)
            >>> policy.validate_path_access("nonexistent__path", exists=False)  # No error
        """
        if self.strict_path and not exists:
            raise KeyError(f"Path not found: {path!r}")
    
    def should_create_containers(self) -> bool:
        """중간 컨테이너 자동 생성 여부.
        
        set/override 시 중간 경로의 dict를 자동 생성할지 결정.
        False일 경우 명시적으로 생성된 경로만 사용 가능.
        
        Returns:
            True if auto-creation is enabled
            
        Examples:
            >>> policy = KeyPathStatePolicy(auto_create_containers=True)
            >>> policy.should_create_containers()
            True
        """
        return self.auto_create_containers

class KeyPathNormalizePolicy(UnifyPolicyBase):
    """KeyPathNormalizer 전용 정책

    Attributes:
        sep: 구분자 (기본값: "__" - copilot-instructions.md 규칙 준수)
        collapse: 연속 구분자 병합 여부 (빈 세그먼트 제거)
        accept_dot: sep 없을 때 "." fallback 허용 여부
        escape_char: 이스케이프 문자 (구분자를 리터럴로 처리)
        enable_list_index: [0], [1] 형태 배열 인덱스 지원 (향후 확장용)
    """
    sep: str = Field(default="__", description="경로 구분자 (프로젝트 표준)")
    collapse: bool = Field(default=True, description="빈 세그먼트 제거 여부")
    accept_dot: bool = Field(default=False, description="구분자 실패 시 '.' fallback 허용")
    escape_char: Optional[str] = Field(default=None, description="이스케이프 문자 (__ 구분자에는 불필요)")
    enable_list_index: bool = Field(default=False, description="배열 인덱스 지원 [0], [1]")

# ---------------------------------------------------------------------------
# KeyPath Resolver Policy (프로젝트 특정 기능)
# ---------------------------------------------------------------------------

class KeyPathResolverPolicy(VarsResolverPolicy):
    """KeyPath 기반 중첩 경로 참조 Resolver 정책
    
    ✅ VarsResolverPolicy 확장:
    - 공통 기능: 환경변수, Context, 단순 참조 (상속)
    - 추가 기능: KeyPath 중첩 경로 (a__b__c)
    
    프로젝트 특정:
    - keypath_sep: "__" 구분자 (프로젝트 표준)
    - KeyPathAccessor를 통한 중첩 경로 탐색
    
    Examples:
        >>> # KeyPath 중첩 참조
        >>> policy = KeyPathResolverPolicy(keypath_sep="__")
        
        >>> # 환경 변수 + Context + KeyPath
        >>> policy = KeyPathResolverPolicy(
        ...     keypath_sep="__",
        ...     enable_env=True,
        ...     enable_context=True,
        ...     context={"HOST": "localhost"}
        ... )
    """
    
    keypath_sep: str = Field("__", description="KeyPath 구분자 (프로젝트 표준)")