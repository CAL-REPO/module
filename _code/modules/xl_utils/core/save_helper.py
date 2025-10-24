# -*- coding: utf-8 -*-
"""
xl_utils/core/save_helper.py
SavePolicy 기반 저장 결정 헬퍼

중복된 SavePolicy 처리 로직을 통합
"""

from typing import Optional
from .policy import SavePolicy


class SavePolicyHelper:
    """SavePolicy 기반 저장 결정 헬퍼
    
    Purpose:
        - XwWb, XwWs에 분산된 SavePolicy 로직 통합
        - 저장 시점 결정 로직 일원화
        - DRY (Don't Repeat Yourself) 원칙 준수
    
    Usage:
        >>> from xl_utils.core.save_helper import SavePolicyHelper
        >>> 
        >>> # Workbook close 시
        >>> should_save = SavePolicyHelper.should_save("close", save_policy, explicit_save)
        >>> 
        >>> # Cell write 시
        >>> should_save = SavePolicyHelper.should_save("write", save_policy)
        >>> 
        >>> # Context exit 시
        >>> should_save = SavePolicyHelper.should_save("exit", save_policy)
    """
    
    @staticmethod
    def should_save(
        event: str,  # "write" | "close" | "exit"
        save_policy: Optional[SavePolicy] = None,
        explicit_save: Optional[bool] = None
    ) -> bool:
        """저장 여부 결정
        
        우선순위:
        1. 명시적 save 인자 (True/False)
        2. SavePolicy 기반 판단
        3. False (기본값 - 저장 안 함)
        
        Args:
            event: 저장 이벤트 종류
                - "write": 셀/범위 쓰기 직후
                - "close": Workbook 닫을 때
                - "exit": Context manager 종료 시
            save_policy: SavePolicy 인스턴스 (optional)
            explicit_save: 명시적 저장 지시 (optional)
        
        Returns:
            bool: True면 저장, False면 저장 안 함
        
        Examples:
            >>> # 1. 명시적 save=True (최우선)
            >>> SavePolicyHelper.should_save("write", save_policy, explicit_save=True)
            True
            
            >>> # 2. SavePolicy.strategy="on_write" + event="write"
            >>> policy = SavePolicy(strategy="on_write")
            >>> SavePolicyHelper.should_save("write", policy)
            True
            
            >>> # 3. SavePolicy.strategy="on_close" + event="close"
            >>> policy = SavePolicy(strategy="on_close")
            >>> SavePolicyHelper.should_save("close", policy)
            True
            
            >>> # 4. SavePolicy.strategy="on_exit" + event="exit"
            >>> policy = SavePolicy(strategy="on_exit")
            >>> SavePolicyHelper.should_save("exit", policy)
            True
            
            >>> # 5. 정책 없으면 False
            >>> SavePolicyHelper.should_save("write", None)
            False
        """
        # 1순위: 명시적 save 인자
        if explicit_save is not None:
            return explicit_save
        
        # 2순위: SavePolicy 기반 판단
        if save_policy:
            strategy = save_policy.strategy
            
            if event == "write":
                # on_write 전략일 때만 저장
                return strategy == "on_write"
            
            elif event == "close":
                # on_close 또는 on_exit 전략일 때 저장
                return strategy in ("on_close", "on_exit")
            
            elif event == "exit":
                # on_exit 전략일 때만 저장
                return strategy == "on_exit"
        
        # 3순위: 기본값 (저장 안 함)
        return False
    
    @staticmethod
    def explain_decision(
        event: str,
        save_policy: Optional[SavePolicy] = None,
        explicit_save: Optional[bool] = None
    ) -> str:
        """저장 결정 이유 설명 (디버깅용)
        
        Args:
            event: 저장 이벤트 종류
            save_policy: SavePolicy 인스턴스
            explicit_save: 명시적 저장 지시
        
        Returns:
            str: 결정 이유 문자열
        
        Example:
            >>> policy = SavePolicy(strategy="on_write")
            >>> SavePolicyHelper.explain_decision("write", policy)
            "Save: True (reason: SavePolicy.strategy='on_write' matches event='write')"
        """
        will_save = SavePolicyHelper.should_save(event, save_policy, explicit_save)
        
        if explicit_save is not None:
            reason = f"explicit_save={explicit_save}"
        elif save_policy:
            reason = f"SavePolicy.strategy='{save_policy.strategy}' {'matches' if will_save else 'does not match'} event='{event}'"
        else:
            reason = "no policy provided"
        
        return f"Save: {will_save} (reason: {reason})"
