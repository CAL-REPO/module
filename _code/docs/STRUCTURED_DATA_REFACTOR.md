# 🔄 data_utils → structured_data 리팩토링 개선 방향

> **작성일**: 2025-10-14  
> **목적**: db_ops와 df_ops를 structured_data로 mixin 형태 모듈화 개선 방향 분석

---

## 📊 현재 상태 분석

### 기존 구조 (data_utils)

```
data_utils/
├── __init__.py              # 통합 export
├── ops.py                   # DictOps (dict 병합)
├── string_ops.py            # StringOps (문자열 조작)
├── list_ops.py              # ListOps (리스트 조작)
├── geometry_ops.py          # GeometryOps (bbox 연산)
├── types.py                 # 타입 정의
└── (외부 참조)
    ├── df → structured_data/df
    └── db_ops → structured_data/db
```

### 새로운 구조 (structured_data)

```
structured_data/
├── base/                    # 공통 기반 클래스
├── df/                      # DataFrame 처리
│   ├── __init__.py
│   ├── base.py             # DFPolicy, BaseDFMixin
│   ├── df_ops.py           # DataFrameOps (통합 인터페이스)
│   ├── mixin_clean.py      # DataFrameCleanMixin
│   ├── mixin_create.py     # DataFrameCreateMixin
│   ├── mixin_filter.py     # DataFrameFilterMixin
│   ├── mixin_normalize.py  # DataFrameNormalizeMixin
│   ├── mixin_update.py     # DataFrameUpdateMixin
│   └── policy.py           # DataFrame 관련 정책
└── db/                      # Database 처리
    ├── __init__.py         # (empty)
    ├── base.py             # (empty)
    ├── ops.py              # SQLiteKVStore, KVKeyMixin
    └── policy.py           # (존재 가능)
```

---

## 🎯 Mixin 기반 설계 분석

### ✅ DataFrame Mixin 구조 (잘 설계됨)

**1. Base Mixin**:
```python
# structured_data/df/base.py
class BaseDFMixin:
    """모든 DataFrame Mixin의 기반 클래스"""
    def __init__(self, policy: Optional[DFPolicy] = None):
        self.policy = policy or DFPolicy()
```

**2. 기능별 Mixin 분리**:
```python
# mixin_clean.py - 정제 기능
class DataFrameCleanMixin(BaseDFMixin):
    def drop_empty(self, df, axis=0):
        return df.dropna(axis=axis, how="all")

# mixin_normalize.py - 정규화 기능
class DataFrameNormalizeMixin(BaseDFMixin):
    def normalize_columns(self, df, aliases):
        # 컬럼명 정규화

# mixin_filter.py - 필터링 기능
class DataFrameFilterMixin(BaseDFMixin):
    def filter_rows(self, df, condition):
        # 조건부 필터링

# mixin_create.py - 생성 기능
class DataFrameCreateMixin(BaseDFMixin):
    def from_dict(self, data):
        # dict → DataFrame 변환

# mixin_update.py - 업데이트 기능
class DataFrameUpdateMixin(BaseDFMixin):
    def update_column(self, df, col, func):
        # 컬럼 업데이트
```

**3. 통합 Interface**:
```python
# df_ops.py
class DataFrameOps(
    DataFrameCleanMixin,
    DataFrameNormalizeMixin,
    DataFrameFilterMixin,
    DataFrameCreateMixin,
    DataFrameUpdateMixin
):
    """모든 DataFrame 기능을 통합한 단일 인터페이스"""
    
    def __init__(self, policy: Optional[DFPolicy] = None):
        super().__init__(policy)
```

---

## 🔍 Database Mixin 개선 방향

### 현재 상태 (db/ops.py)

```python
class KVKeyMixin:
    """키 생성 Mixin (현재 독립적)"""
    @staticmethod
    def make_key(*parts: str) -> str:
        return hashlib.sha256(...).hexdigest()

class SQLiteKVStore(KVKeyMixin):
    """SQLite KV 저장소 (Mixin 상속)"""
    def __init__(self, path, table="cache", ddl=None):
        # ...
```

