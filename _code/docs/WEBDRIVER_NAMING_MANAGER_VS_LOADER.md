# WebDriver 클래스명 최종 검토: Adapter vs Manager vs Loader

## 📅 검토 날짜: 2025-10-23

---

## 🎯 검토 대상 이름

1. **WebDriverAdapter** (현재)
2. **WebDriverManager** (제안 1)
3. **WebDriverLoader** (제안 2)

---

## 🔍 1. 각 이름의 의미와 패턴

### WebDriverAdapter (현재)

**의미:**
- **Adapter Pattern**: 기존 인터페이스를 다른 인터페이스로 변환
- WebDriver를 사용하기 쉽게 감싸는 래퍼

**장점:**
- ✅ GoF 디자인 패턴 명확히 표현
- ✅ "설정 로딩 + WebDriver 선택 + 인터페이스 제공" 역할 명확
- ✅ ImageLoad와 일관성 (둘 다 "무언가를 로드/적응하는" 역할)

**단점:**
- ⚠️ Adapter 패턴이 정확한가? (실제로는 Factory + Facade에 가까움)
- ⚠️ "Adapter"가 너무 기술적

**실제 패턴:**
```python
# Adapter 패턴 (인터페이스 변환)
class WebDriverAdapter:
    def __init__(self, cfg_like):
        self.config = load_config()
        self._webdriver = create_webdriver()  # Factory
    
    def start(self):
        self._webdriver.start()  # Delegation (Facade)
    
    @property
    def driver(self):
        return self._webdriver.driver  # Delegation
```
→ **Factory + Facade + Context Manager 복합 패턴**

---

### WebDriverManager (제안 1)

**의미:**
- **Manager Pattern**: 리소스의 생명주기 관리
- WebDriver의 생성, 시작, 종료를 관리

**장점:**
- ✅ 역할 명확: "WebDriver를 관리한다"
- ✅ Context Manager 역할과 잘 맞음 (`__enter__`, `__exit__`)
- ✅ 직관적 (기술적이지 않음)
- ✅ 다른 라이브러리에서도 흔한 패턴

**단점:**
- ⚠️ 기존 라이브러리와 충돌 가능성?

**다른 라이브러리 사례:**
```python
# webdriver-manager (PyPI)
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.chrome import ChromeDriverManager
# ← 드라이버 다운로드/업데이트 관리

# 우리 프로젝트
class WebDriverManager:
    """WebDriver 생명주기 관리"""
    def start(self): ...
    def quit(self): ...
    def __enter__(self): ...
    def __exit__(self): ...
```

**충돌 위험:**
```python
# ❌ 이름 충돌 가능
from webdriver_manager.firefox import GeckoDriverManager
from crawl_utils.adapter import WebDriverManager

# ← GeckoDriverManager vs WebDriverManager (혼동 가능)
```

**해결책:**
- 우리는 `WebDriverManager` (전체 WebDriver 관리)
- webdriver-manager는 `XxxDriverManager` (특정 드라이버만)
- → 실제 충돌은 적음 (용도가 다름)

---

### WebDriverLoader (제안 2)

**의미:**
- **Loader Pattern**: 설정을 로드하고 WebDriver를 준비
- ImageLoad와 명확한 일관성

**장점:**
- ✅ ImageLoad와 100% 패턴 일치
- ✅ "설정 로드 + WebDriver 로드" 역할 명확
- ✅ 학습 비용 감소 (ImageLoad와 동일한 패턴)
- ✅ 충돌 위험 거의 없음

**단점:**
- ⚠️ "Loader"가 "설정만 로드"하는 것처럼 보일 수 있음
- ⚠️ Context Manager 역할이 명확하지 않음

**ImageLoad와 비교:**
```python
# image_utils/adapter/load.py
class ImageLoad:
    """이미지 로드 및 처리"""
    def __init__(self, cfg_like, ...): ...
    def run(self, source): ...  # 이미지 처리

# crawl_utils/adapter/webdriver.py
class WebDriverLoader:
    """WebDriver 로드 및 관리"""
    def __init__(self, cfg_like, ...): ...
    def start(self): ...  # WebDriver 시작
    def quit(self): ...  # WebDriver 종료
    
    # ImageLoad는 run(), WebDriverLoader는 start/quit
    # ← 메서드명이 다름 (패턴 불일치)
```

