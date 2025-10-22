# ConfigLoader Section 동작 올바른 이해

## ✅ 현재 구조는 정상입니다!

### 현재 방식

```yaml
# webdriver_config_loader.yaml
source:
  - src: [webdriver_china.yaml, "webdriver_china"]   ← section 지정
  - src: [webdriver_global.yaml, "webdriver_global"] ← section 지정
```

```yaml
# webdriver_china.yaml
webdriver_china:        # ← 최상위 키
  region: "china"

# webdriver_global.yaml
webdriver_global:       # ← 최상위 키
  region: "global"
```

### 사용 방법

```python
loader = ConfigLoader(config_loader_cfg_path="webdriver_config_loader.yaml")

# China 설정
china_config = loader.to_dict(section="webdriver_china")
china_policy = WebDriverPolicy(**china_config)

# Global 설정
global_config = loader.to_dict(section="webdriver_global")
global_policy = WebDriverPolicy(**global_config)
```

**결과:**
- ✅ webdriver_china와 webdriver_global을 **별도 section**으로 구분
- ✅ 동일한 WebDriverPolicy 사용
- ✅ section명으로 china/global 구분

---

## 🎯 요구사항 재해석

### 제가 오해한 것

❌ **잘못된 이해:**
> "webdriver_china.yaml과 webdriver_global.yaml을 둘 다 section='webdriver'로 통일해야 한다"

✅ **올바른 이해:**
> "config_loader의 source에서 section을 지정하면, 그게 최종 section명이 된다"
> "YAML 최상위 키와 config_loader section이 일치하면 정상, 불일치하면 문제"

---

## 🔍 요구사항 검증

### 1. 동일 구조 YAML + 다른 내용 → Section명으로 구분

**상황:**
- webdriver_china.yaml, webdriver_global.yaml
- 둘 다 동일한 구조 (provider, region, firefox 등)
- 내용만 다름 (region: china vs global)

**현재 동작:**
```python
loader = ConfigLoader(config_loader_cfg_path="webdriver_config_loader.yaml")

# State 구조: {'webdriver_china': {...}, 'webdriver_global': {...}}
china = loader.to_dict(section="webdriver_china")   # ✅ china 설정
global = loader.to_dict(section="webdriver_global") # ✅ global 설정
```

**결론:** ✅ **정상 동작**

---

### 2. YAML 최상위 Section 설정/미설정 모두 동작

**설정됨:**
```yaml
# webdriver_china.yaml
webdriver_china:        # ← 최상위 Section 존재
  provider: "firefox"
```

**미설정됨 (가정):**
```yaml
# webdriver_flat.yaml (최상위 Section 없음)
provider: "firefox"     # ← 바로 최상위
region: "china"
```

**config_loader에서:**
```yaml
source:
  - src: [webdriver_flat.yaml, "webdriver"]  # ← section 지정으로 wrap
```

**결과:**
```python
# State: {'webdriver': {'provider': 'firefox', 'region': 'china'}}
config = loader.to_dict(section="webdriver")  # ✅ 정상
```

**결론:** ✅ **둘 다 동작 가능**

---

### 3. YAML 최상위 == ConfigLoader Section → 동일 Section 추출

**상황:**
```yaml
# webdriver_china.yaml
webdriver_china:        # ← 최상위 키
  ...
```

```yaml
# config_loader
source:
  - src: [webdriver_china.yaml, "webdriver_china"]  # ← 일치!
```

**결과:**
```python
# State: {'webdriver_china': {...}}
config = loader.to_dict(section="webdriver_china")  # ✅ 정상 추출
```

**결론:** ✅ **정상 동작**

---

### 4. YAML 최상위 != ConfigLoader Section → Raise ⚠️

**상황:**
```yaml
# webdriver_china.yaml
webdriver_china:        # ← 최상위 키
  ...
```

```yaml
# config_loader
source:
  - src: [webdriver_china.yaml, "webdriver"]  # ← 불일치!
```

**현재 동작:**
```python
# State: {'webdriver': {'webdriver_china': {...}}}  ← 중첩됨!
config = loader.to_dict(section="webdriver")
# → {'webdriver_china': {...}}  ← 한 단계 더 들어가야 접근
```