### 🎯 개선 제안: Mixin 분리 및 조합

```python
# structured_data/db/base.py
from typing import Protocol, Optional
from pathlib import Path

class DBPolicy:
    """Database 작업 정책"""
    table_name: str = "cache"
    auto_commit: bool = True
    create_if_missing: bool = True
    enforce_schema: bool = True

class BaseDBMixin:
    """모든 DB Mixin의 기반 클래스"""
    def __init__(self, policy: Optional[DBPolicy] = None):
        self.policy = policy or DBPolicy()
```

```python
# structured_data/db/mixin_connection.py
import sqlite3
from .base import BaseDBMixin

class DBConnectionMixin(BaseDBMixin):
    """연결 관리 Mixin"""
    
    def __init__(self, path: Path, policy=None):
        super().__init__(policy)
        self.path = Path(path)
        self._con: Optional[sqlite3.Connection] = None
    
    def open(self):
        """DB 연결 열기"""
        self._con = sqlite3.connect(str(self.path))
        return self
    
    def close(self):
        """DB 연결 닫기"""
        if self._con:
            self._con.close()
            self._con = None
    
    def __enter__(self):
        return self.open()
    
    def __exit__(self, *args):
        self.close()
    
    @property
    def con(self):
        if not self._con:
            raise RuntimeError("Database not open")
        return self._con
```

```python
# structured_data/db/mixin_schema.py
from .base import BaseDBMixin

class DBSchemaMixin(BaseDBMixin):
    """스키마 관리 Mixin"""
    
    def __init__(self, policy=None):
        super().__init__(policy)
        self._ddl: Optional[str] = None
    
    def set_ddl(self, ddl: str):
        """DDL 설정"""
        self._ddl = ddl
        return self
    
    def ensure_table(self, con, table_name: str):
        """테이블 생성 확인"""
        if self._ddl:
            con.execute(self._ddl)
        else:
            # 기본 스키마
            con.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
```

```python
# structured_data/db/mixin_kv.py
from typing import Optional
from .base import BaseDBMixin

class KVOperationsMixin(BaseDBMixin):
    """Key-Value 작업 Mixin"""
    
    def get(self, con, table: str, key: str) -> Optional[str]:
        """값 조회"""
        cur = con.execute(f"SELECT value FROM {table} WHERE key=?", (key,))
        row = cur.fetchone()
        return row[0] if row else None
    
    def put(self, con, table: str, key: str, value: str):
        """값 저장"""
        con.execute(
            f"INSERT OR REPLACE INTO {table}(key, value) VALUES(?,?)",
            (key, value)
        )
        if self.policy.auto_commit:
            con.commit()
    
    def delete(self, con, table: str, key: str):
        """값 삭제"""
        con.execute(f"DELETE FROM {table} WHERE key=?", (key,))
        if self.policy.auto_commit:
            con.commit()
    
    def exists(self, con, table: str, key: str) -> bool:
        """키 존재 여부"""
        cur = con.execute(f"SELECT 1 FROM {table} WHERE key=? LIMIT 1", (key,))
        return cur.fetchone() is not None
```

```python
# structured_data/db/mixin_key.py
import hashlib
from .base import BaseDBMixin

class KeyGenerationMixin(BaseDBMixin):
    """키 생성 Mixin"""
    
    @staticmethod
    def make_key(*parts: str) -> str:
        """SHA256 기반 안정적 키 생성"""
        h = hashlib.sha256()
        for p in parts:
            h.update((p or "").encode("utf-8", errors="ignore"))
            h.update(b"\0")
        return h.hexdigest()
    
    @staticmethod
    def make_simple_key(*parts: str) -> str:
        """간단한 문자열 연결 키"""
        return ":".join(str(p) for p in parts if p)
```