---

## 📊 2. 패턴별 비교

### 실제 역할 분석
```python
class WebDriverXxx:
    """
    역할:
    1. 설정 로드 (ConfigLikeLoader)  ← Loader
    2. WebDriver 생성 (Factory)       ← Factory
    3. WebDriver 선택 (provider 기반) ← Factory
    4. 생명주기 관리 (start/quit)     ← Manager
    5. Context Manager (__enter__/__exit__) ← Manager
    6. WebDriver 접근 (driver property) ← Facade
    """
```

**가장 가까운 패턴:**
- **Manager** (생명주기 관리가 핵심)
- Factory + Facade (부가적 역할)

---

## 🎯 3. 다른 라이브러리 사례 분석

### SQLAlchemy
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Engine (생성)
engine = create_engine("postgresql://...")

# SessionMaker (팩토리)
SessionMaker = sessionmaker(bind=engine)

# Session (관리)
with SessionMaker() as session:  # Context Manager
    session.add(user)
    session.commit()
```
→ **Session** = Manager 역할

### requests
```python
import requests

# Session (관리)
with requests.Session() as session:  # Context Manager
    session.get("https://...")
    session.post("https://...")
```
→ **Session** = Manager 역할

### Selenium
```python
from selenium import webdriver

# WebDriver (직접 생성 + 관리)
driver = webdriver.Firefox()
driver.get("https://...")
driver.quit()

# ← Manager 없음 (직접 관리)
```

### Django
```python
# ConnectionHandler (Manager)
from django.db import connections

connection = connections['default']
cursor = connection.cursor()
```
→ **ConnectionHandler** = Manager

### 우리 프로젝트
```python
# logs_utils
from logs_utils import LogManager  # ← Manager

log_manager = LogManager(config)
logger = log_manager.logger
```
→ **LogManager** 이미 사용 중!

---

## 🎯 4. 최종 권장: WebDriverManager

### ✅ WebDriverManager 권장 이유

**1. 역할 정확성**
```python
class WebDriverManager:
    """WebDriver 생명주기 관리"""
    def start(self): ...  # 시작
    def quit(self): ...   # 종료
    def __enter__(self): ...  # Context Manager 진입
    def __exit__(self): ...   # Context Manager 종료
```
→ **Manager 패턴 정확히 표현**

**2. 프로젝트 일관성**
```python
# 우리 프로젝트에서 이미 사용 중
from logs_utils import LogManager
from crawl_utils.adapter import WebDriverManager

# 일관된 네이밍
log_manager = LogManager(config)
webdriver_manager = WebDriverManager(config)
```

**3. 직관성**
```python
# ✅ 직관적
with WebDriverManager("configs/webdriver.yaml") as manager:
    manager.driver.get("https://google.com")

# ⚠️ 덜 직관적
with WebDriverAdapter("configs/webdriver.yaml") as adapter:
    adapter.driver.get("https://google.com")

# ⚠️ 혼동 가능
with WebDriverLoader("configs/webdriver.yaml") as loader:
    loader.driver.get("https://google.com")  # Loader인데 driver?
```

**4. Context Manager 명확성**
```python
# Manager = 리소스 관리
with WebDriverManager(...) as manager:
    # manager가 WebDriver 생명주기 관리
    pass

# Adapter = 인터페이스 변환?
with WebDriverAdapter(...) as adapter:
    # adapter가 무엇을 adapt?
    pass

# Loader = 로딩?
with WebDriverLoader(...) as loader:
    # loader가 로딩 후 무엇?
    pass
```

---

## 📊 5. 충돌 위험 재검토

### webdriver-manager (PyPI) 라이브러리
```python
# webdriver-manager 라이브러리 (드라이버 다운로드/업데이트)
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.chrome import ChromeDriverManager

service = Service(GeckoDriverManager().install())
driver = webdriver.Firefox(service=service)
```

**충돌 가능성:**
```python
# ❌ 직접 충돌 (import 이름이 다름)
from webdriver_manager.firefox import GeckoDriverManager
from crawl_utils.adapter import WebDriverManager
# ← GeckoDriverManager ≠ WebDriverManager (충돌 없음)

