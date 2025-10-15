# Crawl Utils - WebDriver 사용 가이드

## 🚀 빠른 시작

### 기본 사용

```python
from crawl_utils import FirefoxWebDriver

# 1. 기본 설정으로 생성
with FirefoxWebDriver() as driver:
    driver.driver.get("https://example.com")
    print(driver.driver.title)
```

### YAML 설정 사용

```python
# 2. YAML 파일로 설정
with FirefoxWebDriver("crawl_utils/config/firefox.yaml") as driver:
    driver.driver.get("https://example.com")
```

### Dictionary 설정

```python
# 3. Dictionary로 직접 설정
config = {
    "headless": True,
    "window_size": (1920, 1080),
    "log_config": {
        "name": "my_crawler",
        "sinks": [
            {"sink_type": "console", "level": "INFO"},
            {"sink_type": "file", "filepath": "crawler.log"}
        ]
    }
}

with FirefoxWebDriver(config) as driver:
    driver.driver.get("https://example.com")
```

---

## 📋 로깅 설정

### 1. 기본 로깅 (log_config=None)

`log_config`를 지정하지 않으면 기본 콘솔 로깅 사용:

```python
driver = FirefoxWebDriver({"headless": True})
# 자동으로 콘솔에 INFO 레벨 로그 출력
```

**기본 설정**:
- Logger name: `firefoxwebdriver` (클래스명 소문자)
- Sink: Console only
- Level: INFO
- Format: 색상 포함 시간/레벨/이름/메시지

### 2. YAML 파일 로깅

별도 YAML 파일로 상세한 로깅 설정:

```python
config = {
    "headless": True,
    "log_config": "crawl_utils/config/webdriver_log.yaml"
}

driver = FirefoxWebDriver(config)
```

**제공되는 YAML**:
- `webdriver_log.yaml`: 콘솔 + 파일 로깅

### 3. Dictionary 로깅

코드에서 직접 로깅 설정:

```python
config = {
    "headless": True,
    "log_config": {
        "name": "taobao_crawler",
        "sinks": [
            {
                "sink_type": "console",
                "level": "INFO",
                "colorize": True
            },
            {
                "sink_type": "file",
                "filepath": "output/logs/taobao.log",
                "level": "DEBUG",
                "rotation": "10 MB",
                "retention": "7 days"
            }
        ]
    }
}

driver = FirefoxWebDriver(config)
```

### 4. 로깅 비활성화

로깅을 완전히 끄려면 빈 sinks 사용:

```python
config = {
    "log_config": {
        "name": "silent",
        "sinks": []
    }
}
```

---

## ⚙️ WebDriverPolicy 주요 옵션

### 기본 설정

```yaml
provider: "firefox"           # "firefox", "chrome", "edge"
headless: false               # Headless 모드
window_size: [1440, 900]      # 브라우저 창 크기
```

### Session 관리

```yaml
session_path: "data/session/firefox.json"
save_session: true
```

브라우저 세션 헤더를 JSON 파일에 저장/로드합니다.

### Driver 경로

```yaml
driver_path: null             # null = 자동 감지
# driver_path: "C:/geckodriver.exe"  # 수동 지정
```

### 브라우저 옵션

```yaml
user_agent: "Mozilla/5.0 ..."
accept_languages: "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
disable_automation: true      # 자동화 감지 우회
```

### Firefox 전용 옵션

```yaml
binary_path: null             # Firefox 실행 파일 경로
profile_path: null            # Firefox 프로필 경로
dom_enabled: false
resist_fingerprint_enabled: false
use_webdriver_manager: true   # geckodriver 자동 다운로드
```

---

## 📝 예제

### 예제 1: 간단한 크롤링

```python
from crawl_utils import FirefoxWebDriver

config = {
    "headless": True,
    "log_config": {
        "name": "simple_crawler",
        "sinks": [{"sink_type": "console", "level": "INFO"}]
    }
}

with FirefoxWebDriver(config) as driver:
    driver.logger.info("크롤링 시작")
    
    driver.driver.get("https://example.com")
    title = driver.driver.title
    
    driver.logger.success(f"페이지 로드 완료: {title}")
```

### 예제 2: 세션 저장/로드

```python
config = {
    "headless": False,
    "session_path": "data/session/taobao.json",
    "save_session": True,
    "log_config": "crawl_utils/config/webdriver_log.yaml"
}

with FirefoxWebDriver(config) as driver:
    driver.logger.info("타오바오 접속")
    driver.driver.get("https://world.taobao.com")
    
    # 수동 로그인 후 세션 자동 저장됨
    input("로그인 후 Enter를 누르세요...")
    
    driver.logger.success("세션 저장 완료")
```

