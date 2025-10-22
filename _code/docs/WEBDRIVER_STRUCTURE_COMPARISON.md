# 🔄 WebDriver 구조 변화: Before & After

## 📅 비교 날짜: 2025-10-22

---

## 🏗️ 구조 비교

### ❌ 기존 구조 (Legacy)

```
crawl_utils/
├─ provider/
│  ├─ base.py                    # BaseWebDriver (ABC)
│  ├─ factory.py                 # create_webdriver() 팩토리 함수
│  └─ firefox.py                 # FirefoxWebDriver (BaseWebDriver 상속)
│
└─ core/
   └─ policy.py                  # WebDriverPolicy
```

**문제점:**
```python
class FirefoxWebDriver(BaseWebDriver):
    def __init__(self, cfg_like=None, **overrides):
        # 🔴 문제 1: 설정 로딩 + 비즈니스 로직 혼재
        self.config = self._load_config(cfg_like, **overrides)
        self._driver = self._create_driver()
    
    def _load_config(self, cfg_like, **overrides):
        # 🔴 문제 2: default_config_filename="firefox.yaml" 하드코딩
        return ConfigLikeLoader.load_with_caller_path(
            cfg_like=cfg_like,
            policy_class=WebDriverPolicy,
            caller_file=__file__,
            default_config_filename="firefox.yaml",  # ❌ 하드코딩
            **overrides
        )
    
    def _create_driver(self):
        # WebDriver 생성 로직
        ...

# 🔴 문제 3: 팩토리 패턴으로 사용
driver = create_webdriver("firefox", "configs/firefox.yaml")
driver.driver.get("https://example.com")
driver.quit()
```

**문제점 요약:**
1. ❌ **SRP 위반**: 설정 로딩 + WebDriver 로직이 한 클래스에 혼재
2. ❌ **하드코딩**: `default_config_filename="firefox.yaml"` 고정
3. ❌ **섹션 이름 무시**: YAML의 `webdriver_china`, `webdriver_global` 사용 불가
4. ❌ **패턴 불일치**: image_utils의 ImageLoad 패턴과 다름
5. ❌ **복잡성**: BaseWebDriver, factory.py 등 불필요한 추상화

---

### ✅ 새로운 구조 (ImageLoad Pattern)

```
crawl_utils/
├─ adapter/
│  └─ webdriver.py               # WebDriverAdapter (설정 로딩)
│
├─ provider/
│  └─ firefox.py                 # FirefoxWebDriver (순수 로직)
│
└─ core/
   └─ policy.py                  # WebDriverPolicy
```

**구조 설명:**

#### 1. **WebDriverAdapter** (Adapter Layer)
```python
# crawl_utils/adapter/webdriver.py

class WebDriverAdapter:
    """WebDriver Adapter (ImageLoad 패턴)
    
    책임:
    1. WebDriverPolicy 로드 (ConfigLikeLoader 사용)
    2. provider 필드에 따라 적절한 WebDriver 선택
    3. Context Manager 지원
    """
    
    def __init__(self, cfg_like=None, **overrides):
        # ✅ 설정 로딩만 담당
        self.config = self._load_config(cfg_like, **overrides)
        
        # ✅ provider 필드로 자동 선택
        self._webdriver = self._create_webdriver()
    
    def _load_config(self, cfg_like, **overrides):
        # ✅ ConfigLikeLoader 사용 (일반화)
        return ConfigLikeLoader.load_with_caller_path(
            cfg_like=cfg_like,
            policy_class=WebDriverPolicy,
            caller_file=__file__,
            default_config_filename="webdriver.yaml",  # ✅ 일반화
            **overrides
        )
    
    def _create_webdriver(self):
        # ✅ provider 필드로 자동 선택
        if self.config.provider == "firefox":
            return FirefoxWebDriver(self.config)
        elif self.config.provider == "chrome":
            return ChromeWebDriver(self.config)
        # ...
    
    def start(self):
        self._webdriver.start()
    
    def quit(self):
        self._webdriver.quit()
    
    @property
    def driver(self):
        return self._webdriver.driver
```

