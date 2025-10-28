# SyncCrawl Retry Mechanism Design

## 📋 개요

**작성일**: 2025-01-28  
**대상 모듈**: `crawl_utils.adapter.sync_crawl`  
**목적**: WebDriver 및 크롤링 실패 시 자동 재시도 메커니즘 도입

---

## 🎯 배경 및 필요성

### 현재 구조 (v8.0)

```
SyncCrawl (High-Level Orchestrator)
├── URL 분석 & Preset 준비
├── WebDriverManager 관리 (시작/종료)
├── SessionBridge 설정 (선택적)
└── Inline Pipeline 실행
    ├── Navigator (load → scroll → wait)
    ├── Extractor (JS execution)
    ├── ItemsNormalizer (policy 기반 변환)
    └── ItemSaver (파일 저장)
```

### 기존 통합 히스토리

> **오늘 개선 작업 전**: Pipeline이 분리되어 있었음  
> **통합 목적**: WebDriver 및 세션 관리를 가볍고 유연하게 처리

**통합 결과**:
- ✅ `_execute()` 메서드에서 전체 pipeline 직접 관리
- ✅ WebDriver 시작/종료 한 곳에서 제어
- ✅ SessionBridge, Fetcher 등 선택적 초기화
- ⚠️ **실패 시 재시도 로직 부재** (현재 문제점)

---

## 🔥 실패 시나리오 분석

### 1. WebDriver 관련 실패

```python
# Step 1: WebDriver 시작
webdriver_manager.start()  # ❌ 실패 가능
```

**실패 원인**:
- Selenium WebDriver 초기화 실패
- Browser binary not found
- Port already in use
- Network timeout (proxy 설정 시)

### 2. Navigation 실패

```python
# Navigator load
navigator.load(url)  # ❌ 실패 가능
```

**실패 원인**:
- Page load timeout
- DNS resolution failure
- CAPTCHA / Bot detection
- Connection refused (China region)

### 3. Extraction 실패

```python
# Extractor JS execution
extracted_records = extractor.extract(dom=dom)  # ❌ 실패 가능
```

**실패 원인**:
- JavaScript execution error
- Page structure changed (selector mismatch)
- Lazy loading not completed
- Dynamic content not loaded

### 4. Item Processing 실패

```python
# ItemsNormalizer / ItemSaver
items = items_normalizer.process(...)  # ❌ 실패 가능
summary = saver.save(items=items, ...)  # ❌ 실패 가능
```

**실패 원인**:
- Validation error (Pydantic)
- File I/O error (disk full)
- Network error (download images)

---

## 🏗️ Retry 메커니즘 설계

### Policy 정의

```yaml
# crawl_policy.retry (새 필드)
retry:
  enabled: true
  max_attempts: 3              # 최대 시도 횟수 (기본: 3)
  backoff_strategy: exponential  # fixed | linear | exponential
  initial_delay_sec: 2.0       # 초기 대기 시간
  max_delay_sec: 30.0          # 최대 대기 시간
  backoff_factor: 2.0          # 지수 증가 배수
  retry_on_exceptions:         # 재시도할 예외 타입
    - TimeoutException
    - WebDriverException
    - ConnectionError
    - NoSuchElementException
  skip_on_exceptions:          # 재시도하지 않을 예외
    - ValidationError
    - KeyboardInterrupt
```

### Pydantic Model

```python
# policy.py
class RetryPolicy(BaseModel):
    """Retry 정책"""
    enabled: bool = Field(default=True, description="Retry 활성화")
    max_attempts: int = Field(default=3, ge=1, le=10, description="최대 시도 횟수")
    backoff_strategy: str = Field(
        default="exponential",
        description="대기 전략: fixed | linear | exponential"
    )
    initial_delay_sec: float = Field(default=2.0, ge=0.1, description="초기 대기 시간 (초)")
    max_delay_sec: float = Field(default=30.0, ge=1.0, description="최대 대기 시간 (초)")
    backoff_factor: float = Field(default=2.0, ge=1.0, description="지수 증가 배수")
    retry_on_exceptions: List[str] = Field(
        default_factory=lambda: [
            "TimeoutException",
            "WebDriverException", 
            "ConnectionError",
            "NoSuchElementException"
        ],
        description="재시도할 예외 타입 (클래스명)"
    )
    skip_on_exceptions: List[str] = Field(
        default_factory=lambda: ["ValidationError", "KeyboardInterrupt"],
        description="재시도하지 않을 예외 (클래스명)"
    )

class SyncCrawlPolicy(BaseModel):
    # ... 기존 필드 ...
    retry: Optional[RetryPolicy] = Field(default_factory=RetryPolicy, description="Retry 정책")
```

