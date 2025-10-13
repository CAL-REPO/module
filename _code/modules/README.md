# 📦 {모듈명}

## 1. 개요
- 역할: {이 모듈이 수행하는 주된 기능}
- 관련 모듈: {상호 의존 관계 명시}
- 사용 위치: {예시 또는 상위 호출 모듈}

## 2. 주요 클래스 / 함수
| 이름 | 타입 | 설명 |
|------|------|------|
| ExampleClass | class | 주요 클래스 역할 |
| example_function() | function | 기능 요약 |

## 3. 예시 코드
```python
from {모듈명} import {핵심 클래스 또는 함수}

obj = {핵심 클래스}()
obj.run()

📘 이 템플릿은 **yaml_utils**, **fso_utils**, **keypath_utils** 등 모든 모듈에 공통 적용합니다.

---

## 🧭 2️⃣ 구조 개선 우선순위

아래는 `module_tree.md` 기준으로  
**현재 구조상 불균형 / 중복 / 확장성 문제**가 예상되는 부분을 분석한 결과입니다:

| 우선순위 | 모듈 | 문제 요약 | 개선 방향 |
|-----------|--------|------------|-------------|
| 🔥 1 | **norm_utils** | `listnomalizer.py`, `normalizer.py`, `type_normalizer.py` 등 역할 중복 | 하나의 `NormalizerBase` 상속 구조로 통합 필요 |
| 🔥 2 | **resolve_utils** | placeholder 전용. 추후 `norm_utils`와 의존성 예상 | `norm_utils` 내부 클래스로 편입 가능성 검토 |
| ⚡ 3 | **keypath_utils** | `mixin`, `state`, `types`, `dict` 등 내부 구조 복잡 | Mixin 구조 정리 및 `dataclass` 기반화 |
| ⚡ 4 | **data_utils** | `df_ops`, `dict_ops`, `list_ops` 기능이 흩어져 있음 | 공통 인터페이스(`DataOpsBase`) 설계 필요 |
| ✅ 5 | **fso_utils** | 구조는 양호하나 `policy` / `ops` 일부 중복 | `ops`를 통합 진입점으로 정리 |
| ✅ 6 | **cfg_utils**, **yaml_utils** | 구조 안정적 | 주석 및 docstring 보강 중심 |
| ⏳ 7 | **firefox** | 브라우저 의존, 외부 라이브러리 많음 | 테스트 후 최종 단계 리팩토링 |
| 🚫 8 | **xl_utils** | 외부 API 의존(openpyxl, xlwings) | 마지막에 구조 통합 (지시대로 보류) |

---

## 🔍 정리

**우선 리팩토링 순서 제안**

