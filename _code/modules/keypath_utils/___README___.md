# 🔑 keypath_utils

경로(path) 기반으로 중첩된 딕셔너리를 안전하게 조작할 수 있도록 설계된 유틸리티 모듈입니다.

---

## 📦 구성 요소

| 구성 요소 | 설명 |
|-----------|------|
| `KeyPath` | 문자열 또는 문자열 리스트 경로 표현 (`"a.b.c"`, `["a", "b", "c"]`) |
| `split_keys()` | 경로를 리스트 형태로 분리하는 유틸 함수 |
| `KeyPathAccessor` | dict에 대해 경로 기반 `get/set/delete/exists/ensure` 기능 제공 |
| `KeyPathDict` | 내부 dict 데이터를 보유한 구조적 컨테이너 + 병합/리키 기능 포함 |
| `KeyPathState` | 설정 및 상태 관리용 클래스 (`name`, `policy`, 데이터 포함) |
| `KeyPathStatePolicy` | Pydantic 기반 정책 모델 (`allow_override`, `deep_merge` 등 설정) |

---

## 🧱 주요 클래스 설명

### ✅ `KeyPathAccessor`
- dict-like 객체에 대해 안전한 경로 접근 기능 제공
- 핵심 메서드: `get()`, `set()`, `exists()`, `delete()`, `ensure()`

### ✅ `KeyPathDict`
- 구조화된 딕셔너리 컨테이너
- `merge()` / `rekey()` / `override()` 기능 포함
- 내부 데이터는 `dict` 형식

### ✅ `KeyPathState`
- 계층적 상태/설정 모델
- 내부에 `KeyPathDict` 포함
- `policy`를 통해 동작 제어 가능 (`KeyPathStatePolicy`)

### ✅ `KeyPathStatePolicy`
- 설정 클래스 (Pydantic 기반)
- 경로 덮어쓰기, 병합 방식 등 정책 지정 가능

---

## 🔁 사용 예시

```python
from keypath_utils import KeyPathState

# 초기 상태 정의
state = KeyPathState(name="example")

# 경로 기반 값 설정
state.set("user.info.name", "Alice")
state.override("user.info.age", 30)

# 값 조회
assert state.get("user.info.name") == "Alice"

# 병합
state.merge({"user": {"info": {"email": "alice@example.com"}}})

# 출력
print(state.to_dict())
```

---

## 🧩 의존 모듈
- `pydantic` (정책 모델링)
- `data_utils.dict_ops.DictOps` (딕셔너리 병합 및 키 리매핑 기능)

---

## 📁 파일 구조 (권장)
```
keypath_utils/
 ┣ model.py          # 데이터 클래스 정의
 ┣ accessor.py       # 경로 조작 유틸
 ┣ types.py          # KeyPath 타입 및 유틸
 ┣ policy.py         # 정책 클래스 (Pydantic)
 ┗ __init__.py       # 진입점 모듈
```

---

## 🧭 개발 방향
- Mixin 제거 → 구성 기반 설계로 전환
- 모든 설정은 정책 → 구조 → 동작 순으로 정의
- 확장성과 가독성 중심 구조 유지

---

## 🔐 라이선스 및 관리
- 사내 내부 유틸리티로 사용
- 외부 배포 금지 / 프로젝트 통합 관리 기준 준수
