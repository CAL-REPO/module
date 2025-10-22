# 🚨 WebDriver 구조 문제점 및 개선안

## 📋 현재 구조의 문제점

### 1️⃣ FirefoxWebDriver의 역할 혼재

**현재 (문제):**
```python
# firefox.py
class FirefoxWebDriver(BaseWebDriver[WebDriverPolicy]):
    def _load_config(self, cfg_like, **overrides):
        return ConfigLikeLoader.load_with_caller_path(
            cfg_like=cfg_like,
            policy_class=WebDriverPolicy,
            caller_file=__file__,
            default_config_filename="firefox.yaml",  # ❌ 하드코딩!
            **overrides
        )
```

**문제점:**
- ❌ `FirefoxWebDriver`가 설정 로딩 책임을 가짐
- ❌ `default_config_filename="firefox.yaml"` 하드코딩
- ❌ WebDriverPolicy는 `webdriver`, `webdriver_china`, `webdriver_global` 등 여러 섹션을 가질 수 있는데, 항상 `firefox.yaml`만 참조
- ❌ YAML 파일의 섹션명(`webdriver`, `webdriver_china`)을 인식하지 못함

---

## 🎯 올바른 구조 (ImageLoad + Translate 패턴)

### ImageLoad/Translate 패턴 분석

```
1. Translate (Adapter) - 설정 로딩 + 실행 오케스트레이션
   - TranslatePolicy 로드 (ConfigLikeLoader 사용)
   - Translator (실제 번역 엔진) 호출
   
2. Translator (Provider/Engine) - 순수 비즈니스 로직
   - API 호출, 번역 처리
   - 설정은 Translate에서 전달받음
```

### WebDriver에 적용

```
1. WebDriverAdapter (Adapter) - 설정 로딩 + WebDriver 선택/실행
   - WebDriverPolicy 로드 (ConfigLikeLoader 사용)
   - provider 필드에 따라 FirefoxWebDriver/ChromeWebDriver 선택
   - Context Manager 지원
   
2. FirefoxWebDriver (Provider/Engine) - 순수 WebDriver 로직
   - Firefox 전용 WebDriver 생성/관리
   - WebDriverPolicy를 생성자에서 받음 (로딩 책임 없음)
```

---

## 🏗️ 개선안 설계

### 구조 1: WebDriverAdapter (권장)

```
crawl_utils/
├── adapter/
│   ├── webdriver.py          ← ✨ NEW: WebDriver Adapter (설정 로딩 + 실행)
│   ├── firefox.py             ← 수정: FirefoxWebDriver (순수 WebDriver 로직)
│   └── chrome.py              ← 미래: ChromeWebDriver
├── provider/
│   ├── base.py                ← 수정: BaseWebDriver 간소화
│   └── factory.py             ← 수정: create_webdriver 로직 이동
└── configs/
    ├── webdriver.yaml         ← section: webdriver
    ├── webdriver_china.yaml   ← section: webdriver_china
    └── webdriver_global.yaml  ← section: webdriver_global
```

---

## 📝 상세 설계

### 1. WebDriverAdapter (adapter/webdriver.py)

