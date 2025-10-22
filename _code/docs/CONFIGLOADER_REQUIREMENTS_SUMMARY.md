# ConfigLoader 요구사항 검증 결과 요약

## 🔥 핵심 문제점

### 1. ❌ YAML 최상위 키가 달라서 요구사항 1 달성 불가

**현재 상황:**
```yaml
# webdriver_china.yaml
webdriver_china:        # ← 파일마다 다름!
  region: "china"

# webdriver_global.yaml  
webdriver_global:       # ← 파일마다 다름!
  region: "global"
```

**문제:**
```python
# 둘 다 "webdriver" section으로 사용하려면?
loader = ConfigLoader(src=("webdriver_china.yaml", "webdriver"))
# → {'webdriver': {'webdriver_china': {...}}}  ← 중첩됨!
```

**원인:** YAML 최상위 키 != ConfigLoader section 지정

---

### 2. ❌ Section 불일치 시 Raise 안 함 (요구사항 4)

**현재 동작:**
```python
# source.py Line 245-247
else:
    # Section이 YAML에 없음: 전체를 해당 section으로 wrap
    data = {section: data}  # ← Wrap만 함! Raise 안 함!
```

**문제:**
- YAML 최상위: `xlcrawl_excel`
- Section 지정: `excel`
- 현재: Wrap → `{'excel': {'xlcrawl_excel': {...}}}`
- 요구: Raise → `ValueError("Section mismatch!")`

---

### 3. ⚠️ 모듈 기본 Section 개념 없음 (요구사항 5)

**현재:**
- Policy 클래스에 default_section 필드 없음
- ConfigLoader에서 section 미지정 시 YAML 최상위 키 사용
- 모듈이 원하는 기본값과 다를 수 있음

---

## ✅ 해결 방안

### Option A: YAML 최상위 키 통일 (권장 - 즉시 적용 가능)

**변경:**
```yaml
# webdriver_china.yaml
webdriver:              # ← 통일!
  region: "china"

# webdriver_global.yaml
webdriver:              # ← 통일!
  region: "global"
```

**효과:**
- ✅ 요구사항 1 달성
- ✅ 요구사항 3 자동 만족
- ✅ 코드 수정 불필요

---

### Option C: Section Validation 강화 (요구사항 4)

**수정 위치:** `modules/cfg_utils/services/source.py` Line 240-248

**수정 내용:**
```python
if section:
    yaml_top_keys = list(data.keys())
    
    if section in data:
        data = {section: data[section]}
    elif len(yaml_top_keys) == 1 and yaml_top_keys[0] != section:
        # ✅ 불일치 시 Raise!
        raise ValueError(
            f"Section mismatch: YAML='{yaml_top_keys[0]}', section='{section}'"
        )
    else:
        data = {section: data}
```

---

### Option D: 모듈 기본 Section (요구사항 5)

**Policy 클래스 활용:**
```python
class WebDriverPolicy(BaseModel):
    name: str = Field("webdriver", ...)  # ← 이것을 기본값으로
```

**ConfigLoader 개선:**
```python
def to_dict(self, section=None, policy_class=None):
    if section is None and policy_class:
        section = policy_class.model_fields["name"].default
    return self.config.to_dict(section=section)
```

---

## 📊 요구사항 달성도

| 요구사항 | 현재 상태 | 조치 후 |
|---------|---------|--------|
| 1. 동일 구조 YAML 구분 | ❌ 중첩 발생 | ✅ YAML 키 통일 |
| 2. 최상위 설정/미설정 | ⚠️ 부분 달성 | ✅ 정상 |
| 3. 일치 시 추출 | ✅ 정상 | ✅ 정상 |
| 4. 불일치 시 Raise | ❌ Wrap만 함 | ✅ Validation 추가 |
| 5. 모듈 기본값 | ⚠️ 미구현 | ✅ Policy.name 활용 |

---

## 🚨 즉시 조치 필요

### 1. YAML 파일 수정 (필수) 🔥

**변경 대상:**
- `webdriver_china.yaml`: `webdriver_china:` → `webdriver:`
- `webdriver_global.yaml`: `webdriver_global:` → `webdriver:`

### 2. UnifiedSource 수정 (필수) 🔥

**파일:** `modules/cfg_utils/services/source.py`
**위치:** Line 240-248

**추가:** Section mismatch 검증 로직

---

## 📝 최종 권장 사항

**조합: Option A + Option C + Option D**

1. **즉시**: YAML 최상위 키 통일
2. **필수**: Section Validation 추가
3. **선택**: 모듈 기본 Section 지원

**우선순위:**
1. 🔥 YAML 파일 수정 (가장 간단)
2. 🔥 Section Validation (요구사항 4)
3. 🎯 모듈 기본 Section (요구사항 5)

---

## 🎯 다음 단계

**구현 승인 대기 중:**
- ✅ 문제점 파악 완료
- ✅ 해결 방안 제시 완료
- ⏳ 사용자 승인 대기
- ⏳ 구현 진행 대기
