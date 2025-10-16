# 🎯 cfg_utils 단기 문제점 개선 방향 (Short-term Improvement Plan)

**작성일**: 2025-10-16  
**목표 기간**: 1주 (즉시 실행)  
**우선순위**: High Priority  
**영향 범위**: cfg_utils 모듈 전체

---

## 📋 1. 개선 대상 문제점

### 1.1 현재 문제점 요약

| 번호 | 문제점 | 심각도 | 영향 범위 |
|------|--------|--------|----------|
| **P1** | policy_overrides가 암묵적 (Dict[str, Any]) | 🔴 High | 모든 사용자 |
| **P2** | None 케이스 처리 복잡 (if 분기 중첩) | 🟠 Medium | None 입력 시 |
| **P3** | 로딩 결과가 dict/model만 반환 (메타데이터 없음) | 🟡 Low | 디버깅 시 |
| **P4** | 테스트 코드 부재 | 🔴 High | 유지보수성 |

### 1.2 개선 우선순위 결정 기준

```
우선순위 = (사용 빈도 × 복잡도) + 영향 범위

P1: policy_overrides → (HIGH × HIGH) + 전체 = 최우선
P4: 테스트 코드 → (LOW × LOW) + 전체 = 고우선 (안정성)
P2: None 케이스 → (LOW × HIGH) + 부분 = 중우선
P3: 메타데이터 → (LOW × LOW) + 디버깅 = 저우선
```

---

## 🔧 2. P1: policy_overrides 명시적 파라미터화

### 2.1 문제점 상세

#### **현재 코드** (Before):
```python
# ❌ 문제: Dict[str, Any]라 타입 안전성 없음
config = ConfigLoader.load(
    "config.yaml",
    model=MyPolicy,
    policy_overrides={
        "drop_blanks": False,      # ← 오타 가능
        "resolve_reference": True,  # ← IDE 자동완성 안 됨
        "merge_mode": "deep"        # ← 잘못된 값 입력 가능
    }
)

# ❌ 더 큰 문제: 중첩된 필드
config = ConfigLoader.load(
    "config.yaml",
    policy_overrides={
        "yaml.source_paths": ["config.yaml"],  # ← 문자열 기반, 취약
        "keypath.sep": "__"
    }
)
```

**문제점**:
1. 🔴 **타입 안전성 부재**: Dict이므로 잘못된 키/값 입력 가능
2. 🔴 **IDE 지원 부족**: 자동완성, 타입 힌트 없음
3. 🔴 **런타임 에러**: 오타 시 Pydantic ValidationError만 발생
4. 🔴 **중첩 필드 복잡**: "yaml.source_paths" 문자열 파싱 필요

### 2.2 개선 방안 (Solution)

#### **Option 1: 직접 파라미터화 (권장)**

