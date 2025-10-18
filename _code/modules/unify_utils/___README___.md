# 🧰 unify_utils

**데이터 정규화 · 구조 표준화 유틸리티 패키지**

입력 데이터의 문자열, 타입, 리스트, 구조 등을 일관성 있게 정제합니다.  
규칙 기반 치환, 재귀적 구조 처리, 단일값 변환, 리스트 분할, 참조 해석 등 다양한 방식의 정규화를 지원하며,  
Pydantic 기반 설정 정책을 통해 안전하고 유연한 구성이 가능합니다.

---

## 📦 구성 모듈

### 🔹 `core/`
- `interface.py`: Normalizer/Resolver 추상 기반(재귀 처리, strict 모드, compose 지원)
- `policy.py`: NormalizePolicy 및 ResolverPolicy (Pydantic 기반) 정의
- `__init__.py`: core 공개 API 정리

### 🔹 `normalizers/`
- `rule.py`: 정규식 · 룰 기반 문자열 정규화 (`RuleBasedNormalizer`)
- `value.py`: bool/int/date 등 단일 값 정규화 (`ValueNormalizer`)
- `list.py`: 문자열/시퀀스 정규화 (`ListNormalizer`)

### 🔹 `resolver/`
- `unified.py`: **정책 기반 통합 Resolver** (`UnifiedResolver`) ⭐ **권장**
  - 단순 참조: `${key:default}`
  - KeyPath 중첩: `${key__path:default}`
  - 환경 변수: `${ENV:default}`
  - Context 변수: `{{VAR}}`
- `reference.py`: 단순 참조 전용 (`ReferenceResolver`) - 레거시
- `placeholder.py`: 환경변수/Context 전용 (`PlaceholderResolver`) - 레거시
- `__init__.py`: Resolver 공개 API

### 🔹 `presets/`
- `rules.py`: `NormalizeRule`, `RuleType`, `LetterCase`, `RegexFlag`, `RulePresets`

---

## 🚀 사용 예시

### Normalizer

```python
from unify_utils import rule_normalizer, RulePresets

normalizer = rule_normalizer(rules=RulePresets.BASIC_CLEAN, recursive=True)
result = normalizer({"name": "  Alice  ", "city": "SEOUL"})
# {'name': 'alice', 'city': 'seoul'}
```

```python
from unify_utils import value_normalizer
vn = value_normalizer()
vn.normalize_bool("YES")       # True
vn.normalize_date("2025-10-10")  # '2025-10-10'
```

```python
from unify_utils import list_normalizer
ln = list_normalizer(sep=",", item_cast=int)
ln("1,2,3")  # [1, 2, 3]
```

### UnifiedResolver (권장) ⭐

```python
from unify_utils import unified_resolver

# Case 1: 단순 참조
data = {"host": "api.com", "url": "${host}:443"}
resolver = unified_resolver(data)
result = resolver.apply(data)
# {'host': 'api.com', 'url': 'api.com:443'}

# Case 2: KeyPath 중첩 참조
data = {"db": {"host": "localhost"}, "url": "${db__host}:5432"}
resolver = unified_resolver(data, enable_keypath=True)
result = resolver.apply(data)
# {'db': {'host': 'localhost'}, 'url': 'localhost:5432'}

# Case 3: 환경 변수 + Context
data = {"url": "http://{{HOST}}:${PORT:8000}"}
resolver = unified_resolver(
    data,
    enable_env=True,
    enable_context=True,
    context={"HOST": "localhost"}
)
result = resolver.apply(data)
# {'url': 'http://localhost:8000'}  # PORT 환경변수 없으면 8000 사용

# Case 4: 모든 기능 통합 🔥
data = {
    "db": {"host": "prod-db", "port": 5432},
    "env": "production",
    "url": "${env}://{{REGION}}.${db__host}:${PORT:${db__port}}"
}
resolver = unified_resolver(
    data,
    enable_keypath=True,
    enable_env=True,
    enable_context=True,
    context={"REGION": "us-west"}
)
result = resolver.apply(data)
# url: "production://us-west.prod-db:5432"
```

---

## ⚙️ 설계 원칙

- 모든 Normalizer/Resolver는 `Normalizer`/`Resolver` 추상 기반을 상속
- `apply()` 단일 인터페이스 기반
- 정책(Pydantic Policy) 기반 설정 주입 구조
- **UnifiedResolver**: 정책 조합으로 모든 참조 해석 통합
- 단일 진입점(`__init__.py`)에서 핵심 클래스 재노출 및 팩토리 제공

---

## 🔧 확장 및 마이그레이션

### 신규 프로젝트
- ✅ `unified_resolver()` 사용 권장
- 필요한 기능만 정책으로 활성화

### 기존 코드 마이그레이션

```python
# Before (ReferenceResolver)
from unify_utils import reference_resolver
resolver = reference_resolver(data)

# After (UnifiedResolver)
from unify_utils import unified_resolver
resolver = unified_resolver(data)  # 동일한 동작

# Before (KeyPathReferenceResolver)
from keypath_utils import KeyPathReferenceResolver
resolver = KeyPathReferenceResolver(data)

# After (UnifiedResolver)
from unify_utils import unified_resolver
resolver = unified_resolver(data, enable_keypath=True)

# Before (PlaceholderResolver)
from unify_utils import placeholder_resolver
resolver = placeholder_resolver(context={"HOST": "localhost"})

# After (UnifiedResolver)
from unify_utils import unified_resolver
resolver = unified_resolver(
    {},
    enable_env=True,
    enable_context=True,
    context={"HOST": "localhost"}
)
```

### 향후 계획
- YAML 기반 Rule 정의 로더 추가 예정
- 사용자 정의 RuleType 등록 지원 구조 (플러그인 구조)

---

## 🧪 테스트 시나리오 (예정)
- 다양한 데이터 타입 조합 테스트
- 재귀 구조 vs 평면 구조 비교
- strict 모드와 예외 상황 테스트

---

## 📁 파일 구조 요약
```
unify_utils/
 ┣ core/
 ┃ ┣ __init__.py          # core API re-export
 ┃ ┣ interface.py         # Normalizer/Resolver 추상 기반
 ┃ ┗ policy.py            # NormalizePolicy + ResolverPolicy
 ┣ normalizers/
 ┃ ┣ __init__.py          # Normalizer 공개 API
 ┃ ┣ list.py              # ListNormalizer
 ┃ ┣ rule.py              # RuleBasedNormalizer
 ┃ ┗ value.py             # ValueNormalizer
 ┣ presets/
 ┃ ┗ rules.py             # NormalizeRule, RulePresets, Enums
 ┣ resolver/
 ┃ ┣ __init__.py          # Resolver 공개 API
 ┃ ┣ unified.py           # UnifiedResolver ⭐ 권장
 ┃ ┣ reference.py         # ReferenceResolver (레거시)
 ┃ ┗ placeholder.py       # PlaceholderResolver (레거시)
 ┣ __init__.py            # 패키지 진입점 + 편의 팩토리
 ┗ ___README___.md
```
