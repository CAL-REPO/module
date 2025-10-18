# 🔑 keypath_utils

경로(path) 기반으로 중첩된 딕셔너리를 안전하게 조작할 수 있도록 설계된 유틸리티 모듈입니다.

**최신 업데이트 (2025-10-17)**: Policy 강화 및 정책 위임 패턴 적용으로 SRP 준수 및 확장성 향상

---

## 📦 구성 요소

| 구성 요소 | 설명 | 역할 |
|-----------|------|------|
| `KeyPath` | 문자열 또는 문자열 리스트 경로 표현 (`"a.b.c"`, `["a", "b", "c"]`) | 타입 정의 |
| `KeyPathAccessor` | dict에 대해 경로 기반 `get/set/delete/exists/ensure` 기능 제공 | Low-level 접근 |
| `KeyPathDict` | 내부 dict 데이터를 보유한 구조적 컨테이너 + 병합/리키 기능 포함 | 데이터 컨테이너 |
| `KeyPathState` | 설정 및 상태 관리용 클래스 (`name`, `policy`, 데이터 포함) | **상태 관리** |
| `KeyPathStatePolicy` | Pydantic 기반 정책 모델 + **정책 판단 메서드** | **정책 관리** |

---

## 🧱 주요 클래스 설명

### ✅ `KeyPathAccessor`
**역할**: dict-like 객체에 대해 안전한 경로 접근 기능 제공

**핵심 메서드**:
- `get(path, default)`: 경로로 값 조회
- `set(path, value)`: 경로에 값 설정 (중간 dict 자동 생성)
- `exists(path)`: 경로 존재 여부 확인
- `delete(path, ignore_missing)`: 경로 삭제
- `ensure(path, default_factory)`: 경로가 없으면 기본값으로 생성

### ✅ `KeyPathDict`
**역할**: 구조화된 딕셔너리 컨테이너

**핵심 메서드**:
- `override(path, value)`: 경로에 값 override
- `merge(patch, deep)`: dict 병합 (deep/shallow)
- `apply_overrides(overrides)`: 여러 override 일괄 적용
- `rekey(mapping_or_func, deep)`: 키 이름 변경

### ✅ `KeyPathState`
**역할**: 계층적 상태/설정 모델 (정책 기반)

**정책 위임 메서드** (Phase 2에서 리팩토링):
- `override(path, value)`: **정책 기반 override** (`policy.should_override()` 위임)
- `merge(patch, path, deep)`: **정책 기반 merge** (`policy.get_merge_mode()` 위임)
- `get(path, default)`: **정책 기반 조회** (`policy.validate_path_access()` 위임)

**일반 메서드**:
- `set(path, value)`: 경로에 값 설정
- `delete(path)`: 경로 삭제
- `exists(path)`: 경로 존재 여부
- `ensure(path, default_factory)`: 경로 보장
- `to_dict(copy)`: dict로 변환

### ✅ `KeyPathStatePolicy` (Phase 1에서 강화)
**역할**: 정책 관리 + 판단 로직 중앙화

**정책 필드**:
| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `allow_override` | bool | True | None 값 override 허용 여부 |
| `deep_merge` | bool | True | merge 시 deep update 기본값 |
| `strict_path` | bool | False | 존재하지 않는 path 접근 시 KeyError 발생 |
| `auto_create_containers` | bool | True | set/override 시 중간 dict 자동 생성 |

**정책 판단 메서드** (Phase 1에서 추가):
- `should_override(value) -> bool`: Override 수행 여부 판단
- `get_merge_mode(explicit_deep) -> bool`: Merge mode 결정
- `validate_path_access(path, exists)`: Path 접근 유효성 검증
- `should_create_containers() -> bool`: 컨테이너 자동 생성 여부

---

## 🔁 사용 예시

