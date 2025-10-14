# 🔗 Structured Data 통합 설계: DB + DF Mixin 통합

> **작성일**: 2025-10-14  
> **목적**: DB Mixin과 DF Mixin을 공통 기반으로 통합하는 설계 제안

---

## 💡 핵심 아이디어: **공통 Mixin 기반 통합**

DB와 DataFrame은 서로 다른 데이터 구조를 다루지만, **Mixin 패턴의 설계 철학은 동일**합니다:

1. **정책 기반 동작** (Policy-driven behavior)
2. **단일 책임 분리** (Single Responsibility)
3. **조합 가능성** (Composability)
4. **공통 베이스 클래스** (Shared Base)

→ **통합 가능**: 공통 `BaseOperationsMixin`과 `OperationsPolicy`로 추상화

---

## 🏗️ 현재 구조 분석

### DF Mixin 구조
```python
# structured_data/df/base.py
@dataclass
class DFPolicy:
    allow_empty: bool = False
    normalize_columns: bool = True
    drop_empty_rows: bool = True
    # ...

class BaseDFMixin:
    def __init__(self, policy: Optional[DFPolicy] = None):
        self.policy = policy or DFPolicy()
```

### DB Mixin 구조 (현재)
```python
# structured_data/db/ops.py
class KVKeyMixin:
    @staticmethod
    def make_key(*parts: str) -> str:
        # SHA256 키 생성

class SQLiteKVStore(KVKeyMixin):
    def __init__(self, path, table="cache", ddl=None):
        # Policy 없음 (하드코딩)
```

**문제점**:
- ❌ DB는 Policy가 없음 (설정이 하드코딩)
- ❌ BaseMixin 없음 (일관된 초기화 패턴 부재)
- ❌ DF와 DB가 완전히 독립적 (공통 추상화 없음)

---

## 🎯 통합 설계 제안

### Phase 1: 공통 Base 계층 생성

```python
# structured_data/base/policy.py
"""공통 정책 기반 클래스"""
from typing import Protocol, TypeVar, Generic
from dataclasses import dataclass

# Generic Policy Protocol
class OperationsPolicy(Protocol):
    """모든 Policy가 따라야 할 프로토콜"""
    pass

PolicyT = TypeVar('PolicyT', bound=OperationsPolicy)


@dataclass
class BaseOperationsPolicy:
    """모든 작업의 공통 정책 기반 클래스"""
    verbose: bool = False
    strict_mode: bool = True
    auto_validate: bool = True


# structured_data/base/mixin.py
"""공통 Mixin 기반 클래스"""
from typing import Optional, Generic
from .policy import PolicyT


class BaseOperationsMixin(Generic[PolicyT]):
    """모든 Operations Mixin의 최상위 베이스 클래스
    
    모든 Mixin은 policy를 받아서 동작을 제어합니다.
    """
    
    def __init__(self, policy: Optional[PolicyT] = None):
        self.policy = policy or self._default_policy()
    
    def _default_policy(self) -> PolicyT:
        """서브클래스에서 오버라이드"""
        raise NotImplementedError("Subclass must provide default policy")
    
    def validate(self):
        """Policy 기반 검증"""
        if self.policy and hasattr(self.policy, 'auto_validate'):
            if self.policy.auto_validate:
                self._perform_validation()
    
    def _perform_validation(self):
        """서브클래스에서 구현"""
        pass
```

### Phase 2: DF Mixin을 공통 Base로 리팩토링

```python
# structured_data/df/base.py
from dataclasses import dataclass, field
from typing import Dict, Set, Optional
from ..base.policy import BaseOperationsPolicy
from ..base.mixin import BaseOperationsMixin


@dataclass
class DFPolicy(BaseOperationsPolicy):
    """DataFrame 작업 정책 (공통 정책 상속)"""
    allow_empty: bool = False
    normalize_columns: bool = True
    drop_empty_rows: bool = True
    drop_empty_cols: bool = True
    warn_on_duplicate_cols: bool = True
    default_aliases: Dict[str, Set[str]] = field(default_factory=dict)


class BaseDFMixin(BaseOperationsMixin[DFPolicy]):
    """DataFrame Mixin 기반 클래스 (공통 Base 상속)"""
    
    def _default_policy(self) -> DFPolicy:
        return DFPolicy()
    
    def _perform_validation(self):
        """DataFrame 관련 검증"""
        if hasattr(self, 'df') and self.df is not None:
            if not self.policy.allow_empty and self.df.empty:
                raise ValueError("Empty DataFrame not allowed by policy")
```