---

## 🔧 구현 방안

### Option 1: Decorator 패턴 (권장)

**장점**:
- 코드 재사용성 높음
- 기존 코드 수정 최소화
- 단위 테스트 용이

**구조**:
```python
# retry_utils.py (새 모듈)
import time
import functools
from typing import Callable, List, Optional, Type
from loguru import logger

def retry_on_exception(
    retry_policy: RetryPolicy,
    log: logger
) -> Callable:
    """Retry decorator with exponential backoff
    
    Args:
        retry_policy: RetryPolicy 인스턴스
        log: Logger 인스턴스
    
    Returns:
        Decorated function with retry logic
    
    Example:
        >>> @retry_on_exception(retry_policy=policy, log=logger)
        ... def crawl_page(url: str):
        ...     # 크롤링 로직
        ...     pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not retry_policy.enabled:
                # Retry 비활성화 시 바로 실행
                return func(*args, **kwargs)
            
            last_exception = None
            
            for attempt in range(1, retry_policy.max_attempts + 1):
                try:
                    log.info(f"🔄 Attempt {attempt}/{retry_policy.max_attempts}: {func.__name__}")
                    result = func(*args, **kwargs)
                    
                    if attempt > 1:
                        log.info(f"✅ Success on attempt {attempt}")
                    
                    return result
                    
                except Exception as e:
                    last_exception = e
                    exception_name = type(e).__name__
                    
                    # Skip 예외 체크
                    if exception_name in retry_policy.skip_on_exceptions:
                        log.error(f"❌ Skip retry for {exception_name}: {e}")
                        raise
                    
                    # Retry 예외 체크
                    if exception_name not in retry_policy.retry_on_exceptions:
                        log.error(f"❌ No retry for {exception_name}: {e}")
                        raise
                    
                    # 마지막 시도 실패
                    if attempt == retry_policy.max_attempts:
                        log.error(f"❌ All {retry_policy.max_attempts} attempts failed")
                        raise
                    
                    # Backoff 계산
                    delay = _calculate_backoff(
                        attempt=attempt,
                        strategy=retry_policy.backoff_strategy,
                        initial_delay=retry_policy.initial_delay_sec,
                        max_delay=retry_policy.max_delay_sec,
                        factor=retry_policy.backoff_factor
                    )
                    
                    log.warning(
                        f"⚠️ Attempt {attempt} failed ({exception_name}): {e}\n"
                        f"   Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
            
            # Should not reach here
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


def _calculate_backoff(
    attempt: int,
    strategy: str,
    initial_delay: float,
    max_delay: float,
    factor: float
) -> float:
    """Backoff 대기 시간 계산
    
    Args:
        attempt: 현재 시도 횟수 (1-based)
        strategy: 전략 (fixed | linear | exponential)
        initial_delay: 초기 대기 시간
        max_delay: 최대 대기 시간
        factor: 증가 배수
    
    Returns:
        대기 시간 (초)
    """
    if strategy == "fixed":
        delay = initial_delay
    elif strategy == "linear":
        delay = initial_delay * attempt
    elif strategy == "exponential":
        delay = initial_delay * (factor ** (attempt - 1))
    else:
        delay = initial_delay
    
    return min(delay, max_delay)
```

### Option 2: Context Manager 패턴

**장점**:
- Resource cleanup 보장 (WebDriver)
- with 구문으로 명시적

**단점**:
- 코드 구조 변경 필요
- 재사용성 낮음

---

## 📐 적용 위치

### 1. `_execute()` 전체 재시도 (Level 1 - 최우선)

```python
class SyncCrawl:
    def run(self, urls: Union[str, List[str]], **overrides) -> List[Dict[str, Any]]:
        # ... URL 분석 및 preset 준비 ...
        
        for url in urls:
            try:
                # ✅ _execute 전체를 retry 대상으로
                result = self._execute_with_retry(
                    url=url,
                    crawl_policy=crawl_policy,
                    webdriver_overrides=webdriver_overrides,
                    preset_policy=preset_policy,
                    **overrides
                )
                all_results.append(result)
            except Exception as e:
                self.log.error(f"Failed after all retries: {url} - {e}")
                all_results.append({"url": url, "error": str(e), "success": False})
        
        return all_results
    
    def _execute_with_retry(self, *args, **kwargs) -> Dict[str, Any]:
        """Retry wrapper for _execute"""
        @retry_on_exception(
            retry_policy=self.policy.retry,  # ✅ Policy에서 가져옴
            log=self.log
        )
        def _wrapped():
            return self._execute(*args, **kwargs)
        
        return _wrapped()
```