```python
# ✅ 개선안: 명시적 파라미터
@staticmethod
def load(
    cfg_like: Union[BaseModel, PathLike, PathsLike, dict, None],
    *,
    model: Optional[Type[T]] = None,
    # ConfigPolicy 필드를 직접 파라미터로
    drop_blanks: Optional[bool] = None,
    resolve_reference: Optional[bool] = None,
    merge_mode: Optional[Literal["deep", "shallow"]] = None,
    yaml_source_paths: Optional[List[PathLike]] = None,
    keypath_sep: Optional[str] = None,
    **overrides: Any
) -> Union[dict, T]:
    """설정을 로드하여 dict 또는 Pydantic 모델로 반환.
    
    Args:
        cfg_like: 설정 소스
        model: Pydantic 모델 클래스
        drop_blanks: 공백 값 제거 여부 (기본: True)
        resolve_reference: Reference 해석 여부 (기본: True)
        merge_mode: 병합 모드 (기본: "deep")
        yaml_source_paths: YAML source_paths 오버라이드
        keypath_sep: KeyPath 구분자 오버라이드 (기본: "__")
        **overrides: 최종 데이터 오버라이드
    
    Examples:
        # ✅ 타입 안전
        config = ConfigLoader.load(
            "config.yaml",
            model=MyPolicy,
            drop_blanks=False,        # ← IDE 자동완성
            merge_mode="shallow"      # ← Literal로 타입 체크
        )
        
        # ✅ 명시적 파라미터
        config = ConfigLoader.load(
            None,
            model=MyPolicy,
            yaml_source_paths=["base.yaml", "prod.yaml"]
        )
    """
    # ConfigPolicy 생성 (None이 아닌 값만 적용)
    policy_kwargs = {}
    if drop_blanks is not None:
        policy_kwargs["drop_blanks"] = drop_blanks
    if resolve_reference is not None:
        policy_kwargs["resolve_reference"] = resolve_reference
    if merge_mode is not None:
        policy_kwargs["merge_mode"] = merge_mode
    
    # 중첩 필드 처리
    if yaml_source_paths is not None or keypath_sep is not None:
        yaml_policy = BaseParserPolicy()
        if yaml_source_paths is not None:
            yaml_policy.source_paths = yaml_source_paths
        policy_kwargs["yaml"] = yaml_policy
        
        if keypath_sep is not None:
            policy_kwargs["keypath"] = KeyPathNormalizePolicy(sep=keypath_sep)
    
    # 기존 로직 (policy_kwargs 사용)
    temp_policy = ConfigPolicy(**policy_kwargs) if policy_kwargs else ConfigPolicy()
    # ...
```

**장점**:
- ✅ **타입 안전**: Literal, Optional로 타입 강제
- ✅ **IDE 지원**: 자동완성, 타입 힌트, docstring 표시
- ✅ **가독성**: 파라미터 이름이 명확
- ✅ **검증**: mypy/pylance가 컴파일 타임에 체크

**단점**:
- ⚠️ **파라미터 증가**: ConfigPolicy 필드만큼 파라미터 늘어남
- ⚠️ **유지보수**: ConfigPolicy 변경 시 load() 시그니처도 변경

#### **Option 2: ConfigPolicy 직접 전달 (대안)**

```python
@staticmethod
def load(
    cfg_like: Union[BaseModel, PathLike, PathsLike, dict, None],
    *,
    model: Optional[Type[T]] = None,
    policy: Optional[ConfigPolicy] = None,  # ← ConfigPolicy 객체
    **overrides: Any
) -> Union[dict, T]:
    """
    Examples:
        # 커스텀 Policy
        policy = ConfigPolicy(
            drop_blanks=False,
            merge_mode="shallow"
        )
        config = ConfigLoader.load("config.yaml", policy=policy)
        
        # 기본값 유지하면서 일부만 변경
        policy = ConfigPolicy(
            **ConfigPolicy().model_dump(),
            drop_blanks=False
        )
    """
    temp_policy = policy if policy else ConfigPolicy()
    # ...
```

**장점**:
- ✅ **단순성**: 파라미터 1개 추가
- ✅ **유연성**: ConfigPolicy 모든 필드 변경 가능
- ✅ **타입 안전**: Pydantic 검증

**단점**:
- ⚠️ **복잡성**: 사용자가 ConfigPolicy 생성 필요
- ⚠️ **기본값 누락 위험**: 전체 교체 시 기본값 날아감

### 2.3 최종 권장 방안

**✅ Option 1 + Option 2 하이브리드**:

```python
@staticmethod
def load(
    cfg_like: Union[BaseModel, PathLike, PathsLike, dict, None],
    *,
    model: Optional[Type[T]] = None,
    # Option 2: 전체 Policy 교체
    policy: Optional[ConfigPolicy] = None,
    # Option 1: 개별 필드 오버라이드 (자주 사용하는 것만)
    drop_blanks: Optional[bool] = None,
    resolve_reference: Optional[bool] = None,
    merge_mode: Optional[Literal["deep", "shallow"]] = None,
    **overrides: Any
) -> Union[dict, T]:
    """
    우선순위:
    1. policy 파라미터 (전체 교체)
    2. 개별 파라미터 (drop_blanks 등)
    3. ConfigPolicy 기본값
    
    Examples:
        # ✅ 간단한 케이스: 개별 파라미터
        config = ConfigLoader.load("config.yaml", drop_blanks=False)
        
        # ✅ 복잡한 케이스: Policy 객체
        policy = ConfigPolicy(yaml=BaseParserPolicy(enable_env=True))
        config = ConfigLoader.load("config.yaml", policy=policy)
        
        # ✅ 하이브리드: Policy + 개별
        policy = ConfigPolicy(yaml=custom_yaml_policy)
        config = ConfigLoader.load("config.yaml", policy=policy, drop_blanks=False)
    """
    # 1. policy가 있으면 사용
    if policy is not None:
        temp_policy = policy
    else:
        temp_policy = ConfigPolicy()
    
    # 2. 개별 파라미터로 오버라이드 (policy보다 우선)
    if drop_blanks is not None:
        temp_policy = temp_policy.model_copy(update={"drop_blanks": drop_blanks})
    if resolve_reference is not None:
        temp_policy = temp_policy.model_copy(update={"resolve_reference": resolve_reference})
    if merge_mode is not None:
        temp_policy = temp_policy.model_copy(update={"merge_mode": merge_mode})
    
    # 기존 로직
    # ...
```

### 2.4 구현 계획

#### **Step 1: 기존 policy_overrides 제거 (Breaking Change)**

```python
# Before
def load(..., policy_overrides: Optional[Dict[str, Any]] = None, ...):

# After (Deprecated)
def load(
    ...,
    policy_overrides: Optional[Dict[str, Any]] = None,  # ← Deprecated
    *,
    policy: Optional[ConfigPolicy] = None,
    drop_blanks: Optional[bool] = None,
    ...
):
    if policy_overrides:
        warnings.warn(
            "policy_overrides is deprecated. Use 'policy' or individual parameters instead.",
            DeprecationWarning,
            stacklevel=2
        )
        # 하위 호환성 유지 (임시)
        policy = ConfigPolicy(**policy_overrides)
```

#### **Step 2: 테스트 코드 작성**

```python
def test_load_with_policy_parameter():
    """policy 파라미터 테스트"""
    policy = ConfigPolicy(drop_blanks=False)
    config = ConfigLoader.load({"a": None}, policy=policy)
    assert config == {"a": None}  # drop_blanks=False이므로 유지

def test_load_with_individual_parameters():
    """개별 파라미터 테스트"""
    config = ConfigLoader.load({"a": None}, drop_blanks=False)
    assert config == {"a": None}

def test_load_parameter_priority():
    """파라미터 우선순위 테스트"""
    policy = ConfigPolicy(drop_blanks=True)
    # 개별 파라미터가 policy보다 우선
    config = ConfigLoader.load({"a": None}, policy=policy, drop_blanks=False)
    assert config == {"a": None}
```

#### **Step 3: 마이그레이션 가이드 작성**

```markdown
# Migration Guide: policy_overrides → policy/parameters

## Before
```python
config = ConfigLoader.load(
    "config.yaml",
    policy_overrides={"drop_blanks": False}
)
```

## After (Option 1: policy)
```python
policy = ConfigPolicy(drop_blanks=False)
config = ConfigLoader.load("config.yaml", policy=policy)
```

## After (Option 2: parameters)
```python
config = ConfigLoader.load("config.yaml", drop_blanks=False)
```
```

---

## 🔧 3. P2: None 케이스 명시적 처리

### 3.1 문제점 상세

#### **현재 코드** (Before):
```python
@staticmethod
def load(cfg_like, *, model, policy_overrides, **overrides):
    # ...
    
    # ❌ 복잡한 None 처리
    if cfg_like is None:
        if policy_overrides and (
            "yaml.source_paths" in policy_overrides or 
            "config_loader_path" in policy_overrides
        ):
            loader = ConfigLoader({}, policy_overrides=policy_overrides)
            if model:
                return loader._as_model_internal(model, **overrides)
            return loader._as_dict_internal(**overrides)
        cfg_like = {}
    
    # 빈 dict로 변환 후 계속 진행...
```

