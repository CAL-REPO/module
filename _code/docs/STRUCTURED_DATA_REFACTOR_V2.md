# 🔄 Structured Data 구조 재설계 제안 (V2)

> **작성일**: 2025-10-14  
> **문제**: db/df 폴더 분리의 필요성 재검토  
> **핵심**: Mixin의 본질은 **역할 기반 조합**, 데이터 타입 분리가 아님

---

## 🎯 문제 인식

### 현재 구조의 모순점

```
structured_data/
├── base/                    # 공통 기반
├── df/                      # DataFrame 전용
│   ├── BaseDFMixin         # ← DataFrame만 사용
│   ├── mixin_clean.py
│   └── mixin_normalize.py
└── db/                      # Database 전용
    ├── BaseDBMixin         # ← Database만 사용
    ├── mixin_connection.py
    └── mixin_kv.py
```

**모순**:
- ✅ **Mixin의 목적**: 동일한 역할을 하는 기능을 재사용 가능한 조각으로 분리
- ❌ **현재 구조**: `BaseDFMixin`과 `BaseDBMixin`으로 분리 → **재사용 불가**
- ❌ **문제**: DB와 DF가 완전히 독립적 → Mixin을 cross-use 할 수 없음

### 실제 사용 시나리오

**시나리오 1: DataFrame을 DB에 저장**
```python
class DataFrameWithDB:
    # ❌ 현재: 두 Base를 상속할 수 없음
    # BaseDFMixin과 BaseDBMixin이 각자 policy를 가짐
    
    # ✅ 원하는 것: 
    # - DataFrameCleanMixin (DF 정제)
    # - DBConnectionMixin (DB 저장)
    # - 둘을 자유롭게 조합
```

**시나리오 2: DB 데이터를 DataFrame으로 변환**
```python
class DBToDataFrame:
    # ❌ 현재: DF Mixin과 DB Mixin을 함께 쓸 수 없음
    
    # ✅ 원하는 것:
    # - KVOperationsMixin (DB에서 읽기)
    # - DataFrameCreateMixin (DF 생성)
```

---

## 💡 새로운 설계 원칙

### Mixin은 **역할(Role)** 기반으로 분리

**잘못된 분리**: 데이터 타입 기반
```
df/  ← DataFrame용
db/  ← Database용
```

**올바른 분리**: 역할 기반
```
mixins/
├── io/              # 입출력 역할
│   ├── connection   # 연결 관리
│   ├── schema       # 스키마 관리
│   └── cache        # 캐싱
├── transform/       # 변환 역할
│   ├── clean        # 정제
│   ├── normalize    # 정규화
│   └── filter       # 필터링
└── create/          # 생성 역할
    ├── from_dict    # dict → 구조화
    └── from_kv      # kv → 구조화
```

---

## 🏗️ 제안: 역할 기반 재구조화

### 새로운 구조

```
structured_data/
├── base/
│   ├── policy.py               # BaseOperationsPolicy
│   └── mixin.py                # BaseOperationsMixin[PolicyT]
│
├── policies/                   # 각 도메인의 Policy만 분리
│   ├── df_policy.py           # DFPolicy
│   └── db_policy.py           # DBPolicy
│
├── mixins/                     # 역할 기반 Mixin
│   ├── io/                    # I/O 관련
│   │   ├── connection.py      # ConnectionMixin (DB 연결)
│   │   ├── schema.py          # SchemaMixin (스키마 관리)
│   │   └── cache.py           # CacheMixin (캐싱)
│   │
│   ├── transform/             # 변환 관련
│   │   ├── clean.py           # CleanMixin (정제)
│   │   ├── normalize.py       # NormalizeMixin (정규화)
│   │   └── filter.py          # FilterMixin (필터링)
│   │
│   ├── create/                # 생성 관련
│   │   ├── from_dict.py       # FromDictMixin
│   │   ├── from_kv.py         # FromKVMixin
│   │   └── from_df.py         # FromDataFrameMixin
│   │
│   └── ops/                   # 작업 관련
│       ├── kv_ops.py          # KVOperationsMixin
│       ├── key_gen.py         # KeyGenerationMixin
│       └── df_ops.py          # DataFrameOperationsMixin
│
└── composites/                # 조합된 클래스
    ├── dataframe.py           # DataFrameOps
    ├── database.py            # SQLiteKVStore
    └── hybrid.py              # 하이브리드 클래스
```

---

## 📝 구체적인 리팩토링 예시

### Before (현재 - 분리됨)

