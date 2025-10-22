# FirefoxWebDriver vs ImageLoad 비교 분석

## 📊 구조 비교

### 공통점

| 항목 | FirefoxWebDriver | ImageLoad |
|------|------------------|-----------|
| **패턴** | Adapter 패턴 | Adapter 패턴 (Translate) |
| **cfg_like** | ✅ 지원 | ✅ 지원 |
| **Policy 클래스** | FirefoxPolicy | ImageLoadPolicy |
| **ConfigLikeLoader** | ✅ 사용 | ✅ 사용 |
| **LogManager** | ✅ 사용 (상속) | ✅ 사용 |

---

## 🔍 상세 비교

### 1. 클래스 구조

#### FirefoxWebDriver
```python
class FirefoxWebDriver(BaseWebDriver[FirefoxPolicy]):
    """Firefox WebDriver 구현체
    
    BaseWebDriver를 상속받아 Firefox 전용 WebDriver 구현
    ConfigLoader 패턴을 따름
    """
    
    def _load_config(self, cfg_like, **overrides) -> FirefoxPolicy:
        """FirefoxPolicy 로드"""
        ...
    
    def _create_driver(self) -> webdriver.Firefox:
        """Firefox WebDriver 인스턴스 생성"""
        ...
    
    def _configure_options(self) -> Options:
        """Firefox 옵션 설정"""
        ...
```

**특징:**
- ✅ BaseWebDriver 상속 (Generic Type)
- ✅ Context Manager 지원 (__enter__, __exit__)
- ✅ Abstract Method 구현 (_load_config, _create_driver)

---

#### ImageLoad
```python
class ImageLoad:
    """Image processing adapter following Translate pattern.
    
    Policy and __init__: NO source
    run(): receives Image object OR file path
    """
    
    def __init__(self, cfg_like, *, log_manager=None, **overrides):
        """Initialize ImageLoad adapter."""
        self.policy = self._load_config(cfg_like, **overrides)
        ...
    
    def _load_config(self, cfg_like, **overrides) -> ImageLoadPolicy:
        """Load ImageLoadPolicy."""
        ...
    
    def run(self, source) -> Dict[str, Any]:
        """Process image."""
        ...
```

**특징:**
- ❌ 상속 없음 (Standalone)
- ❌ Context Manager 미지원
- ✅ run() 메서드로 처리 수행

---

### 2. ConfigLikeLoader 사용 방식

#### FirefoxWebDriver
```python
def _load_config(self, cfg_like, **overrides) -> FirefoxPolicy:
    # 1. Policy 인스턴스 직접 전달 체크
    if isinstance(cfg_like, FirefoxPolicy):
        if overrides:
            return cfg_like.model_copy(update=overrides)
        return cfg_like
    
    # 2. 기본 경로 계산
    default_path = Path(__file__).parent.parent / "configs" / "firefox.yaml"
    
    # 3. cfg_like 타입 변환 (Path → str)
    if cfg_like is None:
        cfg_source = str(default_path)
    elif isinstance(cfg_like, Path):
        cfg_source = str(cfg_like)
    elif isinstance(cfg_like, list):
        cfg_source = [str(item) if isinstance(item, Path) else item for item in cfg_like]
    else:
        cfg_source = cfg_like
    
    # 4. ConfigLikeLoader.load() 호출
    return ConfigLikeLoader.load(
        cfg_like=cfg_source,
        policy_class=FirefoxPolicy,
        default_config_path=str(default_path),  # ← default_config_path 사용
        **overrides
    )
```

**특징:**
- ✅ 수동 경로 계산 (parent.parent/configs/firefox.yaml)
- ✅ Path → str 변환 수동 처리
- ✅ `ConfigLikeLoader.load()` 사용
- ✅ `default_config_path` 매개변수 사용

---

#### ImageLoad
```python
def _load_config(self, cfg_like, **overrides) -> ImageLoadPolicy:
    return ConfigLikeLoader.load_with_caller_path(
        cfg_like=cfg_like,
        policy_class=ImageLoadPolicy,
        caller_file=__file__,               # ← __file__ 전달
        default_config_filename="image.yaml",  # ← 파일명만
        **overrides
    )
```

