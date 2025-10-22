# ConfigLoader 섹션명 동작 방식 정리

## ✅ 핵심 원칙

### 1. **YAML 파일의 최상위 섹션명 = 기본 섹션명**

```yaml
# webdriver_china.yaml
webdriver:          # ← 최상위 섹션명
  provider: "firefox"
  region: "china"
```

```python
loader = ConfigLoader(src=("webdriver_china.yaml", "webdriver"))
data = loader.to_dict(section="webdriver")  # ✅ 성공
# → {'provider': 'firefox', 'region': 'china', ...}
```

---

### 2. **src=(path, section)의 section 동작 방식**

#### **Case A: YAML에 해당 section이 존재하는 경우**
- YAML에서 해당 section만 추출 → 최상위로 올림

```yaml
# config.yaml
webdriver:
  provider: "firefox"
image:
  max_width: 1024
```

```python
loader = ConfigLoader(src=("config.yaml", "webdriver"))
full = loader.to_dict()
# → {'webdriver': {'provider': 'firefox'}}  # image 섹션은 제외됨

section = loader.to_dict(section="webdriver")
# → {'provider': 'firefox'}  # webdriver 내부만 반환
```

#### **Case B: YAML에 해당 section이 없는 경우**
- YAML 전체를 해당 section으로 wrap

```yaml
# xlcrawl_excel.yaml
xlcrawl_excel:      # ← YAML 최상위 키
  target: {...}
  xw_app: {...}
```

```python
# ❌ 잘못된 사용: YAML에 'excel' 키가 없음
loader = ConfigLoader(src=("xlcrawl_excel.yaml", "excel"))
full = loader.to_dict()
# → {'excel': {'xlcrawl_excel': {...}}}  # ⚠️ excel 내부에 xlcrawl_excel이 중첩됨!

section = loader.to_dict(section="excel")
# → {'xlcrawl_excel': {...}}  # 실제 데이터는 한 단계 더 들어가야 접근 가능


# ✅ 올바른 사용: YAML 최상위 키와 동일
loader = ConfigLoader(src=("xlcrawl_excel.yaml", "xlcrawl_excel"))
full = loader.to_dict()
# → {'xlcrawl_excel': {...}}

section = loader.to_dict(section="xlcrawl_excel")
# → {'target': {...}, 'xw_app': {...}}  # 직접 접근 가능
```

---

## 🎯 webdriver YAML 검증 결과

### ✅ **webdriver_china.yaml**
```yaml
webdriver:          # ← 최상위 섹션명
  provider: "firefox"
  region: "china"
  firefox:
    profile_path: "M:/Firefox_Profile/CRAWL_CHINA"
```

**사용법:**
```python
# Option 1: 직접 로드
loader = ConfigLoader(src=("webdriver_china.yaml", "webdriver"))
config = loader.to_dict(section="webdriver")
# → {'provider': 'firefox', 'region': 'china', ...}

# Option 2: config_loader_*.yaml 사용
# config_loader_crawl.yaml
source:
  - src: ["webdriver_china.yaml", "webdriver"]  # ✅ 올바름

loader = ConfigLoader(config_loader_cfg_path="config_loader_crawl.yaml")
config = loader.to_dict(section="webdriver")
# → {'provider': 'firefox', 'region': 'china', ...}
```

---

## ⚠️ 실제 발견된 문제: config_loader_xlcrawl.yaml

### 현재 상태 (문제 있음)
```yaml
# config_loader_xlcrawl.yaml
source:
  - src: ["xlcrawl_excel.yaml", "excel"]  # ❌ xlcrawl_excel.yaml의 최상위 키는 'xlcrawl_excel'
  - src: ["xlcrawl_crawl.yaml", "crawl"]  # ❌ xlcrawl_crawl.yaml의 최상위 키는 'xlcrawl_crawl'
```

### 결과
```python
loader = ConfigLoader(config_loader_cfg_path="config_loader_xlcrawl.yaml")
full = loader.to_dict()
# → {'excel': {'xlcrawl_excel': {...}}, 'crawl': {'xlcrawl_crawl': {...}}}
#            ↑ 한 단계 더 중첩됨!

excel = loader.to_dict(section="excel")
# → {'xlcrawl_excel': {...}}  # 실제 데이터는 excel.xlcrawl_excel에 위치
```