**문제점**:
1. 🔴 **복잡한 분기**: None → policy_overrides 체크 → {} 변환
2. 🔴 **의도 불명확**: None이 무엇을 의미하는지 모호
3. 🔴 **에러 처리 부족**: None + policy_overrides 없으면 빈 dict 반환

### 3.2 개선 방안 (Solution)

#### **Option 1: 전용 메서드 추가 (권장)**

```python
class ConfigLoader:
    @staticmethod
    def load_from_source_paths(
        source_paths: List[PathLike],
        *,
        model: Optional[Type[T]] = None,
        **overrides: Any
    ) -> Union[dict, T]:
        """source_paths에서 직접 로드 (cfg_like=None 케이스 대체).
        
        Args:
            source_paths: 로드할 YAML 파일 경로 리스트
            model: Pydantic 모델 클래스
            **overrides: 최종 데이터 오버라이드
        
        Returns:
            model이 있으면 Pydantic 모델, 없으면 dict
        
        Examples:
            # ✅ 명시적
            config = ConfigLoader.load_from_source_paths(
                ["base.yaml", "prod.yaml"],
                model=MyPolicy
            )
        """
        # source_paths를 yaml.source_paths에 설정
        policy = ConfigPolicy()
        policy.yaml.source_paths = source_paths
        
        # ConfigLoader 인스턴스 생성
        loader = ConfigLoader({}, policy=policy)
        
        if model:
            return loader._as_model_internal(model, **overrides)
        return loader._as_dict_internal(**overrides)
    
    @staticmethod
    def load_from_policy(
        policy: ConfigPolicy,
        *,
        model: Optional[Type[T]] = None,
        **overrides: Any
    ) -> Union[dict, T]:
        """Policy 객체에서 직접 로드.
        
        Args:
            policy: ConfigPolicy 인스턴스
            model: Pydantic 모델 클래스
            **overrides: 최종 데이터 오버라이드
        
        Examples:
            # ✅ 명시적
            policy = ConfigPolicy(
                yaml=BaseParserPolicy(source_paths=["config.yaml"])
            )
            config = ConfigLoader.load_from_policy(policy, model=MyPolicy)
        """
        loader = ConfigLoader({}, policy=policy)
        
        if model:
            return loader._as_model_internal(model, **overrides)
        return loader._as_dict_internal(**overrides)
```

#### **Option 2: load()에서 None 금지 (Breaking Change)**

```python
@staticmethod
def load(
    cfg_like: Union[BaseModel, PathLike, PathsLike, dict],  # ← None 제거
    *,
    model: Optional[Type[T]] = None,
    **overrides: Any
) -> Union[dict, T]:
    """
    Args:
        cfg_like: 설정 소스 (None 불가, 빈 dict 사용)
    
    Raises:
        TypeError: cfg_like가 None인 경우
    
    Examples:
        # ❌ 에러
        config = ConfigLoader.load(None)  # TypeError
        
        # ✅ 빈 dict 사용
        config = ConfigLoader.load({})
        
        # ✅ 또는 전용 메서드 사용
        config = ConfigLoader.load_from_source_paths([...])
    """
    if cfg_like is None:
        raise TypeError(
            "cfg_like cannot be None. "
            "Use ConfigLoader.load_from_source_paths() or load_from_policy() instead."
        )
    # ...
```

### 3.3 최종 권장 방안

**✅ Option 1 (전용 메서드) + Option 2 (None 금지) 조합**:

```python
class ConfigLoader:
    @staticmethod
    def load(
        cfg_like: Union[BaseModel, PathLike, PathsLike, dict],  # None 제거
        *,
        model: Optional[Type[T]] = None,
        policy: Optional[ConfigPolicy] = None,
        **overrides: Any
    ) -> Union[dict, T]:
        """메인 로딩 메서드 (None 불가)."""
        if cfg_like is None:
            raise TypeError(
                "cfg_like cannot be None. Use load_from_source_paths() or load_from_policy()."
            )
        # ...
    
    @staticmethod
    def load_from_source_paths(...):
        """source_paths 전용 메서드."""
        # ...
    
    @staticmethod
    def load_from_policy(...):
        """Policy 전용 메서드."""
        # ...
```

### 3.4 마이그레이션 가이드

```markdown
# Migration Guide: None 케이스

## Before
```python
config = ConfigLoader.load(
    None,
    policy_overrides={"yaml.source_paths": ["config.yaml"]}
)
```

## After (Option 1)
```python
config = ConfigLoader.load_from_source_paths(
    ["config.yaml"],
    model=MyPolicy
)
```

## After (Option 2)
```python
policy = ConfigPolicy(
    yaml=BaseParserPolicy(source_paths=["config.yaml"])
)
config = ConfigLoader.load_from_policy(policy, model=MyPolicy)
```
```

---

## 🔧 4. P3: 로딩 결과 메타데이터 추가

### 4.1 문제점 상세

**현재 코드** (Before):
```python
# ❌ dict 또는 model만 반환 (메타데이터 없음)
config = ConfigLoader.load("config.yaml", model=MyPolicy)
# config는 MyPolicy 인스턴스
# → 어떤 파일에서 로드했는지 알 수 없음
# → 병합 순서가 어땠는지 알 수 없음
```

**문제점**:
1. 🟡 **디버깅 어려움**: 어떤 파일에서 로드했는지 모름
2. 🟡 **추적 불가**: 병합 과정을 알 수 없음
3. 🟡 **검증 어려움**: 최종 Policy가 무엇인지 모름

### 4.2 개선 방안 (Solution)

```python
from dataclasses import dataclass
from typing import List, Union
from pathlib import Path

@dataclass
class ConfigLoadResult:
    """설정 로딩 결과 (메타데이터 포함).
    
    Attributes:
        config: 로드된 설정 (dict 또는 Pydantic 모델)
        policy: 사용된 ConfigPolicy
        loaded_files: 로드한 파일 경로 리스트
        merge_info: 병합 통계
    """
    config: Union[dict, BaseModel]
    policy: ConfigPolicy
    loaded_files: List[Path]
    merge_info: dict
    
    def __repr__(self) -> str:
        return (
            f"ConfigLoadResult(\n"
            f"  loaded_files={[str(f) for f in self.loaded_files]},\n"
            f"  merge_info={self.merge_info}\n"
            f")"
        )


class ConfigLoader:
    @staticmethod
    def load_with_metadata(
        cfg_like: Union[BaseModel, PathLike, PathsLike, dict],
        *,
        model: Optional[Type[T]] = None,
        **overrides: Any
    ) -> ConfigLoadResult:
        """메타데이터를 포함한 로딩.
        
        Returns:
            ConfigLoadResult 인스턴스
        
        Examples:
            result = ConfigLoader.load_with_metadata("config.yaml", model=MyPolicy)
            print(f"Loaded from: {result.loaded_files}")
            print(f"Policy: drop_blanks={result.policy.drop_blanks}")
            config = result.config
        """
        # 기존 load() 호출
        config = ConfigLoader.load(cfg_like, model=model, **overrides)
        
        # 메타데이터 수집 (내부 구현 필요)
        loaded_files = _collect_loaded_files(cfg_like)
        merge_info = {
            "file_count": len(loaded_files),
            "merge_mode": "deep",  # policy에서 가져옴
            "overrides_applied": len(overrides)
        }
        
        return ConfigLoadResult(
            config=config,
            policy=ConfigPolicy(),  # 실제 사용된 policy
            loaded_files=loaded_files,
            merge_info=merge_info
        )
```

### 4.3 사용 예시