#### 2. **FirefoxWebDriver** (Provider Layer)
```python
# crawl_utils/provider/firefox.py

class FirefoxWebDriver:
    """Firefox WebDriver - 순수 로직만 담당 (ImageLoad 패턴)
    
    책임:
    1. WebDriverPolicy를 받아서 Firefox WebDriver 생성
    2. 설정 로딩은 WebDriverAdapter가 담당 (SRP)
    """
    
    def __init__(self, config: WebDriverPolicy):
        # ✅ Policy만 받음 (설정 로딩 제거)
        if not config.firefox:
            raise ValueError("Firefox configuration required")
        
        self.config = config
        self._driver = None
        self._init_logger()
    
    def start(self):
        # ✅ Firefox WebDriver 시작
        options = self._configure_options()
        driver_path = self._get_driver_path()
        
        service = Service(executable_path=driver_path)
        self._driver = webdriver.Firefox(service=service, options=options)
    
    def quit(self):
        # ✅ Firefox WebDriver 종료
        if self._driver:
            self._driver.quit()
            self._driver = None
    
    @property
    def driver(self):
        # ✅ Selenium WebDriver 접근
        if self._driver is None:
            raise RuntimeError("WebDriver not started")
        return self._driver
```

---

## 📊 비교표

| 항목 | 기존 구조 (Legacy) | 새로운 구조 (ImageLoad) |
|------|-------------------|------------------------|
| **패턴** | Factory + Inheritance | Adapter + Provider |
| **SRP** | ❌ 설정 + 로직 혼재 | ✅ 분리 (Adapter vs Provider) |
| **섹션 이름** | ❌ 하드코딩 (`firefox.yaml`) | ✅ 자동 인식 (`webdriver_*`) |
| **YAML 지원** | ❌ 1개 (firefox.yaml) | ✅ 3개 (webdriver, webdriver_china, webdriver_global) |
| **provider 선택** | ❌ 팩토리 함수 호출 | ✅ provider 필드 자동 |
| **일관성** | ❌ image_utils와 다름 | ✅ image_utils와 동일 |
| **복잡성** | ❌ BaseWebDriver, factory | ✅ 단순 (Adapter + Provider) |
| **Context Manager** | ✅ 지원 | ✅ 지원 |
| **Logger** | ⚠️ 비표준 | ✅ image_utils와 동일 |

---

## 💻 사용법 비교

### ❌ 기존 사용법 (Legacy)

```python
from crawl_utils.provider import create_webdriver

# 팩토리 함수로 생성
driver = create_webdriver("firefox", "configs/firefox.yaml")

try:
    driver.driver.get("https://example.com")
    print(driver.driver.title)
finally:
    driver.quit()
```

**문제점:**
- `create_webdriver()` 팩토리 함수 필요
- `firefox.yaml` 파일명 고정
- `webdriver_china.yaml` 사용 불가

---

### ✅ 새로운 사용법 (ImageLoad)

#### 방법 1: Context Manager (권장)
```python
from crawl_utils.adapter import WebDriverAdapter

# 중국 지역 WebDriver
with WebDriverAdapter("configs/webdriver_china.yaml") as adapter:
    adapter.driver.get("https://taobao.com")
    print(adapter.driver.title)

# 글로벌 지역 WebDriver
with WebDriverAdapter("configs/webdriver_global.yaml") as adapter:
    adapter.driver.get("https://amazon.com")
    print(adapter.driver.title)
```

#### 방법 2: 수동 제어
```python
from crawl_utils.adapter import WebDriverAdapter

adapter = WebDriverAdapter("configs/webdriver_china.yaml")
adapter.start()

try:
    adapter.driver.get("https://taobao.com")
    print(adapter.driver.title)
finally:
    adapter.quit()
```

#### 방법 3: dict로 직접 설정
```python
adapter = WebDriverAdapter({
    "provider": "firefox",
    "region": "china",
    "firefox": {
        "profile_path": "M:/Firefox_Profile/CRAWL_CHINA"
    }
})
```

---

## 🎯 개선 효과

### 1. 단일 책임 원칙 (SRP)
```
[Before]
FirefoxWebDriver
├─ 설정 로딩      ❌ 혼재
└─ WebDriver 로직 ❌ 혼재

[After]
WebDriverAdapter → 설정 로딩만 담당      ✅
FirefoxWebDriver → WebDriver 로직만 담당 ✅
```