### 2. Navigator.load() 재시도 (Level 2 - 선택적)

```python
# _execute() 내부
@retry_on_exception(retry_policy=crawl_policy.retry, log=self.log)
def _load_page():
    navigator.load(url)

_load_page()  # ✅ Page load만 재시도
```

### 3. Extractor.extract() 재시도 (Level 3 - 선택적)

```python
@retry_on_exception(retry_policy=crawl_policy.retry, log=self.log)
def _extract_data():
    return extractor.extract(dom=dom)

extracted_records = _extract_data()  # ✅ Extraction만 재시도
```

---

## 📊 예상 동작 시나리오

### Scenario 1: Navigator Timeout (3회 재시도)

```
🔄 Attempt 1/3: _execute
   ├── WebDriver started (Firefox)
   ├── Navigator.load(url) → ❌ TimeoutException
   └── ⚠️ Attempt 1 failed (TimeoutException): Message: Timeout
       Retrying in 2.0s...

🔄 Attempt 2/3: _execute
   ├── WebDriver started (Firefox)
   ├── Navigator.load(url) → ❌ TimeoutException
   └── ⚠️ Attempt 2 failed (TimeoutException): Message: Timeout
       Retrying in 4.0s...

🔄 Attempt 3/3: _execute
   ├── WebDriver started (Firefox)
   ├── Navigator.load(url) → ✅ Success
   ├── Extractor.extract() → ✅ 29 items
   └── ItemSaver.save() → ✅ 26 files saved

✅ Success on attempt 3
```

### Scenario 2: ValidationError (Skip Retry)

```
🔄 Attempt 1/3: _execute
   ├── WebDriver started (Firefox)
   ├── Navigator.load(url) → ✅ Success
   ├── Extractor.extract() → ✅ 29 items
   └── ItemsNormalizer.process() → ❌ ValidationError
       
❌ Skip retry for ValidationError: 1 validation error
   url field required
```

---

## 🧪 테스트 계획

### Unit Test

```python
# test_retry_decorator.py
import pytest
from unittest.mock import Mock
from crawl_utils.retry_utils import retry_on_exception, RetryPolicy

def test_retry_success_on_second_attempt():
    """2번째 시도에서 성공"""
    policy = RetryPolicy(max_attempts=3, initial_delay_sec=0.1)
    log = Mock()
    
    mock_func = Mock(side_effect=[
        TimeoutException("Timeout"),  # 1st attempt
        "success"                      # 2nd attempt
    ])
    
    @retry_on_exception(retry_policy=policy, log=log)
    def test_func():
        return mock_func()
    
    result = test_func()
    
    assert result == "success"
    assert mock_func.call_count == 2
    log.warning.assert_called_once()  # Retry warning


def test_skip_on_validation_error():
    """ValidationError는 재시도하지 않음"""
    policy = RetryPolicy(
        max_attempts=3,
        skip_on_exceptions=["ValidationError"]
    )
    log = Mock()
    
    @retry_on_exception(retry_policy=policy, log=log)
    def test_func():
        raise ValidationError("Invalid data")
    
    with pytest.raises(ValidationError):
        test_func()
    
    log.error.assert_called_with("❌ Skip retry for ValidationError: Invalid data")
```

### Integration Test

```python
# test_sync_crawl_retry.py
def test_crawl_with_retry_on_timeout(mocker):
    """Timeout 시 자동 재시도"""
    # Mock WebDriver to fail first time
    mock_driver = mocker.patch("crawl_utils.adapter.webdriver_manager.WebDriverManager")
    mock_driver.start.side_effect = [
        TimeoutException("Connection timeout"),  # 1st
        None,                                     # 2nd (success)
    ]
    
    config = ConfigLoader(...).to_dict()
    config["crawl"]["retry"]["max_attempts"] = 2
    
    crawl = SyncCrawl(cfg_like=config, log_manager=log_mgr)
    results = crawl.run(urls=["https://example.com/item/123"])
    
    assert results[0]["success"] is True
    assert mock_driver.start.call_count == 2  # Retried once
```