```python
# structured_data/db/mixin_cache.py
from typing import Optional
from .base import BaseDBMixin

class CacheMixin(BaseDBMixin):
    """캐시 전용 Mixin (번역 캐시 등)"""
    
    def get_cached(self, con, table: str, key: str, 
                   fields: list[str]) -> Optional[dict]:
        """캐시 조회 (다중 필드)"""
        fields_str = ", ".join(fields)
        cur = con.execute(
            f"SELECT {fields_str} FROM {table} WHERE key=?", 
            (key,)
        )
        row = cur.fetchone()
        if row:
            return dict(zip(fields, row))
        return None
    
    def put_cached(self, con, table: str, key: str, data: dict):
        """캐시 저장 (다중 필드)"""
        fields = ", ".join(data.keys())
        placeholders = ", ".join("?" * len(data))
        con.execute(
            f"INSERT OR REPLACE INTO {table}(key, {fields}) VALUES(?, {placeholders})",
            (key, *data.values())
        )
        if self.policy.auto_commit:
            con.commit()
```

```python
# structured_data/db/ops.py - 통합 인터페이스
from pathlib import Path
from typing import Optional

from .base import DBPolicy
from .mixin_connection import DBConnectionMixin
from .mixin_schema import DBSchemaMixin
from .mixin_kv import KVOperationsMixin
from .mixin_key import KeyGenerationMixin
from .mixin_cache import CacheMixin


class SQLiteKVStore(
    DBConnectionMixin,
    DBSchemaMixin,
    KVOperationsMixin,
    KeyGenerationMixin,
    CacheMixin
):
    """SQLite 기반 Key-Value 저장소 (Mixin 조합)"""
    
    def __init__(
        self, 
        path: Path | str, 
        *, 
        table: str = "cache",
        ddl: Optional[str] = None,
        policy: Optional[DBPolicy] = None
    ):
        # 모든 Mixin 초기화
        super().__init__(path, policy)
        self.table = table
        if ddl:
            self.set_ddl(ddl)
    
    def open(self):
        """연결 열기 + 스키마 생성"""
        super().open()
        self.ensure_table(self.con, self.table)
        return self
    
    # 편의 메서드 (con과 table을 자동 전달)
    def get(self, key: str) -> Optional[str]:
        return super().get(self.con, self.table, key)
    
    def put(self, key: str, value: str):
        return super().put(self.con, self.table, key, value)
    
    def delete(self, key: str):
        return super().delete(self.con, self.table, key)
    
    def exists(self, key: str) -> bool:
        return super().exists(self.con, self.table, key)


# 번역 캐시 전용 클래스 (특화된 스키마)
class TranslationCache(SQLiteKVStore):
    """번역 캐시 전용 저장소"""
    
    def __init__(self, path: Path | str, policy: Optional[DBPolicy] = None):
        ddl = """
        CREATE TABLE IF NOT EXISTS cache (
            key TEXT PRIMARY KEY,
            src TEXT NOT NULL,
            tgt TEXT NOT NULL,
            target_lang TEXT NOT NULL,
            model TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        super().__init__(path, table="cache", ddl=ddl, policy=policy)
    
    def get_translation(self, src: str, target_lang: str, model: str) -> Optional[str]:
        """번역 조회"""
        key = self.make_key(src, target_lang, model)
        result = self.get_cached(
            self.con, self.table, key, 
            ["tgt"]
        )
        return result["tgt"] if result else None
    
    def put_translation(self, src: str, tgt: str, target_lang: str, model: str):
        """번역 저장"""
        key = self.make_key(src, target_lang, model)
        self.put_cached(
            self.con, self.table, key,
            {"src": src, "tgt": tgt, "target_lang": target_lang, "model": model}
        )
```

---

## 📐 Mixin 설계 원칙

### 1️⃣ **단일 책임 원칙 (SRP)**
각 Mixin은 하나의 관심사만 처리:
- `DBConnectionMixin` → 연결 관리만
- `DBSchemaMixin` → 스키마 관리만
- `KVOperationsMixin` → CRUD 작업만
- `KeyGenerationMixin` → 키 생성만

### 2️⃣ **조합 가능성 (Composability)**
필요한 Mixin만 선택적으로 조합:
```python
# 기본 KV 저장소
class SimpleKVStore(DBConnectionMixin, KVOperationsMixin):
    pass

# 캐시 기능 추가
class CachedKVStore(DBConnectionMixin, CacheMixin):
    pass

# 전체 기능
class FullKVStore(
    DBConnectionMixin, 
    DBSchemaMixin, 
    KVOperationsMixin, 
    KeyGenerationMixin, 
    CacheMixin
):
    pass
```