### Phase 3: DB Mixin을 공통 Base로 리팩토링

```python
# structured_data/db/base.py
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from ..base.policy import BaseOperationsPolicy
from ..base.mixin import BaseOperationsMixin


@dataclass
class DBPolicy(BaseOperationsPolicy):
    """Database 작업 정책 (공통 정책 상속)"""
    table_name: str = "cache"
    auto_commit: bool = True
    create_if_missing: bool = True
    enforce_schema: bool = True
    connection_timeout: int = 5
    enable_wal: bool = True  # Write-Ahead Logging
    foreign_keys: bool = True


class BaseDBMixin(BaseOperationsMixin[DBPolicy]):
    """Database Mixin 기반 클래스 (공통 Base 상속)"""
    
    def _default_policy(self) -> DBPolicy:
        return DBPolicy()
    
    def _perform_validation(self):
        """Database 관련 검증"""
        if hasattr(self, '_con') and self._con is None:
            if self.policy.strict_mode:
                raise RuntimeError("Database connection not established")
```

### Phase 4: 통합 Mixin 구조

```
structured_data/
├── base/                           # 🆕 공통 기반
│   ├── __init__.py
│   ├── policy.py                   # BaseOperationsPolicy, OperationsPolicy
│   └── mixin.py                    # BaseOperationsMixin[PolicyT]
│
├── df/                             # DataFrame (공통 Base 활용)
│   ├── base.py                     # DFPolicy(BaseOperationsPolicy)
│   │                               # BaseDFMixin(BaseOperationsMixin[DFPolicy])
│   ├── mixin_clean.py              # DataFrameCleanMixin(BaseDFMixin)
│   ├── mixin_normalize.py          # DataFrameNormalizeMixin(BaseDFMixin)
│   └── df_ops.py                   # DataFrameOps (통합)
│
└── db/                             # Database (공통 Base 활용)
    ├── base.py                     # DBPolicy(BaseOperationsPolicy)
    │                               # BaseDBMixin(BaseOperationsMixin[DBPolicy])
    ├── mixin_connection.py         # DBConnectionMixin(BaseDBMixin)
    ├── mixin_kv.py                 # KVOperationsMixin(BaseDBMixin)
    └── ops.py                      # SQLiteKVStore (통합)
```

---

## 🔄 통합 예시 코드

### 예시 1: DB Mixin 리팩토링

```python
# structured_data/db/mixin_connection.py
from pathlib import Path
import sqlite3
from typing import Optional
from .base import BaseDBMixin, DBPolicy


class DBConnectionMixin(BaseDBMixin):
    """연결 관리 Mixin (공통 Base 상속)"""
    
    def __init__(self, path: Path | str, policy: Optional[DBPolicy] = None):
        super().__init__(policy)  # 부모 초기화
        self.path = Path(path)
        self._con: Optional[sqlite3.Connection] = None
    
    def open(self):
        """DB 연결 열기 (Policy 기반)"""
        self.validate()  # 공통 검증
        
        self._con = sqlite3.connect(
            str(self.path),
            timeout=self.policy.connection_timeout
        )
        
        # Policy에 따라 설정
        if self.policy.enable_wal:
            self._con.execute("PRAGMA journal_mode=WAL")
        if self.policy.foreign_keys:
            self._con.execute("PRAGMA foreign_keys=ON")
        
        return self
    
    def close(self):
        """DB 연결 닫기"""
        if self._con:
            if self.policy.auto_commit:
                self._con.commit()
            self._con.close()
            self._con = None
    
    def __enter__(self):
        return self.open()
    
    def __exit__(self, *args):
        self.close()
    
    @property
    def con(self):
        if not self._con:
            if self.policy.strict_mode:
                raise RuntimeError("Database not open")
        return self._con
```

### 예시 2: 공통 Policy 활용

```python
# 사용 예시
from structured_data.df import DataFrameOps, DFPolicy
from structured_data.db import SQLiteKVStore, DBPolicy

# DataFrame 작업
df_policy = DFPolicy(
    verbose=True,          # 공통 속성
    strict_mode=True,      # 공통 속성
    allow_empty=False,     # DF 전용
    normalize_columns=True # DF 전용
)
df_ops = DataFrameOps(policy=df_policy)

# Database 작업
db_policy = DBPolicy(
    verbose=True,          # 공통 속성
    strict_mode=True,      # 공통 속성
    auto_commit=False,     # DB 전용
    enable_wal=True        # DB 전용
)
db_store = SQLiteKVStore("cache.db", policy=db_policy)
```