```python
# df/mixin_clean.py
from .base import BaseDFMixin  # ← DF만 사용

class DataFrameCleanMixin(BaseDFMixin):
    def drop_empty(self, df, axis=0):
        return df.dropna(axis=axis, how="all")


# db/mixin_kv.py
from .base import BaseDBMixin  # ← DB만 사용

class KVOperationsMixin(BaseDBMixin):
    def get(self, con, table, key):
        ...
```

**문제**: 두 Mixin을 함께 쓸 수 없음!

---

### After (제안 - 통합)

```python
# mixins/transform/clean.py
from structured_data.base import BaseOperationsMixin

class CleanMixin(BaseOperationsMixin):
    """데이터 정제 Mixin (DataFrame, dict, list 등에 사용 가능)"""
    
    def drop_empty_df(self, df, axis=0):
        """DataFrame에서 빈 행/열 제거"""
        return df.dropna(axis=axis, how="all")
    
    def drop_empty_dict(self, d):
        """dict에서 빈 값 제거"""
        return {k: v for k, v in d.items() if v}
    
    def drop_empty_list(self, lst):
        """list에서 빈 요소 제거"""
        return [x for x in lst if x]


# mixins/io/connection.py
from structured_data.base import BaseOperationsMixin

class ConnectionMixin(BaseOperationsMixin):
    """연결 관리 Mixin (DB, API 등에 사용 가능)"""
    
    def open(self):
        """리소스 연결"""
        raise NotImplementedError
    
    def close(self):
        """리소스 해제"""
        raise NotImplementedError
    
    def __enter__(self):
        return self.open()
    
    def __exit__(self, *args):
        self.close()


# mixins/ops/kv_ops.py
from structured_data.base import BaseOperationsMixin

class KVOperationsMixin(BaseOperationsMixin):
    """Key-Value 작업 Mixin (DB, cache, dict 등에 사용 가능)"""
    
    def get(self, key):
        raise NotImplementedError
    
    def put(self, key, value):
        raise NotImplementedError
    
    def delete(self, key):
        raise NotImplementedError
    
    def exists(self, key):
        raise NotImplementedError
```

---

### 조합 예시

```python
# composites/database.py
from structured_data.mixins.io.connection import ConnectionMixin
from structured_data.mixins.io.schema import SchemaMixin
from structured_data.mixins.ops.kv_ops import KVOperationsMixin
from structured_data.mixins.ops.key_gen import KeyGenerationMixin
from structured_data.policies.db_policy import DBPolicy

class SQLiteKVStore(
    ConnectionMixin,
    SchemaMixin,
    KVOperationsMixin,
    KeyGenerationMixin
):
    """SQLite KV 저장소 (Mixin 조합)"""
    
    def __init__(self, path, policy: DBPolicy = None):
        super().__init__(policy or DBPolicy())
        self.path = path
    
    # ConnectionMixin 구현
    def open(self):
        self._con = sqlite3.connect(self.path)
        return self
    
    # KVOperationsMixin 구현
    def get(self, key):
        return self._get_from_db(key)


# composites/dataframe.py
from structured_data.mixins.transform.clean import CleanMixin
from structured_data.mixins.transform.normalize import NormalizeMixin
from structured_data.mixins.create.from_dict import FromDictMixin
from structured_data.policies.df_policy import DFPolicy

class DataFrameOps(
    CleanMixin,
    NormalizeMixin,
    FromDictMixin
):
    """DataFrame 작업 (Mixin 조합)"""
    
    def __init__(self, policy: DFPolicy = None):
        super().__init__(policy or DFPolicy())


# composites/hybrid.py - ✅ 이제 가능!
from structured_data.mixins.transform.clean import CleanMixin
from structured_data.mixins.io.connection import ConnectionMixin
from structured_data.mixins.ops.kv_ops import KVOperationsMixin

class DataFrameWithCache(
    CleanMixin,           # ← DF 정제
    ConnectionMixin,      # ← DB 연결
    KVOperationsMixin     # ← KV 작업
):
    """DataFrame 처리 + DB 캐싱 하이브리드 클래스"""
    
    def process_and_cache(self, df, key):
        # CleanMixin 사용
        cleaned = self.drop_empty_df(df)
        
        # DB에 저장 (ConnectionMixin + KVOperationsMixin)
        import pickle
        self.put(key, pickle.dumps(cleaned))
        
        return cleaned
```

---

## 🎯 Policy는 어떻게?

### Policy도 역할 기반으로 분리