# ✅ 함께 사용 가능
from webdriver_manager.firefox import GeckoDriverManager
from crawl_utils.adapter import WebDriverManager

# webdriver-manager: 드라이버 다운로드
driver_path = GeckoDriverManager().install()

# 우리: WebDriver 생명주기 관리
with WebDriverManager({
    "firefox": {"driver_path": driver_path}
}) as manager:
    manager.driver.get("https://google.com")
```

**결론: 충돌 없음** (용도가 다름, 함께 사용 가능)

---

## 🎯 6. ImageLoad와의 일관성 검토

### ImageLoad 패턴
```python
class ImageLoad:
    """이미지 로드 및 처리"""
    def __init__(self, cfg_like, log_manager=None): ...
    def run(self, source: Image | Path): ...  # 실행 메서드
```

### WebDriverManager 패턴
```python
class WebDriverManager:
    """WebDriver 생명주기 관리"""
    def __init__(self, cfg_like, log_manager=None): ...
    def start(self): ...  # 시작
    def quit(self): ...   # 종료
    def __enter__(self): ...  # Context Manager
```

**차이점:**
- ImageLoad: `run()` 메서드 (1회성 처리)
- WebDriverManager: `start()/quit()` + Context Manager (생명주기 관리)

**결론:**
- ImageLoad = **Processor** (이미지 처리)
- WebDriverManager = **Manager** (리소스 관리)
- → **역할이 다름, 이름도 달라야 함**

---

## 🎯 7. 최종 권장 사항

### ✅ 권장: WebDriverManager

**이유:**
1. ✅ 역할 정확: 생명주기 관리 (start/quit/context manager)
2. ✅ 프로젝트 일관성: LogManager와 패턴 일치
3. ✅ 직관적: "WebDriver를 관리한다"
4. ✅ 충돌 없음: webdriver-manager와 용도가 다름
5. ✅ Context Manager 역할 명확

### 변경 사항
```python
# Before
from crawl_utils.adapter import WebDriverAdapter

with WebDriverAdapter("configs/webdriver.yaml") as adapter:
    adapter.driver.get("https://google.com")

# After
from crawl_utils.adapter import WebDriverManager

with WebDriverManager("configs/webdriver.yaml") as manager:
    manager.driver.get("https://google.com")
```

### 파일 구조 (변경 없음)
```
crawl_utils/
├─ adapter/
│  ├─ webdriver.py  # WebDriverManager (이름만 변경)
│  └─ crawl.py
│
├─ provider/
│  ├─ firefox.py
│  └─ policy.py
```

---

## 📝 8. 네이밍 최종 정리

### Class 이름 변경
```python
# ✅ 변경
WebDriverAdapter → WebDriverManager

# ✅ 변경
FirefoxSpecificConfig → FirefoxConfig
ChromeSpecificConfig → ChromeConfig
EdgeSpecificConfig → EdgeConfig

# ❌ 변경 안 함
WebDriverPolicy  # ← 유지
```

### 최종 구조
```python
# adapter/webdriver.py
class WebDriverManager:
    """WebDriver 생명주기 관리"""
    ...

# provider/policy.py
class FirefoxConfig(BaseModel):
    """Firefox 설정"""
    ...

class ChromeConfig(BaseModel):
    """Chrome 설정"""
    ...

class EdgeConfig(BaseModel):
    """Edge 설정"""
    ...

class WebDriverPolicy(BaseModel):
    """통합 WebDriver 정책"""
    firefox: Optional[FirefoxConfig]
    chrome: Optional[ChromeConfig]
    edge: Optional[EdgeConfig]
```

---

## 🎉 결론

### 최종 권장
1. **WebDriverAdapter → WebDriverManager** ✅
2. **XxxSpecificConfig → XxxConfig** ✅

### 이유
- **Manager**: 생명주기 관리 역할 명확
- **Config**: 간결하고 자연스러움
- **일관성**: LogManager와 패턴 일치
- **직관성**: 역할이 명확히 드러남

변경하시겠습니까?