```python
# -*- coding: utf-8 -*-
# crawl_utils/adapter/webdriver.py
# WebDriver Adapter - ImageLoad 패턴

from __future__ import annotations
from pathlib import Path
from typing import Any, Union, Optional
from pydantic import BaseModel

from cfg_utils.services import ConfigLikeLoader
from crawl_utils.core.policy import WebDriverPolicy
from crawl_utils.adapter.firefox import FirefoxWebDriver
# from crawl_utils.adapter.chrome import ChromeWebDriver  # 미래


class WebDriverAdapter:
    """WebDriver Adapter (ImageLoad 패턴)
    
    책임:
    1. WebDriverPolicy 로드 (ConfigLikeLoader 사용)
    2. provider 필드에 따라 적절한 WebDriver 선택
    3. Context Manager 지원
    
    Example:
        >>> # YAML 파일에서 로드 (자동으로 webdriver 섹션 인식)
        >>> adapter = WebDriverAdapter("configs/webdriver_china.yaml")
        >>> with adapter:
        ...     adapter.driver.get("https://taobao.com")
        
        >>> # dict로 직접 설정
        >>> adapter = WebDriverAdapter({
        ...     "provider": "firefox",
        ...     "region": "china",
        ...     "firefox": {...}
        ... })
    """
    
    def __init__(
        self,
        cfg_like: Union[BaseModel, Path, str, dict, None] = None,
        **overrides: Any
    ):
        """WebDriverAdapter 초기화
        
        Args:
            cfg_like: WebDriverPolicy, YAML 경로, dict 등
            **overrides: 런타임 오버라이드
        """
        # 1. ConfigLikeLoader로 WebDriverPolicy 로드
        self.config = self._load_config(cfg_like, **overrides)
        
        # 2. provider에 따라 WebDriver 선택
        self._webdriver = self._create_webdriver()
    
    def _load_config(
        self,
        cfg_like: Union[BaseModel, Path, str, dict, None],
        **overrides: Any
    ) -> WebDriverPolicy:
        """WebDriverPolicy 로드
        
        Args:
            cfg_like: 설정 소스
            **overrides: 런타임 오버라이드
        
        Returns:
            로드된 WebDriverPolicy 인스턴스
        """
        return ConfigLikeLoader.load_with_caller_path(
            cfg_like=cfg_like,
            policy_class=WebDriverPolicy,
            caller_file=__file__,
            default_config_filename="webdriver.yaml",  # ✅ 기본값만 지정
            **overrides
        )
    
    def _create_webdriver(self):
        """provider에 따라 WebDriver 생성"""
        provider = self.config.provider.lower()
        
        if provider == "firefox":
            return FirefoxWebDriver(self.config)  # ✅ Policy 전달
        elif provider == "chrome":
            # return ChromeWebDriver(self.config)
            raise NotImplementedError("Chrome WebDriver not implemented yet")
        elif provider == "edge":
            # return EdgeWebDriver(self.config)
            raise NotImplementedError("Edge WebDriver not implemented yet")
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    @property
    def driver(self):
        """Selenium WebDriver 인스턴스"""
        return self._webdriver.driver
    
    # Context Manager 지원
    def __enter__(self):
        """with 문 진입"""
        self._webdriver.start()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        """with 문 종료"""
        self._webdriver.quit()
        return False
    
    def start(self):
        """WebDriver 시작"""
        self._webdriver.start()
    
    def quit(self):
        """WebDriver 종료"""
        self._webdriver.quit()
```

---

### 2. FirefoxWebDriver (adapter/firefox.py) - 간소화