```python
# ✅ 디버깅 시 유용
result = ConfigLoader.load_with_metadata(
    ["base.yaml", "prod.yaml"],
    model=MyPolicy,
    image__max_width=1024
)

print(f"Loaded files: {result.loaded_files}")
# → [Path("base.yaml"), Path("prod.yaml")]

print(f"Merge info: {result.merge_info}")
# → {"file_count": 2, "merge_mode": "deep", "overrides_applied": 1}

print(f"Policy: drop_blanks={result.policy.drop_blanks}")
# → drop_blanks=True

config = result.config  # MyPolicy 인스턴스
```

---

## 🧪 5. P4: 테스트 코드 작성

### 5.1 테스트 커버리지 목표

```
현재: 0% (테스트 없음)
목표: 80% 이상

우선순위:
1. ConfigLoader.load() - 모든 입력 타입
2. Merger (Strategy Pattern) - 각 Merger별
3. ConfigNormalizer - Reference/Blank 처리
4. helpers - apply_overrides, load_source 등
```

### 5.2 테스트 코드 구조

```
tests/
└── cfg_utils/
    ├── __init__.py
    ├── test_config_loader.py      # ConfigLoader 테스트
    ├── test_merger.py              # Merger 테스트
    ├── test_normalizer.py          # ConfigNormalizer 테스트
    ├── test_helpers.py             # helpers 테스트
    └── test_policy.py              # ConfigPolicy 테스트
```

### 5.3 핵심 테스트 케이스

#### **test_config_loader.py**

```python
import pytest
from pathlib import Path
from pydantic import BaseModel
from cfg_utils import ConfigLoader, ConfigPolicy

class TestPolicy(BaseModel):
    name: str
    value: int

class TestConfigLoader:
    """ConfigLoader 통합 테스트"""
    
    def test_load_from_dict(self):
        """dict 입력 테스트"""
        data = {"name": "test", "value": 42}
        config = ConfigLoader.load(data, model=TestPolicy)
        assert config.name == "test"
        assert config.value == 42
    
    def test_load_from_path(self, tmp_path):
        """Path 입력 테스트"""
        # 임시 YAML 파일 생성
        config_file = tmp_path / "config.yaml"
        config_file.write_text("name: test\nvalue: 42")
        
        config = ConfigLoader.load(config_file, model=TestPolicy)
        assert config.name == "test"
        assert config.value == 42
    
    def test_load_with_overrides(self):
        """overrides 테스트"""
        data = {"name": "test", "value": 42}
        config = ConfigLoader.load(
            data,
            model=TestPolicy,
            value=100  # override
        )
        assert config.value == 100
    
    def test_load_with_policy_parameter(self):
        """policy 파라미터 테스트"""
        data = {"name": "test", "value": None}
        policy = ConfigPolicy(drop_blanks=False)
        config = ConfigLoader.load(data, policy=policy)
        assert config == {"name": "test", "value": None}
    
    def test_load_with_drop_blanks_parameter(self):
        """drop_blanks 파라미터 테스트"""
        data = {"name": "test", "value": None}
        config = ConfigLoader.load(data, drop_blanks=False)
        assert config == {"name": "test", "value": None}
    
    def test_load_multiple_files(self, tmp_path):
        """여러 파일 병합 테스트"""
        base = tmp_path / "base.yaml"
        base.write_text("name: base\nvalue: 1")
        
        prod = tmp_path / "prod.yaml"
        prod.write_text("value: 2\nextra: prod")
        
        config = ConfigLoader.load([base, prod])
        assert config["name"] == "base"  # base에서
        assert config["value"] == 2       # prod가 덮어씀
        assert config["extra"] == "prod"  # prod에만 있음
    
    def test_load_none_raises_error(self):
        """None 입력 시 에러 테스트"""
        with pytest.raises(TypeError, match="cfg_like cannot be None"):
            ConfigLoader.load(None)
    
    def test_load_from_source_paths(self, tmp_path):
        """load_from_source_paths 테스트"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("name: test\nvalue: 42")
        
        config = ConfigLoader.load_from_source_paths(
            [config_file],
            model=TestPolicy
        )
        assert config.name == "test"
```