### 2. 유연성 향상
```
[Before]
❌ firefox.yaml만 지원
❌ 섹션 이름 고정

[After]
✅ webdriver.yaml (기본)
✅ webdriver_china.yaml (중국)
✅ webdriver_global.yaml (글로벌)
✅ 섹션 이름 자동 인식
```

### 3. 일관성 유지
```
[Before]
crawl_utils ≠ image_utils (패턴 불일치)

[After]
crawl_utils = image_utils (완전 일치)
├─ Adapter (설정 로딩)
└─ Provider (순수 로직)
```

### 4. 코드 간소화
```
[Before]
- BaseWebDriver (386줄)
- factory.py (112줄)
- FirefoxWebDriver (복잡)
= 총 500+ 줄

[After]
- WebDriverAdapter (203줄)
- FirefoxWebDriver (271줄, 순수 로직)
= 총 474줄 (26줄 감소 + 더 명확한 책임)
```

---

## 🔄 마이그레이션 가이드

### Step 1: Import 변경
```python
# Before
from crawl_utils.provider import create_webdriver

# After
from crawl_utils.adapter import WebDriverAdapter
```

### Step 2: 생성 방식 변경
```python
# Before
driver = create_webdriver("firefox", "configs/firefox.yaml")

# After
adapter = WebDriverAdapter("configs/webdriver.yaml")
# 또는
adapter = WebDriverAdapter("configs/webdriver_china.yaml")
```

### Step 3: 사용 방식 동일
```python
# Before & After 동일
adapter.driver.get("https://example.com")
print(adapter.driver.title)
adapter.quit()
```

---

## 📝 YAML 파일 예시

### webdriver.yaml (기본 글로벌)
```yaml
webdriver:
  provider: "firefox"
  region: "global"
  headless: false
  window_size: [1920, 1080]
  accept_languages: "en-US,en;q=0.9"
  
  firefox:
    binary_path: "C:/Program Files/Mozilla Firefox/firefox.exe"
    profile_path: ""
    driver_path: "M:/WebDriver/geckodriver_win32.exe"
```

### webdriver_china.yaml (중국 지역)
```yaml
webdriver_china:
  provider: "firefox"
  region: "china"
  headless: false
  window_size: [1920, 1080]
  accept_languages: "zh-CN,zh;q=0.9,en-US;q=0.8"
  
  firefox:
    binary_path: "C:/Program Files/Mozilla Firefox/firefox.exe"
    profile_path: "M:/Firefox_Profile/CRAWL_CHINA"
    driver_path: "M:/WebDriver/geckodriver_win32.exe"
```

### webdriver_global.yaml (글로벌 명시)
```yaml
webdriver_global:
  provider: "firefox"
  region: "global"
  headless: false
  window_size: [1920, 1080]
  accept_languages: "en-US,en;q=0.9,zh-CN;q=0.8"
  
  firefox:
    binary_path: "C:/Program Files/Mozilla Firefox/firefox.exe"
    profile_path: "M:/Firefox_Profile/CRAWL_GLOBAL"
    driver_path: "M:/WebDriver/geckodriver_win32.exe"
```

---

## ✨ 핵심 변화 요약

| 변화 | 설명 | 효과 |
|------|------|------|
| **Factory → Adapter** | `create_webdriver()` 제거 | 더 명확한 책임 |
| **Inheritance → Composition** | BaseWebDriver 제거 | 복잡성 감소 |
| **하드코딩 제거** | `firefox.yaml` → `webdriver.yaml` | 유연성 향상 |
| **섹션 자동 인식** | ConfigLikeLoader 개선 | 3개 YAML 지원 |
| **SRP 준수** | Adapter vs Provider 분리 | 유지보수성 향상 |
| **패턴 일관성** | image_utils와 동일 | 학습 비용 감소 |

---

**작성일**: 2025-10-22  
**비교 대상**: Legacy Factory Pattern vs ImageLoad Adapter Pattern  
**결론**: ✅ ImageLoad 패턴이 더 단순하고, 명확하며, 확장 가능합니다.
