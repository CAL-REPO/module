# Crawl Utils Configuration Examples

이 디렉토리는 `crawl_utils` 모듈의 설정 파일 예제를 포함합니다.

## 📁 파일 구조

```
config/
├── README.md                # 이 파일
├── crawl.yaml               # 기본 설정
├── crawl_simple.yaml        # 간단한 예제
└── crawl_full.yaml          # 전체 옵션 예제
```

## 🎯 사용 방법

### 1. Simple 버전 (권장)

자주 사용하는 옵션만 포함한 간단한 예제입니다.

```python
from crawl_utils import FirefoxWebDriver, run_sync_crawl

# WebDriver 설정
driver_config = {
    "headless": True,
    "window_size": (1920, 1080)
}

# 동기 방식으로 크롤링 실행
with FirefoxWebDriver(driver_config) as driver:
    items = run_sync_crawl(
        "crawl_utils/config/crawl_simple.yaml",
        driver,
        max_pages=5
    )
    print(f"Crawled {len(items)} items")
```

### 2. Full 버전

모든 가능한 옵션을 확인하고 싶을 때 참고하세요.

```python
from crawl_utils import SyncCrawlRunner, FirefoxWebDriver, CrawlPolicy
from cfg_utils import ConfigLoader

# YAML에서 정책 로드
loader = ConfigLoader("crawl_utils/config/crawl_full.yaml")
policy = loader.as_model(CrawlPolicy, section="crawl")

# 크롤러 실행
with FirefoxWebDriver(driver_config) as driver:
    runner = SyncCrawlRunner(policy)
    items = runner.run_crawl(driver, max_pages=10)
```

### 3. Runtime Override

YAML 설정을 기본으로 하고 특정 값만 런타임에 변경:

```python
from cfg_utils import ConfigLoader

# YAML 로드
loader = ConfigLoader("crawl_utils/config/crawl_simple.yaml")
policy = loader.as_model(CrawlPolicy, section="crawl")

# 런타임에 설정 변경
policy.execution_mode = "async"
policy.concurrency = 8
policy.navigation.max_pages = 20

# 실행
runner = SyncCrawlRunner(policy)
items = runner.run_crawl(driver)
```

## 📋 주요 설정 설명

### Navigation (페이지 순회)

```yaml
navigation:
  base_url: "https://example.com/products"
  url_template: "https://example.com/products?page={page}"
  page_param: "page"
  start_page: 1
  max_pages: 10
  params:
    category: "electronics"
```

### Scroll (스크롤 전략)

```yaml
scroll:
  strategy: "infinite"      # none | paginate | infinite
  max_scrolls: 10
  scroll_pause_sec: 1.5
```

### Extractor (데이터 추출)

```yaml
extractor:
  type: "dom"              # dom | js | api
  item_selector: ".product-item"
```

### Wait (로딩 대기)

```yaml
wait:
  hook: "css"              # none | css | xpath
  selector: ".product-item"
  timeout_sec: 10.0
  condition: "visibility"  # presence | visibility
```

### Normalization (정규화)

```yaml
normalization:
  rules:
    - kind: "image"
      source: "img.src"
      static_section: "products"
      name_template: "product_{index}"
      extension: ".jpg"
      explode: true
```

### Storage (저장)

```yaml
storage:
  image:
    base_dir: "output/crawl/images"
    name_template: "{section}_{index}"
    ensure_unique: true
  
  text:
    base_dir: "output/crawl/texts"
    name_template: "{section}_{index}"
```

### Execution (실행 모드)

```yaml
execution_mode: "async"    # async | sync
concurrency: 4             # async 모드에서만
retries: 2
retry_backoff_sec: 1.0
```

## 🔄 실행 모드

### Async Mode (기본, 권장)

고성능, 복잡한 파이프라인에 적합:

```yaml
execution_mode: "async"
concurrency: 4
```

**장점:**
- 여러 페이지 동시 처리
- 네트워크 대기 시간 최소화
- 대량 크롤링에 효율적

**사용 예:**
```python
# 자동으로 비동기 실행됨
runner = SyncCrawlRunner(policy)  # 내부에서 asyncio.run() 사용
items = runner.run_crawl(driver)
```

### Sync Mode

간단한 스크립트, Jupyter 노트북에 적합:

```yaml
execution_mode: "sync"
```

**장점:**
- 이해하기 쉬운 순차 실행
- 디버깅 용이
- 작은 규모 크롤링에 적합

**사용 예:**
```python
# 순차적으로 한 페이지씩 처리
runner = SyncCrawlRunner(policy)
items = runner.run_crawl(driver, max_pages=3)
```

## 💡 팁

### 1. 최소 설정

필수 항목만 설정하고 나머지는 기본값 사용:

```yaml
crawl:
  navigation:
    base_url: "https://example.com"
  
  storage:
    image:
      base_dir: "output/images"
  
  execution_mode: "sync"
```

### 2. 무한 스크롤 페이지

Instagram, Facebook 등의 무한 스크롤:

```yaml
scroll:
  strategy: "infinite"
  max_scrolls: 20
  scroll_pause_sec: 2.0

wait:
  hook: "css"
  selector: ".loading-spinner"
  condition: "visibility"
```

### 3. API 기반 추출

JavaScript로 API 호출:

```yaml
extractor:
  type: "js"
  js_snippet: |
    const response = await fetch('/api/products');
    return await response.json();
```

### 4. 섹션별 그룹핑

카테고리별로 파일 분류:

```yaml
normalization:
  rules:
    - kind: "image"
      source: "img.src"
      section_field: ".category"  # 카테고리별로 섹션 생성
      name_template: "{section}_{index}"
```

## 📚 관련 문서

- [crawl_utils README](../../../docs/README.md)
- [CrawlPolicy 정의](../core/policy.py)
- [SyncCrawlRunner 구현](../services/sync_runner.py)

## ⚠️ 주의사항

1. **execution_mode**: async 모드가 기본이지만, 간단한 스크립트는 sync 권장
2. **concurrency**: 너무 높으면 서버 부하 증가 (2-8 권장)
3. **retries**: API 제한이 있는 사이트는 재시도 줄이기
4. **selector**: CSS 셀렉터 정확성이 크롤링 성공의 핵심

## 🎯 마이그레이션 가이드

### 기존 방식

```python
# 직접 파이프라인 구성
navigator = Navigator(...)
extractor = Extractor(...)
normalizer = Normalizer(...)
# ...
```

### 새 방식 (YAML 사용)

```python
# YAML로 모든 설정 관리
items = run_sync_crawl("config/crawl.yaml", driver)
```

### 주요 변경사항

1. **설정 파일화**: 코드와 설정 분리
2. **실행 모드**: sync/async 선택 가능
3. **편의 함수**: `run_sync_crawl()` 추가
4. **타입 안전성**: Pydantic Policy로 검증