#### **test_merger.py**

```python
import pytest
from pydantic import BaseModel
from cfg_utils.services.merger import (
    DictMerger, ModelMerger, PathMerger, SequenceMerger, MergerFactory
)
from keypath_utils import KeyPathDict

class TestMerger:
    """Merger Strategy Pattern 테스트"""
    
    def test_dict_merger(self, mock_loader):
        """DictMerger 테스트"""
        merger = DictMerger(mock_loader)
        data = KeyPathDict({})
        source = {"a": 1, "b": 2}
        
        merger.merge(source, data, deep=True)
        assert data.data == {"a": 1, "b": 2}
    
    def test_model_merger(self, mock_loader):
        """ModelMerger 테스트"""
        class TestModel(BaseModel):
            a: int
            b: str
        
        merger = ModelMerger(mock_loader)
        data = KeyPathDict({})
        source = TestModel(a=1, b="test")
        
        merger.merge(source, data, deep=True)
        assert data.data == {"a": 1, "b": "test"}
    
    def test_merger_factory(self, mock_loader):
        """MergerFactory 테스트"""
        # dict → DictMerger
        merger = MergerFactory.get({"a": 1}, mock_loader)
        assert isinstance(merger, DictMerger)
        
        # BaseModel → ModelMerger
        class TestModel(BaseModel):
            a: int
        merger = MergerFactory.get(TestModel(a=1), mock_loader)
        assert isinstance(merger, ModelMerger)
```

#### **test_normalizer.py**

```python
import pytest
from cfg_utils import ConfigNormalizer, ConfigPolicy

class TestConfigNormalizer:
    """ConfigNormalizer 테스트"""
    
    def test_drop_blanks_enabled(self):
        """drop_blanks=True 테스트"""
        policy = ConfigPolicy(drop_blanks=True)
        normalizer = ConfigNormalizer(policy)
        
        data = {"a": None, "b": "", "c": [], "d": {}, "e": 1}
        result = normalizer.apply(data)
        assert result == {"e": 1}
    
    def test_drop_blanks_disabled(self):
        """drop_blanks=False 테스트"""
        policy = ConfigPolicy(drop_blanks=False)
        normalizer = ConfigNormalizer(policy)
        
        data = {"a": None, "b": "", "c": [], "d": {}, "e": 1}
        result = normalizer.apply(data)
        assert result == data
    
    def test_resolve_reference_enabled(self):
        """resolve_reference=True 테스트"""
        policy = ConfigPolicy(resolve_reference=True)
        normalizer = ConfigNormalizer(policy)
        
        data = {"base": "/path", "full": "${ref:base}/file.txt"}
        result = normalizer.apply(data)
        assert result["full"] == "/path/file.txt"
    
    def test_resolve_reference_disabled(self):
        """resolve_reference=False 테스트"""
        policy = ConfigPolicy(resolve_reference=False)
        normalizer = ConfigNormalizer(policy)
        
        data = {"base": "/path", "full": "${ref:base}/file.txt"}
        result = normalizer.apply(data)
        assert result["full"] == "${ref:base}/file.txt"
```

### 5.4 테스트 실행 계획

```bash
# 1. pytest 설치
pip install pytest pytest-cov

# 2. 테스트 실행
pytest tests/cfg_utils/ -v

# 3. 커버리지 측정
pytest tests/cfg_utils/ --cov=modules.cfg_utils --cov-report=html

# 4. 커버리지 확인
# htmlcov/index.html 열기
```

---

## 📅 6. 구현 일정

### Week 1 (Day 1-3): P1 개선

- [ ] **Day 1**: policy_overrides → policy/parameters 리팩토링
  - [ ] load() 시그니처 변경
  - [ ] 기존 policy_overrides Deprecated 처리
  - [ ] Docstring 업데이트

