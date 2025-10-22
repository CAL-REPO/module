# WebDriver 네이밍 컨벤션 분석 및 제안

## 📅 분석 날짜: 2025-10-23

---

## 🔍 1. WebDriverAdapter → WebDriver 이름 충돌 검토

### ❌ 충돌 위험 있음!

**충돌 지점:**
```python
# provider/firefox.py
from selenium import webdriver  # ← selenium.webdriver 모듈

# 만약 WebDriverAdapter → WebDriver로 변경한다면?
from crawl_utils.adapter import WebDriver  # ← 이름 충돌!
```

**실제 사용 예시:**
```python
# ❌ 문제 발생 가능
from selenium import webdriver
from crawl_utils.adapter import WebDriver

# selenium.webdriver가 WebDriver로 덮어씌워질 수 있음
driver = webdriver.Firefox()  # ← 어떤 webdriver?
adapter = WebDriver()  # ← 명확하지만 selenium.webdriver와 혼동
```

**Selenium 구조:**
```python
selenium/
  webdriver/
    __init__.py  # webdriver.Firefox, webdriver.Chrome 등
    firefox/
    chrome/
    edge/
```

---

## 🎯 결론 1: WebDriverAdapter 유지 권장

### ✅ 권장: WebDriverAdapter (현재 이름 유지)

**이유:**
1. **충돌 방지**: selenium.webdriver와 명확히 구분
2. **패턴 명시**: "Adapter" 접미사로 역할 명확
3. **일관성**: ImageLoad도 "Load" 접미사 사용
4. **명확성**: "WebDriver를 감싸는 Adapter"임을 즉시 알 수 있음

**다른 라이브러리 사례:**
```python
# requests 라이브러리
requests.Session  # ← Session (직접)
requests.adapters.HTTPAdapter  # ← Adapter 접미사

# SQLAlchemy
sqlalchemy.engine.Engine  # ← Engine (직접)
sqlalchemy.engine.Connectable  # ← 인터페이스

# 우리 프로젝트
ImageLoad  # ← Load 접미사
WebDriverAdapter  # ← Adapter 접미사 (일관성)
```

---

## 🔍 2. FirefoxSpecificConfig → FirefoxPolicy 네이밍 검토

### 현재 구조
```python
class FirefoxSpecificConfig(BaseModel):
    """Firefox 전용 설정"""
    binary_path: Optional[Path]
    profile_path: Optional[Path]
    # ...

class WebDriverPolicy(BaseModel):
    """통합 WebDriver 정책"""
    firefox: Optional[FirefoxSpecificConfig]
    chrome: Optional[ChromeSpecificConfig]
    edge: Optional[EdgeSpecificConfig]
```

### 제안 1: FirefoxPolicy (간결)
```python
class FirefoxPolicy(BaseModel):
    """Firefox 전용 정책"""
    binary_path: Optional[Path]
    profile_path: Optional[Path]
    # ...

class WebDriverPolicy(BaseModel):
    """통합 WebDriver 정책"""
    firefox: Optional[FirefoxPolicy]  # ← 간결
    chrome: Optional[ChromePolicy]
    edge: Optional[EdgePolicy]
```

**장점:**
- ✅ 간결함
- ✅ "Policy" 접미사로 일관성
- ✅ 타이핑 감소

**단점:**
- ⚠️ WebDriverPolicy와 혼동 가능 (둘 다 Policy)
- ⚠️ "Firefox의 무엇에 대한 Policy?"가 불명확

### 제안 2: FirefoxConfig (현재 유사)
```python
class FirefoxConfig(BaseModel):
    """Firefox 전용 설정"""
    binary_path: Optional[Path]
    profile_path: Optional[Path]
    # ...

class WebDriverPolicy(BaseModel):
    """통합 WebDriver 정책"""
    firefox: Optional[FirefoxConfig]  # ← Config
    chrome: Optional[ChromeConfig]
    edge: Optional[EdgeConfig]
```

**장점:**
- ✅ "Config" = 설정값 모음 (명확)
- ✅ Policy vs Config 구분 (Policy가 Config를 포함)
- ✅ 다른 프로젝트에서도 흔한 패턴

**단점:**
- ⚠️ "Specific"이 없어서 "일반 Config"처럼 보일 수 있음

### 제안 3: FirefoxOptions (Selenium 패턴)
```python
class FirefoxOptions(BaseModel):
    """Firefox 전용 옵션"""
    binary_path: Optional[Path]
    profile_path: Optional[Path]
    # ...

class WebDriverPolicy(BaseModel):
    """통합 WebDriver 정책"""
    firefox: Optional[FirefoxOptions]  # ← Options (Selenium 스타일)
    chrome: Optional[ChromeOptions]
    edge: Optional[EdgeOptions]
```

**장점:**
- ✅ Selenium과 유사 (selenium.webdriver.firefox.options.Options)
- ✅ "Options" = 브라우저 옵션 (직관적)

**단점:**
- ⚠️ Selenium의 Options와 혼동 가능
- ⚠️ 우리는 Selenium Options를 감싸는 상위 레벨

---

## 🎯 결론 2: 최종 권장 네이밍