### 기본 사용법 (Default Policy)
```python
from keypath_utils import KeyPathState

# 초기 상태 정의
state = KeyPathState(name="example")

# 경로 기반 값 설정
state.set("user.info.name", "Alice")
state.set("user.info.age", 30)

# Override (None 값도 허용 - allow_override=True)
state.override("user.info.email", None)
assert state.get("user.info.email") is None

# 값 조회
assert state.get("user.info.name") == "Alice"
assert state.get("nonexistent", "default") == "default"

# 병합 (deep merge - deep_merge=True)
state.merge({"user": {"info": {"email": "alice@example.com"}}})
assert state.get("user.info.name") == "Alice"  # 기존 값 유지
assert state.get("user.info.email") == "alice@example.com"  # 업데이트

# 출력
print(state.to_dict())
# {'user': {'info': {'name': 'Alice', 'age': 30, 'email': 'alice@example.com'}}}
```

### 정책 커스터마이징
```python
from keypath_utils import KeyPathState, KeyPathStatePolicy

# 엄격한 정책 정의
strict_policy = KeyPathStatePolicy(
    allow_override=False,  # None 값 거부
    deep_merge=True,       # Deep merge
    strict_path=True       # 존재하지 않는 경로 접근 시 KeyError
)
state = KeyPathState(name="config", policy=strict_policy)

# None 값 override 시도 → 무시됨
state.override("debug", None)
assert not state.exists("debug")

# None 아닌 값은 설정됨
state.override("debug", True)
assert state.get("debug") is True

# 존재하지 않는 경로 접근 → KeyError
try:
    state.get("nonexistent")
except KeyError as e:
    print(f"Error: {e}")  # KeyError: "Path not found: 'nonexistent'"
```

### 정책별 동작 비교
```python
from keypath_utils import KeyPathStatePolicy, KeyPathState

# 1. Lenient Policy (관대한 정책)
lenient = KeyPathStatePolicy(
    allow_override=True,   # None 허용
    strict_path=False      # 경로 검증 느슨
)
state1 = KeyPathState(policy=lenient)
state1.override("key", None)  # ✅ 설정됨
state1.get("nonexistent")     # ✅ None 반환 (에러 없음)

# 2. Strict Policy (엄격한 정책)
strict = KeyPathStatePolicy(
    allow_override=False,  # None 거부
    strict_path=True       # 경로 검증 엄격
)
state2 = KeyPathState(policy=strict)
state2.override("key", None)  # ❌ 무시됨
# state2.get("nonexistent")   # ❌ KeyError 발생

# 3. 동적 정책 변경
state = KeyPathState()
state.override("key1", None)  # ✅ 설정됨 (allow_override=True)

state.policy.allow_override = False
state.override("key2", None)  # ❌ 무시됨 (정책 변경됨)
```

### Merge Mode 제어
```python
from keypath_utils import KeyPathState, KeyPathStatePolicy

# Deep Merge (기본값)
state = KeyPathState()
state.set("app.db.host", "localhost")
state.set("app.db.port", 5432)

state.merge({"app": {"db": {"host": "127.0.0.1", "user": "admin"}}})
# Deep merge → 기존 값 유지
assert state.get("app.db.port") == 5432  # ✅ 유지됨
assert state.get("app.db.user") == "admin"  # ✅ 추가됨

# Shallow Merge (정책 변경)
policy = KeyPathStatePolicy(deep_merge=False)
state2 = KeyPathState(policy=policy)
state2.set("app.db.host", "localhost")
state2.set("app.db.port", 5432)

state2.merge({"app": {"db": {"host": "127.0.0.1", "user": "admin"}}})
# Shallow merge → 기존 값 손실
assert not state2.exists("app.db.port")  # ❌ 손실됨
assert state2.get("app.db.user") == "admin"  # ✅ 추가됨

# 명시적 deep 파라미터 (정책보다 우선)
state2.merge({"app": {"cache": {"ttl": 300}}}, deep=True)
# 명시적 deep=True가 정책 기본값(False)보다 우선
```

---

## 🎯 정책 활용 패턴

### 1. 디버깅 모드 (strict_path=True)
```python
# 오타 즉시 감지
policy = KeyPathStatePolicy(strict_path=True)
state = KeyPathState(policy=policy)

state.set("app.name", "MyApp")

# ❌ 오타 → KeyError (즉시 발견)
try:
    value = state.get("app.nmae")  # 오타!
except KeyError:
    print("오타 감지!")

# ✅ 올바른 경로
value = state.get("app.name")  # "MyApp"
```