### 예시 3: 공통 Mixin 조합

```python
# structured_data/hybrid/df_with_cache.py
"""DataFrame과 DB를 조합한 하이브리드 작업"""
from structured_data.df import BaseDFMixin, DFPolicy
from structured_data.db import BaseDBMixin, DBPolicy


class CachedDataFrameMixin(BaseDFMixin, BaseDBMixin):
    """DataFrame 작업 결과를 DB에 캐싱하는 Mixin"""
    
    def __init__(self, df_policy=None, db_policy=None):
        # 두 Policy 모두 초기화
        BaseDFMixin.__init__(self, df_policy)
        BaseDBMixin.__init__(self, db_policy)
    
    def load_or_fetch(self, key: str, fetch_func):
        """캐시에서 로드하거나, 없으면 fetch 후 저장"""
        # DB에서 조회
        cached = self.get_cached_df(key)
        if cached is not None:
            return cached
        
        # 새로 fetch
        df = fetch_func()
        
        # 캐시 저장
        self.save_cached_df(key, df)
        return df
```

---

## 📊 통합의 장점

### 1️⃣ **일관된 API**
```python
# 모든 작업이 동일한 패턴 사용
df_ops = DataFrameOps(policy=DFPolicy(...))
db_ops = SQLiteKVStore(policy=DBPolicy(...))

# 둘 다 validate() 메서드 사용 가능
df_ops.validate()
db_ops.validate()
```

### 2️⃣ **Policy 재사용**
```python
# 공통 설정을 한 번만 정의
common_config = {
    "verbose": True,
    "strict_mode": False,
    "auto_validate": True
}

df_policy = DFPolicy(**common_config, allow_empty=True)
db_policy = DBPolicy(**common_config, auto_commit=False)
```

### 3️⃣ **타입 안전성**
```python
# Generic을 통한 타입 안전성
class BaseOperationsMixin(Generic[PolicyT]):
    def __init__(self, policy: Optional[PolicyT] = None):
        self.policy: PolicyT = policy or self._default_policy()

# IDE가 policy 타입 추론 가능
df_ops.policy.allow_empty  # ✅ IDE가 DFPolicy 인식
db_ops.policy.auto_commit  # ✅ IDE가 DBPolicy 인식
```

### 4️⃣ **확장성**
```python
# 새로운 데이터 타입 추가 시 동일 패턴 사용
# structured_data/json/base.py
@dataclass
class JSONPolicy(BaseOperationsPolicy):
    indent: int = 2
    ensure_ascii: bool = False

class BaseJSONMixin(BaseOperationsMixin[JSONPolicy]):
    def _default_policy(self) -> JSONPolicy:
        return JSONPolicy()
```

### 5️⃣ **하이브리드 작업**
```python
# DF + DB 조합
class DataFrameWithCache(BaseDFMixin, BaseDBMixin):
    """DataFrame 처리 + DB 캐싱"""
    
    def process_and_cache(self, df, key: str):
        # DF 처리 (BaseDFMixin 사용)
        cleaned = self.drop_empty(df)
        normalized = self.normalize_columns(cleaned)
        
        # DB 저장 (BaseDBMixin 사용)
        import pickle
        self.put(key, pickle.dumps(normalized))
        
        return normalized
```

---

## 🔧 마이그레이션 계획

### Step 1: 공통 Base 생성 (1일)

```powershell
# 파일 생성
New-Item -Path "modules\structured_data\base" -ItemType Directory
New-Item -Path "modules\structured_data\base\__init__.py"
New-Item -Path "modules\structured_data\base\policy.py"
New-Item -Path "modules\structured_data\base\mixin.py"
```

**파일 내용**:
- `policy.py`: `BaseOperationsPolicy`, `OperationsPolicy` Protocol
- `mixin.py`: `BaseOperationsMixin[PolicyT]`

### Step 2: DF 리팩토링 (1일)

```python
# structured_data/df/base.py 수정
- from dataclasses import dataclass
+ from ..base.policy import BaseOperationsPolicy
+ from ..base.mixin import BaseOperationsMixin

- class BaseDFMixin:
+ class BaseDFMixin(BaseOperationsMixin[DFPolicy]):
-     def __init__(self, policy: Optional[DFPolicy] = None):
-         self.policy = policy or DFPolicy()
+     def _default_policy(self) -> DFPolicy:
+         return DFPolicy()
```