### 3️⃣ **Policy 기반 동작**
모든 Mixin이 공통 Policy 객체 사용:
```python
policy = DBPolicy(
    auto_commit=False,  # 수동 커밋
    create_if_missing=True,
    enforce_schema=True
)
store = SQLiteKVStore("db.sqlite", policy=policy)
```

### 4️⃣ **명확한 인터페이스**
각 Mixin은 명확한 메서드 시그니처 제공:
```python
# Protocol로 인터페이스 정의 가능
from typing import Protocol

class KVProtocol(Protocol):
    def get(self, con, table: str, key: str) -> Optional[str]: ...
    def put(self, con, table: str, key: str, value: str): ...
```

---

## 🔄 마이그레이션 전략

### Phase 1: Mixin 분리 (1주)

**작업 순서**:
1. ✅ `structured_data/db/base.py` 작성
   - DBPolicy 정의
   - BaseDBMixin 정의

2. ✅ Mixin 파일 생성
   - mixin_connection.py
   - mixin_schema.py
   - mixin_kv.py
   - mixin_key.py
   - mixin_cache.py

3. ✅ ops.py 리팩토링
   - SQLiteKVStore를 Mixin 조합으로 재작성
   - 기존 API 유지 (하위 호환성)

### Phase 2: 테스트 작성 (1주)

```python
# tests/test_db_mixins.py
import pytest
from structured_data.db import SQLiteKVStore, TranslationCache

def test_kv_basic_operations(tmp_path):
    db_path = tmp_path / "test.db"
    
    with SQLiteKVStore(db_path) as store:
        # Put
        store.put("key1", "value1")
        
        # Get
        assert store.get("key1") == "value1"
        
        # Exists
        assert store.exists("key1") is True
        
        # Delete
        store.delete("key1")
        assert store.exists("key1") is False

def test_translation_cache(tmp_path):
    db_path = tmp_path / "translation.db"
    
    with TranslationCache(db_path) as cache:
        # Put translation
        cache.put_translation(
            src="Hello",
            tgt="안녕하세요",
            target_lang="ko",
            model="gpt-4"
        )
        
        # Get translation
        result = cache.get_translation("Hello", "ko", "gpt-4")
        assert result == "안녕하세요"
```

### Phase 3: data_utils 통합 (1주)

```python
# data_utils/__init__.py 업데이트
from structured_data.df import DFPolicy, DataFrameOps
from structured_data.db import SQLiteKVStore, TranslationCache

# 기존 export 유지 (하위 호환성)
from .ops import DictOps
from .string_ops import StringOps
from .list_ops import ListOps

__all__ = [
    # Structured data (NEW)
    "DFPolicy", "DataFrameOps",
    "SQLiteKVStore", "TranslationCache",
    
    # Legacy (기존 유지)
    "DictOps", "StringOps", "ListOps",
]
```

---

## 📊 Mixin 조합 예시

### 예시 1: 간단한 KV 저장소

```python
from structured_data.db import (
    DBConnectionMixin, 
    KVOperationsMixin
)

class SimpleKV(DBConnectionMixin, KVOperationsMixin):
    """최소 기능 KV 저장소"""
    
    def __init__(self, path):
        super().__init__(path)
    
    def get(self, key: str):
        return super().get(self.con, "kv", key)
    
    def put(self, key: str, value: str):
        return super().put(self.con, "kv", key, value)
```

### 예시 2: 세션 저장소

```python
from structured_data.db import (
    DBConnectionMixin,
    DBSchemaMixin,
    CacheMixin
)

class SessionStore(DBConnectionMixin, DBSchemaMixin, CacheMixin):
    """세션 데이터 저장소"""
    
    def __init__(self, path):
        super().__init__(path)
        self.set_ddl("""
            CREATE TABLE IF NOT EXISTS sessions (
                key TEXT PRIMARY KEY,
                user_id TEXT,
                data TEXT,
                expires_at TIMESTAMP
            )
        """)
    
    def save_session(self, session_id: str, user_id: str, data: str):
        self.put_cached(self.con, "sessions", session_id, {
            "user_id": user_id,
            "data": data
        })
```