```python
# policies/io_policy.py
@dataclass
class IOPolicy(BaseOperationsPolicy):
    """I/O 작업 공통 정책"""
    connection_timeout: int = 5
    auto_commit: bool = True
    enable_wal: bool = True


# policies/transform_policy.py
@dataclass
class TransformPolicy(BaseOperationsPolicy):
    """변환 작업 공통 정책"""
    allow_empty: bool = False
    normalize: bool = True
    drop_empty: bool = True


# policies/composite_policy.py
@dataclass
class CompositePolicy:
    """조합된 Policy"""
    io: IOPolicy = field(default_factory=IOPolicy)
    transform: TransformPolicy = field(default_factory=TransformPolicy)


# 사용 예시
policy = CompositePolicy(
    io=IOPolicy(connection_timeout=10),
    transform=TransformPolicy(allow_empty=True)
)

ops = DataFrameWithCache(policy=policy)
```

---

## 📊 비교: 현재 vs 제안

### 현재 구조

```python
# ❌ DF와 DB를 함께 쓸 수 없음
class MyClass(BaseDFMixin, BaseDBMixin):
    # 두 Base가 충돌!
    # 각자 다른 policy를 가짐
    pass
```

**문제점**:
1. ❌ BaseDFMixin과 BaseDBMixin이 독립적
2. ❌ Mixin cross-use 불가
3. ❌ 하이브리드 작업 구현 어려움
4. ❌ 코드 중복 (clean, normalize가 DF/DB 각각 존재 가능)

---

### 제안 구조

```python
# ✅ 모든 Mixin을 자유롭게 조합
class MyClass(
    CleanMixin,        # 정제
    ConnectionMixin,   # 연결
    KVOperationsMixin  # KV 작업
):
    # 모든 Mixin이 BaseOperationsMixin 상속
    # 하나의 policy로 통합 제어
    pass
```

**장점**:
1. ✅ 모든 Mixin이 공통 Base 상속
2. ✅ 자유로운 조합 가능
3. ✅ 하이브리드 작업 쉬움
4. ✅ 역할 기반 분리로 명확한 구조

---

## 🔄 마이그레이션 계획

### Phase 1: Mixin 역할 분석 (1일)

현재 Mixin 목록:
```
DF:
- DataFrameCleanMixin      → CleanMixin (transform/)
- DataFrameNormalizeMixin  → NormalizeMixin (transform/)
- DataFrameFilterMixin     → FilterMixin (transform/)
- DataFrameCreateMixin     → FromDictMixin (create/)
- DataFrameUpdateMixin     → UpdateMixin (ops/)

DB:
- DBConnectionMixin        → ConnectionMixin (io/)
- DBSchemaMixin           → SchemaMixin (io/)
- KVOperationsMixin       → KVOperationsMixin (ops/)
- KeyGenerationMixin      → KeyGenerationMixin (ops/)
- CacheMixin              → CacheMixin (io/)
```

### Phase 2: mixins/ 폴더 생성 (2일)

역할별로 재배치:
```
mixins/
├── io/          # 5개 Mixin
├── transform/   # 3개 Mixin
├── create/      # 1개 Mixin
└── ops/         # 3개 Mixin
```

### Phase 3: Policy 통합 (1일)

```python
# CompositePolicy로 통합
@dataclass
class StructuredDataPolicy:
    io: IOPolicy = field(default_factory=IOPolicy)
    transform: TransformPolicy = field(default_factory=TransformPolicy)
    ops: OpsPolicy = field(default_factory=OpsPolicy)
```

### Phase 4: 기존 클래스 재작성 (2일)

```python
# composites/에서 재조합
class SQLiteKVStore(ConnectionMixin, SchemaMixin, ...):
    ...

class DataFrameOps(CleanMixin, NormalizeMixin, ...):
    ...
```

### Phase 5: 하이브리드 클래스 추가 (1일)

```python
# composites/hybrid.py
class DataFrameWithCache(...):
    ...

class DBToDataFrame(...):
    ...
```

---

## ✅ 결론

### 현재 구조의 문제

**db/와 df/ 폴더 분리는 Mixin 철학에 맞지 않음**:
- Mixin은 **역할(기능)**로 분리해야 함
- 데이터 타입으로 분리하면 재사용 불가
- 하이브리드 작업 구현 어려움

### 제안: 역할 기반 재구조화

```
structured_data/
├── base/        # 공통 기반
├── policies/    # 역할별 Policy
├── mixins/      # 역할별 Mixin
│   ├── io/
│   ├── transform/
│   ├── create/
│   └── ops/
└── composites/  # 조합된 클래스
    ├── database.py
    ├── dataframe.py
    └── hybrid.py
```

**장점**:
1. ✅ 모든 Mixin을 자유롭게 조합
2. ✅ 역할이 명확 (connection, clean, normalize...)
3. ✅ 하이브리드 작업 쉬움
4. ✅ 확장성 높음 (새 역할 추가 용이)

---

**다음 단계**:
1. 기존 구조 유지하면서 점진적 마이그레이션
2. 또는 즉시 재구조화 시작

어떻게 진행하시겠습니까?