### ✅ 최종 권장: FirefoxConfig (Specific 제거, Config 유지)

```python
# provider/policy.py

class FirefoxConfig(BaseModel):
    """Firefox WebDriver 설정"""
    binary_path: Optional[Path] = Field(None, description="Firefox binary path")
    profile_path: Optional[Path] = Field(None, description="Firefox profile path")
    driver_path: Optional[Path] = Field(None, description="Geckodriver path")
    # ...

class ChromeConfig(BaseModel):
    """Chrome WebDriver 설정"""
    binary_path: Optional[Path] = Field(None, description="Chrome binary path")
    user_data_dir: Optional[Path] = Field(None, description="Chrome user data dir")
    driver_path: Optional[Path] = Field(None, description="Chromedriver path")
    # ...

class EdgeConfig(BaseModel):
    """Edge WebDriver 설정"""
    binary_path: Optional[Path] = Field(None, description="Edge binary path")
    user_data_dir: Optional[Path] = Field(None, description="Edge user data dir")
    driver_path: Optional[Path] = Field(None, description="EdgeDriver path")
    # ...

class WebDriverPolicy(BaseModel):
    """통합 WebDriver 정책 (모든 브라우저 지원)"""
    name: str = Field(default="webdriver")
    provider: ProviderType = Field(default="firefox")
    
    # 브라우저별 설정
    firefox: Optional[FirefoxConfig] = Field(None, description="Firefox config")
    chrome: Optional[ChromeConfig] = Field(None, description="Chrome config")
    edge: Optional[EdgeConfig] = Field(None, description="Edge config")
```

**이유:**
1. **명확성**: Config = 설정값 모음 (명확한 의미)
2. **구분**: Policy (정책) > Config (설정) 계층 구조
3. **간결성**: Specific 제거로 타이핑 감소
4. **일관성**: 다른 프로젝트에서도 흔한 패턴 (XxxConfig)

---

## 📊 다른 라이브러리 사례 비교

### Pydantic
```python
class DatabaseConfig(BaseModel):
    host: str
    port: int

class AppSettings(BaseModel):
    database: DatabaseConfig  # ← XxxConfig 패턴
```

### Django
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'mydb',
        # ...
    }
}
# ← XxxxConfig 개념
```

### FastAPI
```python
class Settings(BaseSettings):
    app_name: str
    database_url: str
    
class DatabaseConfig(BaseModel):
    url: str
    pool_size: int
```

### Selenium (참고용)
```python
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions

# ← Options 패턴 (하지만 우리는 Options를 감싸는 상위 레벨)
```

---

## 🎯 최종 권장 사항

### 1. Class 이름
```python
# ❌ 변경 안 함
WebDriverAdapter  # ← 유지 (selenium.webdriver와 충돌 방지)

# ✅ 변경
FirefoxSpecificConfig → FirefoxConfig
ChromeSpecificConfig → ChromeConfig
EdgeSpecificConfig → EdgeConfig
```

### 2. 이유
```
WebDriverAdapter:
  - selenium.webdriver와 이름 충돌 방지
  - Adapter 패턴 명시
  - ImageLoad와 일관성 (접미사 사용)

FirefoxConfig (Specific 제거):
  - 간결함 (Specific 불필요)
  - Config = 설정값 (명확한 의미)
  - Policy vs Config 계층 구조
```

### 3. 사용 예시
```python
# Import
from crawl_utils.adapter import WebDriverAdapter
from crawl_utils.provider.policy import (
    WebDriverPolicy,
    FirefoxConfig,
    ChromeConfig,
    EdgeConfig,
)

# 사용
policy = WebDriverPolicy(
    provider="firefox",
    firefox=FirefoxConfig(
        profile_path="M:/Firefox_Profile/CRAWL_CHINA",
        driver_path="M:/WebDriver/geckodriver_win32.exe"
    )
)

adapter = WebDriverAdapter(policy)
```

---

## 📝 변경 요약

### ✅ 권장 변경
```python
# Before
class FirefoxSpecificConfig(BaseModel): ...
class ChromeSpecificConfig(BaseModel): ...
class EdgeSpecificConfig(BaseModel): ...

# After
class FirefoxConfig(BaseModel): ...
class ChromeConfig(BaseModel): ...
class EdgeConfig(BaseModel): ...
```

### ❌ 변경 안 함
```python
# 유지
class WebDriverAdapter: ...  # ← selenium.webdriver와 충돌 방지
```

---

## 🎉 결론

1. **WebDriverAdapter → WebDriver**: ❌ 변경 안 함 (충돌 위험)
2. **XxxSpecificConfig → XxxConfig**: ✅ 변경 권장 (간결함, 명확성)

**최종 구조:**
```
WebDriverAdapter (Adapter)
  └─ WebDriverPolicy (Policy)
      ├─ FirefoxConfig (Config)
      ├─ ChromeConfig (Config)
      └─ EdgeConfig (Config)
```

이 구조는:
- ✅ 충돌 없음
- ✅ 계층 구조 명확
- ✅ 간결하고 명확
- ✅ 다른 라이브러리 패턴과 일치