---

## ✅ 해결 방법

### **Option 1: YAML 최상위 키 변경 (권장)**
```yaml
# xlcrawl_excel.yaml
xlcrawl_excel:  # ← 'excel'로 변경
  target: {...}

# ↓ 변경 후

# xlcrawl_excel.yaml
excel:          # ✅ 최상위 키 변경
  target: {...}
```

### **Option 2: config_loader에서 section 수정**
```yaml
# config_loader_xlcrawl.yaml
source:
  - src: ["xlcrawl_excel.yaml", "xlcrawl_excel"]  # ✅ YAML 최상위 키와 동일
  - src: ["xlcrawl_crawl.yaml", "xlcrawl_crawl"]  # ✅ YAML 최상위 키와 동일
```

```python
loader = ConfigLoader(config_loader_cfg_path="config_loader_xlcrawl.yaml")
excel = loader.to_dict(section="xlcrawl_excel")  # ✅ 직접 접근
crawl = loader.to_dict(section="xlcrawl_crawl")  # ✅ 직접 접근
```

### **Option 3: section 없이 로드**
```yaml
# config_loader_xlcrawl.yaml
source:
  - src: ["xlcrawl_excel.yaml"]  # section 생략
  - src: ["xlcrawl_crawl.yaml"]  # section 생략
```

```python
loader = ConfigLoader(config_loader_cfg_path="config_loader_xlcrawl.yaml")
excel = loader.to_dict(section="xlcrawl_excel")  # ✅ YAML 최상위 키로 접근
crawl = loader.to_dict(section="xlcrawl_crawl")  # ✅ YAML 최상위 키로 접근
```

---

## 📝 정리

| 상황 | src=(path, section) | to_dict(section=?) | 결과 |
|------|---------------------|-------------------|------|
| YAML 최상위 키 = webdriver<br>section = "webdriver" | ✅ 일치 | section="webdriver" | ✅ 직접 접근 |
| YAML 최상위 키 = xlcrawl_excel<br>section = "excel" | ❌ 불일치 | section="excel" | ⚠️ 중첩됨 (excel.xlcrawl_excel) |
| YAML 최상위 키 = xlcrawl_excel<br>section = "xlcrawl_excel" | ✅ 일치 | section="xlcrawl_excel" | ✅ 직접 접근 |

**핵심 규칙:**
> **src=(path, section)의 section은 YAML 최상위 키와 동일해야 중첩 없이 직접 접근 가능!**

---

## 🔥 webdriver YAML 사용 시 주의사항

### ✅ **올바른 사용**
```python
# 1. 직접 로드
loader = ConfigLoader(src=("webdriver_china.yaml", "webdriver"))
config = loader.to_dict(section="webdriver")
policy = WebDriverPolicy(**config)

# 2. config_loader_*.yaml 사용
# config_loader.yaml
source:
  - src: ["webdriver_china.yaml", "webdriver"]  # ✅ 최상위 키와 동일

loader = ConfigLoader(config_loader_cfg_path="config_loader.yaml")
config = loader.to_dict(section="webdriver")
policy = WebDriverPolicy(**config)
```

### ❌ **잘못된 사용**
```python
# config_loader.yaml
source:
  - src: ["webdriver_china.yaml", "driver"]  # ❌ YAML 최상위 키는 'webdriver'

loader = ConfigLoader(config_loader_cfg_path="config_loader.yaml")
config = loader.to_dict(section="driver")
# → {'webdriver': {...}}  # 중첩됨!

# WebDriverPolicy 파싱 실패!
policy = WebDriverPolicy(**config)  # ❌ 'provider' 키가 없음
```

---

## 🎯 결론

**ConfigLoader에서 YAML 로드 시:**
1. ✅ **YAML 파일의 최상위 섹션명 = ConfigLoader의 섹션명**
2. ✅ **src=(path, section)의 section은 YAML 최상위 키와 동일해야 함**
3. ✅ **webdriver_china.yaml의 'webdriver' → section='webdriver'**
4. ⚠️ **section이 YAML 최상위 키와 다르면 중첩 구조가 됨!**
