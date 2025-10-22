# ConfigLoader 요구사항 vs 현재 구현 종합 분석 보고서

## 📋 요구사항 정리

### 1. 동일 구조 YAML + 다른 내용 → Section명으로 구분
- **목적**: webdriver_china.yaml, webdriver_global.yaml 같은 동일 구조를 Section명으로 구분
- **예상 동작**: 
  - ConfigLoader(src=(webdriver_china.yaml, "webdriver"))
  - ConfigLoader(src=(webdriver_global.yaml, "webdriver"))
  - 둘 다 section="webdriver"로 추출 가능해야 함

### 2. YAML 최상위 Section 설정/미설정 모두 동작
- **설정됨**: YAML에 최상위 Section 키가 있음 (예: webdriver_china:)
- **미설정됨**: YAML이 flat 구조 (provider:, region: 등이 바로 최상위)

### 3. YAML 최상위 == ConfigLoader Section → 동일 Section 추출
- **조건**: YAML 최상위 키 = ConfigLoader에서 지정한 section
- **동작**: 중첩 없이 해당 section 데이터 추출

### 4. YAML 최상위 != ConfigLoader Section → Raise ⚠️
- **조건**: YAML 최상위 키 ≠ ConfigLoader에서 지정한 section
- **동작**: ValueError 발생 (중첩/wrap 금지!)

### 5. 모듈별 Section 기본값 사용
- **조건**: ConfigLoader에서 section 미지정
- **동작**: 모듈의 기본 section 사용 (예: webdriver 모듈은 "webdriver")

---

## 🔍 현재 구현 분석

### 현재 YAML 파일 구조

```yaml
# webdriver_china.yaml
webdriver_china:        # ← 최상위 키
  provider: "firefox"
  region: "china"
  firefox: {...}

# webdriver_global.yaml
webdriver_global:       # ← 최상위 키
  provider: "firefox"
  region: "global"
  firefox: {...}
```

### 현재 ConfigLoader 동작

```python
# source.py의 _extract_yaml() - Line 240-248
if section:
    if section in data:
        # Section이 YAML에 존재: 해당 section만 추출 후 wrap
        data = {section: data[section]}
    else:
        # Section이 YAML에 없음: 전체를 해당 section으로 wrap
        data = {section: data}
```

**동작 시나리오:**

| YAML 최상위 키 | ConfigLoader section | 결과 | 중첩 여부 |
|---------------|---------------------|------|---------|
| `webdriver_china` | `"webdriver"` | `{'webdriver': {'webdriver_china': {...}}}` | ❌ 중첩됨 |
| `webdriver_china` | `"webdriver_china"` | `{'webdriver_china': {...}}` | ✅ 정상 |
| `webdriver` | `"webdriver"` | `{'webdriver': {...}}` | ✅ 정상 |
| `xlcrawl_excel` | `"excel"` | `{'excel': {'xlcrawl_excel': {...}}}` | ❌ 중첩됨 |

---

## ❌ 문제점 분석

### 문제 1: 요구사항 1 달성 불가 ⚠️

**현재 상황:**
```yaml
# webdriver_china.yaml
webdriver_china:        # 최상위 키가 다름!
  region: "china"

# webdriver_global.yaml
webdriver_global:       # 최상위 키가 다름!
  region: "global"
```

```python
# 둘 다 "webdriver" section으로 사용하려면?
loader1 = ConfigLoader(src=("webdriver_china.yaml", "webdriver"))
# → {'webdriver': {'webdriver_china': {...}}}  ← 중첩됨!

loader2 = ConfigLoader(src=("webdriver_global.yaml", "webdriver"))
# → {'webdriver': {'webdriver_global': {...}}}  ← 중첩됨!
```

**요구사항과의 충돌:**
- 요구사항: 동일한 section명 "webdriver"로 구분
- 현실: 각 파일의 최상위 키가 다름 (webdriver_china, webdriver_global)
- 결과: section="webdriver" 지정 시 중첩 발생