다음 실행 시 저장된 헤더를 사용합니다.

### 예제 3: 상세 로깅 + 파일 저장

```python
config = {
    "headless": True,
    "log_config": {
        "name": "detailed_crawler",
        "sinks": [
            {
                "sink_type": "console",
                "level": "INFO",
                "format": "<green>{time:HH:mm:ss}</green> | <level>{message}</level>",
                "colorize": True
            },
            {
                "sink_type": "file",
                "filepath": "output/logs/crawler/{time:YYYY-MM-DD}_crawl.log",
                "level": "DEBUG",
                "rotation": "50 MB",
                "retention": "30 days",
                "compression": "zip",
                "format": "{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {file}:{line} | {message}",
                "backtrace": True
            },
            {
                "sink_type": "file",
                "filepath": "output/logs/crawler/errors/{time:YYYY-MM-DD}_error.log",
                "level": "ERROR",
                "rotation": "20 MB",
                "retention": "90 days",
                "backtrace": True,
                "diagnose": True
            }
        ]
    }
}

with FirefoxWebDriver(config) as driver:
    driver.logger.info("크롤링 시작")
    
    try:
        driver.driver.get("https://example.com")
        driver.logger.debug("페이지 로드 완료")
        
        # 크롤링 로직
        items = driver.driver.find_elements("css selector", ".item")
        driver.logger.info(f"아이템 {len(items)}개 발견")
        
        for i, item in enumerate(items):
            driver.logger.debug(f"아이템 {i} 처리 중...")
            # ...
        
        driver.logger.success("크롤링 완료!")
        
    except Exception as e:
        driver.logger.error(f"크롤링 실패: {e}")
        raise
```

### 예제 4: Runtime Override

```python
# YAML 파일 + 런타임 오버라이드
driver = FirefoxWebDriver(
    "crawl_utils/config/firefox.yaml",
    headless=True,  # YAML의 headless 설정 오버라이드
    window_size=(1920, 1080)
)
```

---

## 🔧 고급 사용법

### Context Manager vs Manual

```python
# Context Manager (권장)
with FirefoxWebDriver(config) as driver:
    driver.driver.get("https://example.com")
# 자동으로 quit() 호출 + 로깅 종료

# Manual
driver = FirefoxWebDriver(config)
try:
    driver.driver.get("https://example.com")
finally:
    driver.quit()  # 수동 정리 필요
```

### Lazy Driver Creation

```python
driver = FirefoxWebDriver(config)
# 여기까지는 브라우저가 실행되지 않음

driver.driver.get("https://example.com")
# driver.driver 첫 접근 시 브라우저 실행
```

### 세션 헤더 추출

```python
with FirefoxWebDriver(config) as driver:
    driver.driver.get("https://example.com")
    
    # 현재 브라우저 헤더 추출
    headers = driver._extract_headers()
    print(headers)
    # {
    #     "User-Agent": "Mozilla/5.0 ...",
    #     "Accept-Language": "ko-KR,ko;q=0.9"
    # }
```

---

## 📚 관련 문서

- [logs_utils 사용 가이드](../logs_utils/config/README.md)
- [FirefoxPolicy 정의](../crawl_utils/core/policy.py)
- [BaseWebDriver 구현](../crawl_utils/provider/base.py)

---

## ⚠️ 주의사항

1. **logs_utils 의존성**: `logs_utils` 모듈이 필수입니다.
2. **로깅 fallback 제거**: 이전 버전의 기본 `logging` 모듈 fallback이 삭제되었습니다.
3. **Context Manager 권장**: 리소스 정리를 위해 `with` 문 사용을 권장합니다.
4. **Thread Safety**: loguru 덕분에 멀티스레드 환경에서도 안전합니다 (enqueue=True).

---

## 🎯 마이그레이션 가이드

### 기존 코드 (v1)

```python
# 예전 방식
from firefox import FirefoxDriver

driver = FirefoxDriver(config_path="firefox.yaml")
driver.quit()
```

### 새 코드 (v2 - 리팩토링 후)

```python
# 새 방식
from crawl_utils import FirefoxWebDriver

with FirefoxWebDriver("crawl_utils/config/firefox.yaml") as driver:
    # 작업 수행
    pass
# 자동 정리
```

### 주요 변경사항

1. **Import 경로**: `firefox` → `crawl_utils`
2. **클래스명**: `FirefoxDriver` → `FirefoxWebDriver`
3. **로깅**: 기본 `logging` → `logs_utils` (loguru)
4. **설정**: `log_policy` 필드 → `log_config` 필드
