# -*- coding: utf-8 -*-
# keypath_utils/services/state.py
# KeyPathState 클래스 정의 - 정책 기반 상태 관리

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Dict
from data_utils.core.types import KeyPath
from modules.keypath_utils.core.policy import KeyPathStatePolicy
from modules.keypath_utils.core.accessor import KeyPathAccessor
from data_utils.services.dict_ops import DictOps


@dataclass
class KeyPathState:
    """정책 기반 KeyPath 상태 관리 클래스.
    
    KeyPathModel과 KeyPathStatePolicy를 조합하여 정책 기반으로 상태를 관리합니다.
    - get/set/delete: 기본 접근
    - override: 정책 기반 값 덮어쓰기
    - merge: 정책 기반 병합
    - ensure: 경로 자동 생성
    
    Examples:
        >>> from keypath_utils.services import KeyPathState
        >>> state = KeyPathState()
        >>> state.set("a__b", 1)
        >>> state.get("a__b")
        1
        
        >>> # 정책 적용
        >>> from keypath_utils.core import KeyPathStatePolicy
        >>> policy = KeyPathStatePolicy(allow_override=False)
        >>> state = KeyPathState(policy=policy)
        >>> state.override("key", None)  # 무시됨
    """
    
    name: str = ""
    store: Dict[str, Any] = field(default_factory=dict)
    policy: KeyPathStatePolicy = field(default_factory=lambda: KeyPathStatePolicy()) # type: ignore

    def rename(self, name: str) -> KeyPathState:
        """상태 이름 변경.
        
        Args:
            name: 새로운 이름
            
        Returns:
            Self for chaining
        """
        self.name = name
        return self

    def get(self, path: KeyPath, default: Any = None) -> Any:
        """값 조회 (정책 기반 검증).
        
        정책의 validate_path_access로 경로 존재 여부를 검증.
        strict_path=True일 경우 존재하지 않는 경로 접근 시 KeyError 발생.
        
        Args:
            path: 조회할 경로
            default: 경로가 없을 때 반환할 기본값
            
        Returns:
            조회된 값 또는 default
            
        Raises:
            KeyError: strict_path=True이고 경로가 존재하지 않는 경우
            
        Examples:
            >>> state = KeyPathState()
            >>> state.set("a__b", 1)
            >>> state.get("a__b")
            1
            >>> state.get("nonexistent", "default")
            'default'
            
            >>> policy = KeyPathStatePolicy(strict_path=True)
            >>> state = KeyPathState(policy=policy)
            >>> state.get("nonexistent")  # KeyError
        """
        exists = self.exists(path)
        # ✅ 정책에 경로 검증 위임
        self.policy.validate_path_access(path, exists)
        return KeyPathAccessor(self.store).get(path, default)

    def exists(self, path: KeyPath) -> bool:
        """경로 존재 여부 확인.
        
        Args:
            path: 확인할 경로
            
        Returns:
            경로 존재 여부
        """
        return KeyPathAccessor(self.store).exists(path)

    def set(self, path: KeyPath, value: Any) -> KeyPathState:
        """값 설정.
        
        Args:
            path: 설정할 경로
            value: 설정할 값
            
        Returns:
            Self for chaining
        """
        KeyPathAccessor(self.store).set(path, value)
        return self

    def delete(self, path: KeyPath, *, ignore_missing: bool = True) -> KeyPathState:
        """값 삭제.
        
        Args:
            path: 삭제할 경로
            ignore_missing: 존재하지 않는 경로 무시 여부
            
        Returns:
            Self for chaining
        """
        KeyPathAccessor(self.store).delete(path, ignore_missing=ignore_missing)
        return self

    def ensure(self, path: KeyPath, default_factory: Callable[[], Any] = dict) -> Any:
        """경로 확보 (존재하지 않으면 생성).
        
        Args:
            path: 확보할 경로
            default_factory: 경로가 없을 때 생성할 값의 팩토리 함수
            
        Returns:
            경로의 값
        """
        return KeyPathAccessor(self.store).ensure(path, default_factory)

    def override(self, path: KeyPath, value: Any) -> KeyPathState:
        """값 override (정책 기반).
        
        정책의 should_override 메서드에 판단을 위임하여 SRP 준수.
        
        Args:
            path: 설정할 경로
            value: 설정할 값
            
        Returns:
            Self for chaining
            
        Examples:
            >>> state = KeyPathState()
            >>> state.override("key", None)  # allow_override=True이므로 설정됨
            >>> state.get("key")
            None
            
            >>> policy = KeyPathStatePolicy(allow_override=False)
            >>> state = KeyPathState(policy=policy)
            >>> state.override("key", None)  # 무시됨
            >>> state.exists("key")
            False
        """
        # ✅ 정책 판단 위임
        if self.policy.should_override(value):
            self.set(path, value)
        return self

    def merge(self, patch: Dict[str, Any], *, path: Optional[KeyPath] = None, deep: Optional[bool] = None) -> KeyPathState:
        """Dict merge (정책 기반).
        
        정책의 get_merge_mode 메서드에 merge mode 결정을 위임하여 SRP 준수.
        명시적 deep 파라미터가 정책 기본값보다 우선순위가 높음.
        
        Args:
            patch: 병합할 dict
            path: 병합 대상 경로 (None이면 root에 병합)
            deep: 명시적 merge mode (None이면 정책 기본값 사용)
            
        Returns:
            Self for chaining
            
        Examples:
            >>> state = KeyPathState()
            >>> state.merge({"a": {"b": 1}})  # deep_merge=True (기본값)
            
            >>> policy = KeyPathStatePolicy(deep_merge=False)
            >>> state = KeyPathState(policy=policy)
            >>> state.merge({"a": 1})  # shallow merge
            >>> state.merge({"b": 2}, deep=True)  # 명시적 deep이 우선
        """
        # ✅ 정책에 merge mode 결정 위임
        merge_deep = self.policy.get_merge_mode(deep)
        if path:
            target = self.ensure(path, dict)
            DictOps.deep_update(target, patch, inplace=True)
        else:
            if merge_deep:
                DictOps.deep_update(self.store, patch, inplace=True)
            else:
                self.store.update(patch)
        return self

    def to_dict(self, *, copy: bool = True) -> Dict[str, Any]:
        """상태를 dict로 변환.
        
        Args:
            copy: 복사본 반환 여부 (False면 참조 반환)
            
        Returns:
            상태 dict
        """
        return dict(self.store) if copy else self.store
