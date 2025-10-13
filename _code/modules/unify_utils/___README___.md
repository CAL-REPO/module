# 🧰 unify_utils

**데이터 정규화 · 구조 표준화 유틸리티 패키지**

입력 데이터의 문자열, 타입, 리스트, 구조 등을 일관성 있게 정제합니다.  
규칙 기반 치환, 재귀적 구조 처리, 단일값 변환, 리스트 분할, 참조 해석 등 다양한 방식의 정규화를 지원하며,  
Pydantic 기반 설정 정책을 통해 안전하고 유연한 구성이 가능합니다.

---

## 📦 구성 모듈

### 🔹 `core/`
- `NormalizerBase`: 모든 Normalizer 클래스의 추상 기반 (재귀 처리, strict 모드, compose 지원)
- `PolicyBase`: 모든 Policy 클래스의 공통 설정
- `RulePolicy`, `ValuePolicy`, `ListPolicy`: 각각의 Normalizer에서 사용하는 설정 모델

### 🔹 `normalizers/`
- `RuleBasedNormalizer`: 정규식 / 클린룰 기반 문자열 정규화기
- `ValueNormalizer`: bool/int/date/filename 등 단일 값 정규화기
- `ListNormalizer`: 문자열, 리스트 등 시퀀스형 데이터 정규화기
- `ReferenceResolver`: ${key.path[:default]} 참조 문자열 해석 정규화기

### 🔹 `presets/`
- `NormalizeRule`: 룰 정의 모델
- `RuleType`, `LetterCase`, `RegexFlag`: 룰 적용 방식 및 옵션 Enum
- `RulePresets`: 자주 사용하는 정규화 규칙 모음

---

## 🚀 사용 예시

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

```python
from unify_utils import reference_resolver
resolver = reference_resolver({"a": {"b": 123}, "text": "value: ${a.b}"})
resolved = resolver.apply(resolver.data)
# {'a': {'b': 123}, 'text': 'value: 123'}
```

---

## ⚙️ 설계 원칙

- 모든 Normalizer는 `NormalizerBase`를 상속
- `apply()` 단일 인터페이스 기반
- 정책(Pydantic Policy) 기반 설정 주입 구조
- 단일 진입점(`__init__.py`)에서 핵심 클래스 재노출 및 팩토리 제공

---

## 🔧 확장 포인트

- YAML 기반 Rule 정의 로더 추가 예정
- 사용자 정의 RuleType 등록 지원 구조 (플러그인 구조)
- 기존 `resolve_utils` 기능 통합 완료 → `ReferenceResolver` 편입

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
 ┃ ┣ base.py              # NormalizerBase
 ┃ ┗ policy.py            # PolicyBase 및 설정 모델
 ┣ normalizers/
 ┃ ┣ rule_normalizer.py   # RuleBasedNormalizer
 ┃ ┣ value_normalizer.py  # ValueNormalizer
 ┃ ┣ list_normalizer.py   # ListNormalizer
 ┃ ┗ reference_resolver.py# ReferenceResolver
 ┣ presets/
 ┃ ┗ rules.py             # NormalizeRule, Presets, Enums
 ┗ __init__.py            # 진입점 + 편의 팩토리
```