```python
# -*- coding: utf-8 -*-
# crawl_utils/adapter/firefox.py
# Firefox WebDriver - Pure Logic

from __future__ import annotations
import shutil
from typing import Optional
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

from crawl_utils.core.policy import WebDriverPolicy
from logs_utils import setup_logger


class FirefoxWebDriver:
    """Firefox WebDriver 순수 로직
    
    책임:
    1. Firefox WebDriver 생성/관리
    2. Firefox 전용 옵션 설정
    
    설정 로딩 책임 없음! (WebDriverAdapter가 처리)
    
    Example:
        >>> from crawl_utils.core.policy import WebDriverPolicy
        >>> policy = WebDriverPolicy(provider="firefox", firefox={...})
        >>> driver = FirefoxWebDriver(policy)
        >>> driver.start()
        >>> driver.driver.get("https://example.com")
        >>> driver.quit()
    """
    
    def __init__(self, config: WebDriverPolicy):
        """FirefoxWebDriver 초기화
        
        Args:
            config: WebDriverPolicy 인스턴스 (이미 로드됨!)
        """
        # Validation: Firefox 설정 확인
        if not config.firefox:
            raise ValueError(
                "Firefox configuration is required. "
                "Add 'firefox:' section to your WebDriverPolicy."
            )
        
        self.config = config
        self._driver: Optional[webdriver.Firefox] = None
        
        # 로거 초기화
        self.logger = setup_logger(
            name=f"FirefoxWebDriver_{config.region}",
            log_config=config.log_config
        ) if config.log_config else setup_logger("FirefoxWebDriver")
    
    def start(self):
        """WebDriver 시작"""
        if self._driver is None:
            opts = self._configure_options()
            exe = self._get_driver_path()
            
            self.logger.info(f"Launching Firefox WebDriver (region={self.config.region})")
            self._driver = webdriver.Firefox(
                service=Service(executable_path=exe),
                options=opts
            )
    
    def quit(self):
        """WebDriver 종료"""
        if self._driver:
            self._driver.quit()
            self._driver = None
            self.logger.info("Firefox WebDriver closed")
    
    @property
    def driver(self) -> webdriver.Firefox:
        """Selenium WebDriver 인스턴스"""
        if self._driver is None:
            raise RuntimeError(
                "WebDriver not started. Call start() first or use context manager."
            )
        return self._driver
    
    def _configure_options(self) -> Options:
        """Firefox 옵션 설정"""
        cfg = self.config
        opts = Options()
        
        # Binary path
        if cfg.firefox.binary_path:
            opts.binary_location = str(cfg.firefox.binary_path)
        
        # Profile path
        if cfg.firefox.profile_path:
            opts.add_argument("-profile")
            opts.add_argument(str(cfg.firefox.profile_path))
        
        # Headless
        if cfg.headless:
            opts.add_argument("--headless")
        
        # Window size
        if cfg.window_size:
            w, h = cfg.window_size
            opts.add_argument(f"--width={w}")
            opts.add_argument(f"--height={h}")
        
        # Accept-Language
        if cfg.accept_languages:
            opts.set_preference("intl.accept_languages", cfg.accept_languages)
        
        # User-Agent
        if cfg.user_agent:
            opts.set_preference("general.useragent.override", cfg.user_agent)
        
        # Anti-Detection
        if cfg.disable_automation:
            opts.set_preference("dom.webdriver.enabled", False)
        else:
            opts.set_preference("dom.webdriver.enabled", cfg.firefox.dom_enabled)
        
        opts.set_preference(
            "privacy.resistFingerprinting",
            cfg.firefox.resist_fingerprint_enabled
        )
        
        return opts
    
    def _get_driver_path(self) -> str:
        """GeckoDriver 경로 확인"""
        # 1. 명시적 경로
        if self.config.firefox.driver_path:
            return str(self.config.firefox.driver_path)
        
        # 2. 시스템 PATH
        if shutil.which("geckodriver"):
            return "geckodriver"
        
        # 3. webdriver-manager
        if self.config.firefox.use_webdriver_manager:
            try:
                from webdriver_manager.firefox import GeckoDriverManager
                return GeckoDriverManager().install()
            except ImportError:
                self.logger.warning("webdriver-manager not installed")
                return "geckodriver"
        
        return "geckodriver"
```

---

### 3. BaseWebDriver (provider/base.py) - 삭제 또는 간소화

**옵션 A: 완전 삭제 (권장)**
- FirefoxWebDriver, ChromeWebDriver가 독립적으로 동작
- WebDriverAdapter가 Context Manager 제공

**옵션 B: 인터페이스만 유지**
```python
from abc import ABC, abstractmethod

class IWebDriver(ABC):
    """WebDriver 인터페이스"""
    
    @abstractmethod
    def start(self):
        """WebDriver 시작"""
        pass
    
    @abstractmethod
    def quit(self):
        """WebDriver 종료"""
        pass
    
    @property
    @abstractmethod
    def driver(self):
        """Selenium WebDriver 인스턴스"""
        pass
```

---

### 4. 사용 예시

#### 방법 1: WebDriverAdapter 사용 (권장)