**문제점:**
- config에서 `provider`에 직접 접근 불가
- `config['webdriver_china']['provider']`로 접근해야 함
- WebDriverPolicy 파싱 실패!

**요구사항:**
```python
# ValueError 발생해야 함!
raise ValueError(
    f"Section mismatch: "
    f"YAML top-level key is 'webdriver_china', "
    f"but section='webdriver' specified in config_loader."
)
```

**결론:** ❌ **구현 필요!**

---

### 5. 모듈별 Section 기본값

**시나리오:**
```python
# crawl_utils 모듈에서 기본 section = "webdriver"
loader = ConfigLoader(config_loader_cfg_path="...")

# section 지정 안 하면?
config = loader.to_dict()  # ← section 미지정
```

**현재 동작:**
```python
# 전체 State 반환
# {'webdriver_china': {...}, 'webdriver_global': {...}}
```

**요구사항:**
- 모듈이 기본 section명을 가짐 (예: "webdriver")
- section 미지정 시 모듈 기본값 사용
- 하지만 현재는 china/global이 분리되어 있어서 기본값 선택 어려움

**해결:**
```python
# Option 1: 명시적 지정
config = loader.to_dict(section="webdriver_china")  # ← 명확!

# Option 2: 모듈 기본값 + fallback
default_section = "webdriver_china"  # 모듈 설정
config = loader.to_dict(section=default_section)
```

**결론:** ⚠️ **부분 구현 (명시적 지정 필요)**

---

## 🔥 실제 문제점은 단 하나!

### 요구사항 4: Section 불일치 시 Raise

**문제가 되는 경우:**

```yaml
# 잘못된 config_loader 설정
source:
  - src: [webdriver_china.yaml, "webdriver"]  # ← 불일치!
```

```python
# 중첩 발생
loader = ConfigLoader(config_loader_cfg_path="...")
config = loader.to_dict(section="webdriver")
# → {'webdriver_china': {...}}  ← 예상과 다름!

# WebDriverPolicy 파싱 실패
policy = WebDriverPolicy(**config)  # ❌ 'provider' 키 없음!
```

**해결:**
```python
# source.py의 _extract_yaml() 수정
if section and section not in data and len(data) == 1:
    yaml_top_key = list(data.keys())[0]
    if yaml_top_key != section:
        raise ValueError(
            f"Section mismatch in YAML: "
            f"Expected section='{section}', "
            f"but YAML has '{yaml_top_key}' as top-level key. "
            f"Fix config_loader to use section='{yaml_top_key}'"
        )
```

---

## ✅ 최종 결론

### 현재 구조 평가

| 요구사항 | 상태 | 비고 |
|---------|------|------|
| 1. 동일 구조 YAML 구분 | ✅ 정상 | section명으로 구분 가능 |
| 2. 최상위 설정/미설정 | ✅ 정상 | config_loader section이 최종 결정 |
| 3. 일치 시 추출 | ✅ 정상 | 중첩 없이 추출됨 |
| 4. 불일치 시 Raise | ❌ **구현 필요** | 현재는 중첩만 발생 |
| 5. 모듈 기본값 | ⚠️ 부분 | 명시적 지정으로 해결 가능 |

### 즉시 구현 필요한 것

**단 하나:** Section Validation (요구사항 4)

**파일:** `modules/cfg_utils/services/source.py`
**위치:** `_extract_yaml()` 메서드

**구현:**
```python
# Section 불일치 검증
if section:
    if section not in data:
        yaml_keys = list(data.keys())
        if len(yaml_keys) == 1 and yaml_keys[0] != section:
            raise ValueError(
                f"Section mismatch: "
                f"YAML top-level key is '{yaml_keys[0]}', "
                f"but section='{section}' specified. "
                f"Use section='{yaml_keys[0]}' in config_loader."
            )
        # 나머지는 기존대로 wrap
        data = {section: data}
    else:
        data = {section: data[section]}
```

---

## 🎯 구현 승인 요청

**구현할 것:**
1. ✅ Section Validation 로직 추가 (요구사항 4)

**구현하지 않을 것:**
- ~~YAML 최상위 키 통일~~ (불필요 - 현재 구조가 올바름)
- ~~모듈 기본 Section~~ (명시적 지정으로 충분)

**승인하시겠습니까?**