### 예시 3: 메타데이터 저장소

```python
from structured_data.db import (
    DBConnectionMixin,
    DBSchemaMixin,
    KVOperationsMixin,
    KeyGenerationMixin
)

class MetadataStore(
    DBConnectionMixin, 
    DBSchemaMixin, 
    KVOperationsMixin,
    KeyGenerationMixin
):
    """파일 메타데이터 저장소"""
    
    def save_file_meta(self, filepath: str, metadata: dict):
        key = self.make_key("file", filepath)
        import json
        self.put(self.con, "metadata", key, json.dumps(metadata))
    
    def get_file_meta(self, filepath: str) -> dict:
        key = self.make_key("file", filepath)
        result = self.get(self.con, "metadata", key)
        import json
        return json.loads(result) if result else {}
```

---

## 🎯 최종 구조 (목표)

```
structured_data/
├── base/                        # 공통 기반
│   ├── __init__.py
│   ├── policy.py               # StructuredDataPolicy
│   └── interfaces.py           # Protocol 정의
│
├── df/                          # DataFrame (Mixin 기반)
│   ├── __init__.py
│   ├── base.py                 # DFPolicy, BaseDFMixin
│   ├── df_ops.py               # DataFrameOps (통합)
│   ├── mixin_clean.py
│   ├── mixin_create.py
│   ├── mixin_filter.py
│   ├── mixin_normalize.py
│   └── mixin_update.py
│
└── db/                          # Database (Mixin 기반)
    ├── __init__.py              # export SQLiteKVStore, TranslationCache
    ├── base.py                  # DBPolicy, BaseDBMixin
    ├── ops.py                   # SQLiteKVStore (통합)
    ├── mixin_connection.py      # 연결 관리
    ├── mixin_schema.py          # 스키마 관리
    ├── mixin_kv.py              # KV 작업
    ├── mixin_key.py             # 키 생성
    └── mixin_cache.py           # 캐시 작업
```

---

## ✅ 개선 효과

### 1️⃣ **유지보수성 향상**
- 각 Mixin이 독립적으로 테스트 가능
- 기능 추가/수정 시 해당 Mixin만 변경
- 명확한 책임 분리

### 2️⃣ **재사용성 증대**
- 필요한 기능만 조합하여 사용
- 다양한 저장소 타입 쉽게 생성
- 코드 중복 최소화

### 3️⃣ **확장성 개선**
- 새로운 Mixin 추가 용이
- 기존 코드 수정 없이 기능 확장
- 다형성을 통한 유연한 설계

### 4️⃣ **타입 안전성**
- Protocol을 통한 인터페이스 정의
- Pydantic Policy로 타입 검증
- IDE 자동완성 지원

---

## 📝 체크리스트

### DB Mixin 구현
- [ ] base.py - DBPolicy, BaseDBMixin
- [ ] mixin_connection.py - 연결 관리
- [ ] mixin_schema.py - 스키마 관리
- [ ] mixin_kv.py - KV 작업
- [ ] mixin_key.py - 키 생성
- [ ] mixin_cache.py - 캐시 작업
- [ ] ops.py - SQLiteKVStore 통합
- [ ] __init__.py - export 설정

### 테스트 작성
- [ ] test_db_connection.py
- [ ] test_db_kv_operations.py
- [ ] test_db_cache.py
- [ ] test_db_integration.py

### 문서화
- [ ] 각 Mixin API 문서
- [ ] 사용 예시 추가
- [ ] 마이그레이션 가이드

### 통합
- [ ] data_utils/__init__.py 업데이트
- [ ] 기존 코드 호환성 확인
- [ ] 성능 테스트

---

**작성자**: GitHub Copilot  
**다음 단계**: Mixin 구현 시작 여부 확인