**테스트**: 기존 DF 코드가 그대로 작동하는지 확인

### Step 3: DB 리팩토링 (2일)

1. `db/base.py` 생성
   - `DBPolicy(BaseOperationsPolicy)`
   - `BaseDBMixin(BaseOperationsMixin[DBPolicy])`

2. Mixin 분리
   - `mixin_connection.py` (BaseDBMixin 상속)
   - `mixin_kv.py` (BaseDBMixin 상속)
   - `mixin_key.py` (BaseDBMixin 상속)

3. `ops.py` 통합
   ```python
   class SQLiteKVStore(
       DBConnectionMixin,
       KVOperationsMixin,
       KeyGenerationMixin
   ):
       def __init__(self, path, policy=None):
           super().__init__(path, policy)
   ```

### Step 4: 통합 테스트 (1일)

```python
# tests/test_structured_data_integration.py
def test_common_policy_attributes():
    """공통 Policy 속성 테스트"""
    df_policy = DFPolicy(verbose=True, strict_mode=False)
    db_policy = DBPolicy(verbose=True, strict_mode=False)
    
    assert df_policy.verbose == db_policy.verbose
    assert df_policy.strict_mode == db_policy.strict_mode

def test_hybrid_operations():
    """DF + DB 하이브리드 작업 테스트"""
    ops = CachedDataFrameOps(
        df_policy=DFPolicy(),
        db_policy=DBPolicy()
    )
    
    df = ops.load_or_create("test_key", lambda: pd.DataFrame(...))
    assert not df.empty
```

### Step 5: 문서화 (1일)

- API 문서 업데이트
- 마이그레이션 가이드
- 사용 예시 추가

---

## 🎯 최종 구조 (통합 후)

```
structured_data/
├── base/                           # 🆕 공통 기반 (핵심!)
│   ├── __init__.py
│   ├── policy.py                   # BaseOperationsPolicy
│   └── mixin.py                    # BaseOperationsMixin[PolicyT]
│
├── df/                             # DataFrame (공통 Base 활용)
│   ├── base.py                     # DFPolicy(BaseOperationsPolicy)
│   │                               # BaseDFMixin(BaseOperationsMixin[DFPolicy])
│   ├── mixin_clean.py              # ← BaseDFMixin 상속
│   ├── mixin_normalize.py          # ← BaseDFMixin 상속
│   ├── mixin_filter.py             # ← BaseDFMixin 상속
│   ├── mixin_create.py             # ← BaseDFMixin 상속
│   ├── mixin_update.py             # ← BaseDFMixin 상속
│   └── df_ops.py                   # DataFrameOps (통합)
│
├── db/                             # Database (공통 Base 활용)
│   ├── base.py                     # DBPolicy(BaseOperationsPolicy)
│   │                               # BaseDBMixin(BaseOperationsMixin[DBPolicy])
│   ├── mixin_connection.py         # ← BaseDBMixin 상속
│   ├── mixin_schema.py             # ← BaseDBMixin 상속
│   ├── mixin_kv.py                 # ← BaseDBMixin 상속
│   ├── mixin_key.py                # ← BaseDBMixin 상속
│   ├── mixin_cache.py              # ← BaseDBMixin 상속
│   └── ops.py                      # SQLiteKVStore (통합)
│
└── hybrid/                         # 🆕 하이브리드 작업
    ├── __init__.py
    └── df_with_cache.py            # DataFrame + DB 조합
```

---

## ✅ 결론

### **통합 가능하고, 오히려 권장됨!**

**이유**:
1. ✅ **공통 패턴 강제** - 모든 작업이 Policy 기반 동작
2. ✅ **코드 중복 제거** - BaseOperationsMixin에 공통 로직 집중
3. ✅ **타입 안전성** - Generic을 통한 Policy 타입 보장
4. ✅ **확장성** - 새로운 데이터 타입 추가 시 동일 패턴 사용
5. ✅ **하이브리드 작업 가능** - DF + DB 조합 쉬움

**비용**:
- 초기 리팩토링 시간 (약 5일)
- 기존 코드 마이그레이션 필요

**결론**: **투자 가치 충분히 있음** 👍

---

**다음 단계**:
1. ✅ structured_data/base/ 생성
2. ✅ BaseOperationsPolicy, BaseOperationsMixin 구현
3. ✅ DF/DB 리팩토링
4. ✅ 통합 테스트

시작하시겠습니까?