### 문제 2: 요구사항 4 미구현 ❌

**현재 동작:**
```python
loader = ConfigLoader(src=("xlcrawl_excel.yaml", "excel"))
# YAML 최상위: xlcrawl_excel
# Section 지정: excel
# 현재: {'excel': {'xlcrawl_excel': {...}}}  ← Wrap됨
# 요구: ValueError("Section mismatch!")      ← Raise!
```

**코드 위치:** `source.py:245-247`
```python
else:
    # Section이 YAML에 없음: 전체를 해당 section으로 wrap
    data = {section: data}  # ← 여기서 Raise해야 함!
```

### 문제 3: 요구사항 5 미구현 ⚠️

**현재 상황:**
- 모듈별 Section 기본값 개념 없음
- ConfigLoader에서 section 미지정 시 YAML 최상위 키 사용
- Policy 클래스에 default_section 필드 없음

---

## 🎯 해결 방안

### Option A: YAML 최상위 키 통일 (권장) ✅

**변경 전:**
```yaml
# webdriver_china.yaml
webdriver_china:
  region: "china"

# webdriver_global.yaml
webdriver_global:
  region: "global"
```

**변경 후:**
```yaml
# webdriver_china.yaml
webdriver:              # ← 통일!
  region: "china"

# webdriver_global.yaml
webdriver:              # ← 통일!
  region: "global"
```

**장점:**
- ✅ 요구사항 1 달성: 동일 section명 "webdriver" 사용 가능
- ✅ 요구사항 3 자동 만족: 최상위 == section
- ✅ 코드 수정 불필요

**단점:**
- YAML 파일명으로만 구분 (파일 내부에서 구분 어려움)

### Option B: Section Mapping 기능 추가

**SourcePolicy에 section_mapping 추가:**
```python
class SourcePolicy(BaseModel):
    src: Any
    section_mapping: Optional[Dict[str, str]] = None
    # {"webdriver_china": "webdriver", "webdriver_global": "webdriver"}
```

**동작:**
```python
# YAML 최상위 키가 section_mapping에 있으면 자동 변환
if yaml_top_key in section_mapping:
    data = {section_mapping[yaml_top_key]: data[yaml_top_key]}
```

**장점:**
- YAML 파일 수정 불필요
- 유연한 매핑 가능

**단점:**
- 설정 복잡도 증가
- Mapping 관리 필요

### Option C: Section Validation 강화 (요구사항 4)

**UnifiedSource._extract_yaml() 수정:**
```python
# 2. Section 처리
if section:
    yaml_top_keys = list(data.keys())
    
    if section in data:
        # Case 1: Section이 YAML에 존재 → 추출
        data = {section: data[section]}
    elif len(yaml_top_keys) == 1:
        # Case 2: YAML 최상위 키 1개 & section과 불일치 → Raise!
        raise ValueError(
            f"Section mismatch: "
            f"YAML top-level key is '{yaml_top_keys[0]}', "
            f"but section='{section}' specified. "
            f"Please use section='{yaml_top_keys[0]}' or rename YAML key to '{section}'."
        )
    else:
        # Case 3: YAML 최상위 키 여러 개 → Wrap (기존 동작)
        data = {section: data}
```

**장점:**
- ✅ 요구사항 4 달성: 불일치 시 명확한 에러 메시지
- YAML 구조 문제를 조기에 발견

**단점:**
- 기존 동작과 호환성 깨짐 (Breaking Change)

### Option D: 모듈 기본 Section 추가 (요구사항 5)

**Policy 클래스에 default_section 추가:**
```python
class WebDriverPolicy(BaseModel):
    name: str = Field("webdriver", description="Config section name")
    # ↑ 이것을 기본값으로 사용
```