```python
from crawl_utils.adapter.webdriver import WebDriverAdapter

# YAML 파일에서 로드 (자동으로 webdriver_china 섹션 인식)
with WebDriverAdapter("configs/webdriver_china.yaml") as driver:
    driver.driver.get("https://taobao.com")
    print(driver.driver.title)

# dict로 직접 설정
adapter = WebDriverAdapter({
    "provider": "firefox",
    "region": "china",
    "firefox": {
        "profile_path": "M:/Firefox_Profile/CRAWL_CHINA",
        "use_webdriver_manager": True
    }
})
adapter.start()
adapter.driver.get("https://taobao.com")
adapter.quit()
```

#### 방법 2: FirefoxWebDriver 직접 사용

```python
from crawl_utils.adapter.firefox import FirefoxWebDriver
from crawl_utils.core.policy import WebDriverPolicy, FirefoxSpecificConfig

# Policy 생성
policy = WebDriverPolicy(
    provider="firefox",
    region="china",
    firefox=FirefoxSpecificConfig(
        profile_path="M:/Firefox_Profile/CRAWL_CHINA"
    )
)

# WebDriver 사용
driver = FirefoxWebDriver(policy)
driver.start()
driver.driver.get("https://taobao.com")
driver.quit()
```

---

## 📊 변경 사항 요약

| 파일 | 변경 내용 | 책임 |
|------|-----------|------|
| **adapter/webdriver.py** | ✨ 신규 생성 | ConfigLoader + provider 선택 + Context Manager |
| **adapter/firefox.py** | 🔧 간소화 | 순수 Firefox WebDriver 로직 (설정 로딩 제거) |
| **provider/base.py** | ❌ 삭제 또는 간소화 | 불필요 (WebDriverAdapter가 대체) |
| **provider/factory.py** | ❌ 삭제 | WebDriverAdapter._create_webdriver()가 대체 |

---

## ✅ 개선 효과

### 1. 단일 책임 원칙 (SRP)
- **WebDriverAdapter**: 설정 로딩 + WebDriver 선택
- **FirefoxWebDriver**: Firefox WebDriver 로직만

### 2. ImageLoad 패턴 일관성
```
Translate (Adapter) → Translator (Provider)
WebDriverAdapter → FirefoxWebDriver
```

### 3. 유연성
- YAML 파일의 모든 섹션 지원 (`webdriver`, `webdriver_china`, `webdriver_global`)
- provider 필드로 Firefox/Chrome/Edge 자동 선택

### 4. 간결성
- FirefoxWebDriver에서 ConfigLikeLoader 제거
- 생성자에서 WebDriverPolicy만 받음

---

## 🚀 마이그레이션 계획

### Phase 1: WebDriverAdapter 생성
1. `adapter/webdriver.py` 생성
2. ConfigLikeLoader.load_with_caller_path 사용
3. provider 기반 WebDriver 선택 로직

### Phase 2: FirefoxWebDriver 간소화
1. `_load_config()` 메서드 삭제
2. 생성자에서 WebDriverPolicy 받음
3. BaseWebDriver 상속 제거

### Phase 3: BaseWebDriver 정리
1. `provider/base.py` 삭제 또는 간소화
2. `provider/factory.py` 삭제

### Phase 4: 테스트 및 검증
1. 기존 코드 호환성 확인
2. 3개 YAML 파일 테스트
3. Context Manager 동작 확인

---

## 💡 결론

**현재 문제:**
- FirefoxWebDriver가 설정 로딩 + WebDriver 로직 혼재
- `default_config_filename="firefox.yaml"` 하드코딩
- YAML 섹션명 무시

**해결책:**
- **WebDriverAdapter** 도입 (설정 로딩 + provider 선택)
- **FirefoxWebDriver** 간소화 (순수 WebDriver 로직)
- **ImageLoad 패턴** 일관성 유지

**다음 단계:**
사용자 승인 후 단계별 구현 진행