**특징:**
- ✅ 자동 경로 계산 (`load_with_caller_path`)
- ✅ Path 변환 자동 처리
- ✅ `caller_file=__file__` 전달
- ✅ `default_config_filename` 매개변수 사용 (파일명만)

---

### 3. 로깅 초기화

#### FirefoxWebDriver
```python
# BaseWebDriver에서 처리
class BaseWebDriver:
    def __init__(self, cfg_like, **overrides):
        self.config = self._load_config(cfg_like, **overrides)
        
        # LogManager는 BaseWebDriver에서 자동 초기화
        self.logger = ...  # 상속받은 클래스에서 사용
```

**특징:**
- ✅ BaseWebDriver가 자동 초기화
- ✅ self.logger로 접근

---

#### ImageLoad
```python
def __init__(self, cfg_like, *, log_manager=None, **overrides):
    self.policy = self._load_config(cfg_like, **overrides)
    
    # LogManager 수동 초기화
    if log_manager:
        self.log = log_manager.logger
    elif self.policy.log:
        self.log = LogManager(self.policy.log).logger
    else:
        self.log = LogManager({"enabled": False}).logger
    
    self.log.debug("ImageLoad initialized")
```

**특징:**
- ✅ 수동 초기화 필요
- ✅ log_manager 매개변수 지원
- ✅ self.log로 접근

---

### 4. 실행 패턴

#### FirefoxWebDriver
```python
# Context Manager 패턴
with FirefoxWebDriver("configs/firefox.yaml") as driver:
    driver.driver.get("https://example.com")
    # driver.driver = selenium.webdriver.Firefox 인스턴스

# 또는 수동 관리
driver = FirefoxWebDriver("configs/firefox.yaml")
driver.start()  # WebDriver 시작
driver.driver.get("https://example.com")
driver.quit()   # WebDriver 종료
```

**특징:**
- ✅ Context Manager 지원
- ✅ WebDriver 생명주기 관리
- ✅ self.driver로 Selenium WebDriver 접근

---

#### ImageLoad
```python
# run() 메서드 패턴
loader = ImageLoad("configs/image.yaml")

# 이미지 처리
result = loader.run(source="image.jpg")
# result = {
#     "success": True,
#     "image": PIL.Image,
#     "original_size": (width, height),
#     "processed_size": (width, height),
#     "processing": {...},
#     "error": None
# }
```

**특징:**
- ✅ run() 메서드로 처리
- ✅ source 매개변수 (Image 또는 경로)
- ✅ 결과 dict 반환
- ❌ Context Manager 미지원

---

## 🔥 주요 차이점

### 1. BaseWebDriver 상속 vs Standalone

| FirefoxWebDriver | ImageLoad |
|------------------|-----------|
| BaseWebDriver[FirefoxPolicy] 상속 | 상속 없음 |
| Abstract Method 구현 필요 | 자유로운 구조 |
| Context Manager 자동 지원 | Context Manager 미지원 |
| 통일된 WebDriver 인터페이스 | 독립적인 인터페이스 |

---

### 2. ConfigLikeLoader 사용

| FirefoxWebDriver | ImageLoad |
|------------------|-----------|
| `ConfigLikeLoader.load()` | `ConfigLikeLoader.load_with_caller_path()` |
| 수동 경로 계산 | 자동 경로 계산 |
| Path → str 변환 수동 | 변환 자동 |
| `default_config_path` 사용 | `default_config_filename` 사용 |
| 코드 복잡도 높음 | 코드 간결함 |

---

### 3. 로깅 초기화

| FirefoxWebDriver | ImageLoad |
|------------------|-----------|
| BaseWebDriver에서 자동 | 수동 초기화 필요 |
| self.logger 사용 | self.log 사용 |
| log_manager 매개변수 없음 | log_manager 매개변수 지원 |

---

### 4. 실행 패턴

| FirefoxWebDriver | ImageLoad |
|------------------|-----------|
| Context Manager 패턴 | run() 메서드 패턴 |
| WebDriver 생명주기 관리 | 단일 처리 수행 |
| start() / quit() | run(source) |
| 장시간 유지 가능 | 일회성 처리 |