**ConfigLoader에서 활용:**
```python
def to_dict(self, section: Optional[str] = None, policy_class: Optional[Type[BaseModel]] = None) -> Dict:
    if section is None and policy_class is not None:
        # Policy의 name 필드를 기본 section으로 사용
        section = policy_class.model_fields["name"].default
    
    return self.config.to_dict(section=section)
```

**사용 예:**
```python
loader = ConfigLoader(src="webdriver_china.yaml")
config = loader.to_dict(policy_class=WebDriverPolicy)  # section 자동 = "webdriver"
```

---

## 📊 요구사항 달성도

| 요구사항 | Option A | Option B | Option C | Option D |
|---------|----------|----------|----------|----------|
| 1. 동일 구조 구분 | ✅ | ✅ | ✅ | ✅ |
| 2. 설정/미설정 | ✅ | ✅ | ✅ | ✅ |
| 3. 일치 시 추출 | ✅ | ✅ | ✅ | ✅ |
| 4. 불일치 Raise | - | - | ✅ | - |
| 5. 모듈 기본값 | - | - | - | ✅ |

---

## ✅ 최종 권장 방안

### 조합: **Option A + Option C + Option D**

1. **YAML 최상위 키 통일 (Option A)**
   - webdriver_china.yaml → 최상위 키를 `webdriver`로 변경
   - webdriver_global.yaml → 최상위 키를 `webdriver`로 변경

2. **Section Validation 강화 (Option C)**
   - UnifiedSource._extract_yaml()에 불일치 검증 추가
   - 명확한 에러 메시지로 사용자 가이드

3. **모듈 기본 Section (Option D)**
   - Policy.name 필드를 기본 section으로 활용
   - ConfigLoader.to_dict(policy_class=...) 패턴 지원

**구현 우선순위:**
1. 🔥 **즉시**: YAML 최상위 키 통일 (webdriver_china: → webdriver:)
2. 🔥 **필수**: Section Validation (요구사항 4)
3. 🎯 **선택**: 모듈 기본 Section (요구사항 5)

---

## 🚨 즉시 조치 필요 사항

### 1. YAML 파일 수정 (필수)

**변경 대상:**
- `webdriver_china.yaml`: `webdriver_china:` → `webdriver:`
- `webdriver_global.yaml`: `webdriver_global:` → `webdriver:`

### 2. UnifiedSource 수정 (필수)

**파일**: `modules/cfg_utils/services/source.py`
**위치**: Line 240-248 (_extract_yaml 메서드)

**수정 내용:**
```python
# 2. Section 처리
if section:
    yaml_top_keys = list(data.keys())
    
    if section in data:
        # Section이 YAML에 존재: 해당 section만 추출 후 wrap
        data = {section: data[section]}
    elif len(yaml_top_keys) == 1 and yaml_top_keys[0] != section:
        # Section이 YAML에 없고, 최상위 키가 1개이며, section과 불일치
        raise ValueError(
            f"Section mismatch: YAML top-level key is '{yaml_top_keys[0]}', "
            f"but section='{section}' was specified. "
            f"Options: 1) Use section='{yaml_top_keys[0]}' in ConfigLoader, "
            f"or 2) Rename YAML key to '{section}'."
        )
    else:
        # Section이 YAML에 없음: 전체를 해당 section으로 wrap
        data = {section: data}
```

---

## 📝 정리

**현재 상태:**
- ❌ 요구사항 1: YAML 최상위 키가 달라 달성 불가
- ✅ 요구사항 2: 부분 달성 (설정된 경우만 테스트됨)
- ✅ 요구사항 3: 정상 동작
- ❌ 요구사항 4: Wrap만 하고 Raise 안 함
- ⚠️ 요구사항 5: 기본값 개념 미구현

**조치 후 상태 (예상):**
- ✅ 요구사항 1: YAML 최상위 키 통일로 달성
- ✅ 요구사항 2: 정상 동작
- ✅ 요구사항 3: 정상 동작
- ✅ 요구사항 4: Section Validation으로 달성
- ✅ 요구사항 5: Policy.name 활용으로 달성