---

## 🎛️ 설정 예시

### 기본 설정 (YAML)

```yaml
# configs/xloto/xloto_crawl.yaml
crawl:
  retry:
    enabled: true
    max_attempts: 3
    backoff_strategy: exponential
    initial_delay_sec: 2.0
    max_delay_sec: 30.0
    backoff_factor: 2.0
    retry_on_exceptions:
      - TimeoutException
      - WebDriverException
      - ConnectionError
      - NoSuchElementException
    skip_on_exceptions:
      - ValidationError
      - KeyboardInterrupt
```

### Runtime Override

```python
# 런타임에 retry 설정 변경
crawl = SyncCrawl(cfg_like=config.to_dict(), log_manager=log_mgr)

results = crawl.run(
    urls=["https://example.com/item/123"],
    crawl__retry__max_attempts=5,  # ✅ KeyPath override
    crawl__retry__initial_delay_sec=5.0
)
```

---

## 📈 성능 영향 분석

### Best Case (성공)
- **추가 오버헤드**: 거의 없음 (decorator call만)
- **실행 시간**: 기존과 동일

### Worst Case (3회 재시도 후 실패)
- **추가 대기 시간**: 2s + 4s + 8s = 14s (exponential)
- **WebDriver 재시작**: 3회 × ~5s = 15s
- **총 추가 시간**: ~29s

### Expected Case (2회 시도 후 성공)
- **추가 대기 시간**: 2s
- **WebDriver 재시작**: 1회 × ~5s = 5s
- **총 추가 시간**: ~7s

---

## ✅ 구현 체크리스트

### Phase 1: 기본 구조 (1-2시간)
- [ ] `RetryPolicy` Pydantic 모델 추가 (`policy.py`)
- [ ] `retry_utils.py` 모듈 생성
- [ ] `retry_on_exception` decorator 구현
- [ ] `_calculate_backoff` 헬퍼 함수 구현

### Phase 2: SyncCrawl 통합 (1-2시간)
- [ ] `SyncCrawl._execute_with_retry()` 메서드 추가
- [ ] `SyncCrawl.run()` 수정 (retry 적용)
- [ ] Exception 로깅 개선

### Phase 3: 테스트 (2-3시간)
- [ ] Unit test 작성 (retry_utils)
- [ ] Integration test 작성 (sync_crawl)
- [ ] Manual test (실제 URL)

### Phase 4: 문서화 (1시간)
- [ ] YAML 설정 예시
- [ ] README 업데이트
- [ ] Docstring 보완

---

## 🚀 우선순위

1. **High Priority**: Level 1 - `_execute()` 전체 재시도
   - 이유: WebDriver 시작/종료까지 포함, 가장 포괄적
   - 난이도: 중
   - 예상 시간: 4-6시간

2. **Medium Priority**: Retry Policy 설정 유연화
   - 이유: 사이트별/region별 다른 설정 필요
   - 난이도: 중
   - 예상 시간: 2-3시간

3. **Low Priority**: Level 2/3 - 개별 단계 재시도
   - 이유: Level 1로 대부분 커버 가능
   - 난이도: 하
   - 예상 시간: 1-2시간

---

## 📝 참고사항

### 유사 라이브러리
- `tenacity`: Python retry 라이브러리 (참고용)
- `backoff`: Exponential backoff 구현 (참고용)

### 고려사항
1. **WebDriver cleanup**: 재시도 시 이전 WebDriver 반드시 종료
2. **Stateful 객체**: SessionBridge 등은 재생성 필요
3. **Logging**: 각 시도마다 구분 가능하도록 로그 개선
4. **Cost**: 재시도로 인한 시간/리소스 증가 고려

---

## 🎓 결론

**권장 방안**: Option 1 (Decorator 패턴) + Level 1 (_execute 전체 재시도)

**이유**:
1. ✅ 코드 재사용성 높음
2. ✅ 기존 구조 최소 변경
3. ✅ 테스트 용이
4. ✅ 유연한 정책 설정
5. ✅ WebDriver cleanup 보장

**예상 개발 시간**: 8-12시간 (설계 1h + 구현 4-6h + 테스트 3-5h)

---

**작성자**: GitHub Copilot  
**검토자**: [User]  
**승인일**: [Date]