### 2. 프로덕션 모드 (allow_override=False, strict_path=False)
```python
# None 값 거부, 경로 검증 느슨
policy = KeyPathStatePolicy(
    allow_override=False,
    strict_path=False
)
state = KeyPathState(policy=policy)

# None 값은 무시됨 (데이터 무결성 보장)
state.override("config.timeout", None)  # 무시됨
assert not state.exists("config.timeout")

# 존재하지 않는 경로는 default 반환 (graceful degradation)
timeout = state.get("config.timeout", 30)  # 30
```

### 3. 개발 모드 (모두 허용)
```python
# 모든 값 허용, 에러 없음
policy = KeyPathStatePolicy(
    allow_override=True,
    strict_path=False,
    deep_merge=True
)
state = KeyPathState(policy=policy)

# 빠른 프로토타이핑
state.override("temp.data", None)  # ✅
state.get("any.path")  # ✅ None 반환
state.merge({"a": {"b": 1}})  # ✅ Deep merge
```

---

## 🧩 의존 모듈
- `pydantic` (정책 모델링)
- `data_utils.core.types` (KeyPath 타입)
- `data_utils.services.dict_ops` (DictOps - 딕셔너리 병합 및 키 리매핑)
- `unify_utils.normalizers.keypath` (KeyPathNormalizer - 경로 해석)

---

## 📁 파일 구조
```
keypath_utils/
 ┣ __init__.py       # Public API
 ┣ policy.py         # 정책 클래스 + 판단 메서드 (Pydantic)
 ┣ model.py          # 데이터 클래스 (KeyPathDict, KeyPathState)
 ┣ accessor.py       # Low-level 경로 조작 유틸
 ┗ ___README___.md   # 모듈 문서 (이 파일)
```

---

## 🔄 변경 이력

### v2.0 (2025-10-17) - Policy 강화 & 정책 위임 패턴
**Phase 1: Policy 강화**
- ✅ `KeyPathStatePolicy`에 정책 판단 메서드 4개 추가
  - `should_override(value) -> bool`
  - `get_merge_mode(explicit_deep) -> bool`
  - `validate_path_access(path, exists)`
  - `should_create_containers() -> bool`
- ✅ 새로운 정책 필드 2개 추가
  - `strict_path` (기본값: False)
  - `auto_create_containers` (기본값: True)
- ✅ 25개 정책 단위 테스트 작성
- ✅ 100% 커버리지 달성 (policy.py)

**Phase 2: Model 리팩토링**
- ✅ `KeyPathState` 3개 메서드에 정책 위임 패턴 적용
  - `override()` → `policy.should_override()` 위임
  - `merge()` → `policy.get_merge_mode()` 위임
  - `get()` → `policy.validate_path_access()` 위임
- ✅ 23개 통합 테스트 작성
- ✅ 전체 125개 테스트 통과 (cfg_utils 77 + keypath_utils 48)
- ✅ 하위 호환성 100% 유지

**개선 효과**:
- ✅ SRP 준수: 정책 판단은 policy.py, 상태 관리는 model.py
- ✅ 확장성: 새 정책 추가 시 policy.py만 수정
- ✅ 테스트 가능성: 정책 로직 독립 테스트
- ✅ 가독성: 명확한 메서드 이름으로 의도 표현

---

## 🧭 개발 방향
- ✅ Mixin 제거 → 구성 기반 설계로 전환
- ✅ 정책 로직 중앙화 → SRP 준수
- ✅ 정책 위임 패턴 → 확장성 및 테스트 가능성 향상
- 🔧 추가 정책 고려 (Future)
  - `track_history`: 변경 이력 추적
  - `max_depth`: 최대 중첩 깊이 제한
  - `validate_types`: 타입 검증

---

## 🔐 라이선스 및 관리
- 사내 내부 유틸리티로 사용
- 외부 배포 금지 / 프로젝트 통합 관리 기준 준수