- [ ] **Day 2**: 테스트 코드 작성 (P1)
  - [ ] test_load_with_policy_parameter
  - [ ] test_load_with_individual_parameters
  - [ ] test_parameter_priority

- [ ] **Day 3**: 마이그레이션 가이드 작성
  - [ ] MIGRATION.md 작성
  - [ ] 예시 코드 추가

### Week 1 (Day 4-5): P2 개선

- [ ] **Day 4**: None 케이스 처리
  - [ ] load_from_source_paths() 추가
  - [ ] load_from_policy() 추가
  - [ ] load()에서 None 금지 (TypeError)

- [ ] **Day 5**: 테스트 코드 작성 (P2)
  - [ ] test_load_none_raises_error
  - [ ] test_load_from_source_paths
  - [ ] test_load_from_policy

### Week 1 (Day 6-7): P4 개선

- [ ] **Day 6**: 핵심 테스트 작성
  - [ ] test_config_loader.py (10개 테스트)
  - [ ] test_merger.py (5개 테스트)
  - [ ] test_normalizer.py (4개 테스트)

- [ ] **Day 7**: 커버리지 측정 및 보완
  - [ ] pytest-cov 실행
  - [ ] 80% 미만 영역 보완
  - [ ] CI/CD에 테스트 추가

### Week 2 (Optional): P3 개선

- [ ] **Day 8**: ConfigLoadResult 구현
- [ ] **Day 9**: load_with_metadata() 추가
- [ ] **Day 10**: 테스트 및 문서화

---

## 📊 7. 성공 지표 (Success Metrics)

### 7.1 정량적 지표

| 지표 | 현재 | 목표 | 측정 방법 |
|------|------|------|----------|
| **타입 안전성** | 0% | 100% | mypy --strict 통과 |
| **테스트 커버리지** | 0% | 80% | pytest-cov |
| **Breaking Change** | - | 0 | 하위 호환성 유지 |
| **API 명확성** | 낮음 | 높음 | IDE 자동완성 지원 |

### 7.2 정성적 지표

- ✅ **사용자 경험**: 파라미터 이름만 봐도 의미 이해 가능
- ✅ **에러 메시지**: 명확한 에러 메시지 (TypeError, ValueError)
- ✅ **문서화**: Docstring, 예시 코드 충분
- ✅ **유지보수성**: 테스트 코드로 리팩토링 안전

---

## 🎯 8. 요약

### 8.1 개선 전후 비교

#### **Before (현재)**:
```python
# ❌ 타입 안전성 없음
config = ConfigLoader.load(
    "config.yaml",
    policy_overrides={"drop_blanks": False}  # Dict[str, Any]
)

# ❌ None 케이스 복잡
config = ConfigLoader.load(
    None,
    policy_overrides={"yaml.source_paths": ["config.yaml"]}
)

# ❌ 메타데이터 없음
config = ConfigLoader.load("config.yaml")
# 어떤 파일에서 로드했는지 모름
```

#### **After (개선 후)**:
```python
# ✅ 타입 안전
config = ConfigLoader.load(
    "config.yaml",
    model=MyPolicy,
    drop_blanks=False  # ← IDE 자동완성, 타입 체크
)

# ✅ 명시적 메서드
config = ConfigLoader.load_from_source_paths(
    ["config.yaml"],
    model=MyPolicy
)

# ✅ 메타데이터
result = ConfigLoader.load_with_metadata("config.yaml")
print(f"Loaded from: {result.loaded_files}")
```

### 8.2 핵심 변경 사항

1. **policy_overrides 제거** → policy/개별 파라미터로 대체
2. **None 케이스 제거** → 전용 메서드로 분리
3. **메타데이터 추가** → ConfigLoadResult 도입
4. **테스트 추가** → 80% 커버리지 목표

---

**작성자**: GitHub Copilot  
**상태**: 준비 완료 (Ready to Implement)  
**다음 단계**: 구현 시작 (Day 1 부터)