---

## ✅ 개선 제안

### FirefoxWebDriver를 ImageLoad 패턴으로 개선

#### 1. ConfigLikeLoader 사용 간소화
```python
# Before (현재)
def _load_config(self, cfg_like, **overrides) -> FirefoxPolicy:
    if isinstance(cfg_like, FirefoxPolicy):
        if overrides:
            return cfg_like.model_copy(update=overrides)
        return cfg_like
    
    default_path = Path(__file__).parent.parent / "configs" / "firefox.yaml"
    
    if cfg_like is None:
        cfg_source = str(default_path)
    elif isinstance(cfg_like, Path):
        cfg_source = str(cfg_like)
    elif isinstance(cfg_like, list):
        cfg_source = [str(item) if isinstance(item, Path) else item for item in cfg_like]
    else:
        cfg_source = cfg_like
    
    return ConfigLikeLoader.load(
        cfg_like=cfg_source,
        policy_class=FirefoxPolicy,
        default_config_path=str(default_path),
        **overrides
    )

# After (개선)
def _load_config(self, cfg_like, **overrides) -> FirefoxPolicy:
    return ConfigLikeLoader.load_with_caller_path(
        cfg_like=cfg_like,
        policy_class=FirefoxPolicy,
        caller_file=__file__,
        default_config_filename="firefox.yaml",
        **overrides
    )
```

**개선 효과:**
- ✅ 코드 16줄 → 7줄 (57% 감소)
- ✅ Path 변환 자동 처리
- ✅ 경로 계산 자동화
- ✅ Policy 인스턴스 체크 자동 (ConfigLikeLoader 내부)

---

#### 2. 로깅 초기화 명확화
```python
# ImageLoad 패턴 참고
def __init__(self, cfg_like, *, log_manager=None, **overrides):
    self.config = self._load_config(cfg_like, **overrides)
    
    # 로깅 초기화
    if log_manager:
        self.logger = log_manager.logger
    elif self.config.log:
        self.logger = LogManager(self.config.log).logger
    else:
        self.logger = LogManager({"enabled": False}).logger
    
    self.logger.debug("FirefoxWebDriver initialized")
```

---

## 📊 최종 비교 표

| 항목 | FirefoxWebDriver | ImageLoad | 권장 |
|------|------------------|-----------|------|
| **상속** | BaseWebDriver | 없음 | 유지 (WebDriver 통일) |
| **ConfigLikeLoader** | load() | load_with_caller_path() | **개선 필요** ✅ |
| **경로 계산** | 수동 | 자동 | **개선 필요** ✅ |
| **로깅 초기화** | 자동 (상속) | 수동 | 유지 |
| **Context Manager** | ✅ | ❌ | 유지 |
| **실행 패턴** | start/quit | run() | 유지 (목적 다름) |

---

## 🚀 구현 우선순위

1. **즉시 개선:** ConfigLikeLoader 사용 간소화
   - `load()` → `load_with_caller_path()` 변경
   - 16줄 → 7줄 코드 간소화

2. **선택 개선:** 로깅 초기화 패턴 통일
   - BaseWebDriver에서 처리 중이므로 유지 가능

3. **유지:** BaseWebDriver 상속 구조
   - WebDriver 통일된 인터페이스 제공
   - Context Manager 자동 지원

---

## ✅ 결론

**공통점:**
- ✅ Adapter 패턴
- ✅ cfg_like 지원
- ✅ ConfigLikeLoader 사용
- ✅ Policy 기반 설정

**차이점:**
- FirefoxWebDriver: BaseWebDriver 상속, Context Manager, WebDriver 생명주기 관리
- ImageLoad: Standalone, run() 메서드, 단순 처리

**개선 필요:**
- ✅ **ConfigLikeLoader 사용 간소화** (즉시)
  - `load()` → `load_with_caller_path()`
  - 코드 57% 감소

**유지:**
- ✅ BaseWebDriver 상속 (WebDriver 통일성)
- ✅ Context Manager (생명주기 관리)
