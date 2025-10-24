# SyncCrawl Configuration Guide

## 📋 Two-Policy Config Structure

SyncCrawl은 **2개의 분리된 정책**을 명시적으로 받습니다:

### 1. cfg_like_webdriver (WebDriver 설정)
```
modules/crawl_utils/configs/webdriver_manager.yaml
```
- **용도**: SyncCrawl.__init__()에서 WebDriver 초기화
- **정책**: WebDriverManagerPolicy
- **내용**: provider, headless, window_size, firefox config 등
- **로드 시점**: 인스턴스 생성 시 (1회)

### 2. cfg_like_crawl (Crawl 정책)
```
modules/crawl_utils/configs/crawl_default.yaml
```
- **용도**: Preset이 없을 때 사용하는 fallback CrawlPolicy
- **정책**: CrawlPolicy
- **내용**: scroll, wait, extractor, post_processor 등
- **로드 시점**: run() 실행 시 (PresetManager가 정책 못 찾을 때)

---

## 🎯 사용 시나리오

### 시나리오 1: Preset과 함께 사용 (일반적)
```python
from crawl_utils.adapter import SyncCrawl
from logs_utils import LogManager

# 두 개의 정책 모두 명시
crawl = SyncCrawl(
    cfg_like_webdriver="modules/crawl_utils/configs/webdriver_manager.yaml",
    cfg_like_crawl="modules/crawl_utils/configs/crawl_default.yaml",
    log_manager=LogManager(name="crawl", level="INFO")
)

# URL 크롤링 → PresetManager가 site/method 분석 → Preset 사용
results = crawl.run(
    urls=["https://www.aliexpress.com/item/123456.html"],  # ✅ Preset 있음
    provider="firefox"
)
```

### 시나리오 2: Preset 없이 fallback 사용
```python
from crawl_utils.adapter import SyncCrawl
from logs_utils import LogManager

# 두 개의 정책 모두 명시
crawl = SyncCrawl(
    cfg_like_webdriver="modules/crawl_utils/configs/webdriver_manager.yaml",
    cfg_like_crawl="modules/crawl_utils/configs/crawl_default.yaml",
    log_manager=LogManager(name="crawl", level="INFO")
)

# URL 크롤링 → PresetManager가 정책 못 찾음 → cfg_like_crawl 사용 (fallback)
results = crawl.run(
    urls=["https://unknown-site.com/product/123"],  # ❌ Preset 없음 → fallback 사용
    provider="firefox"
)
```

### 시나리오 3: Dict로 직접 전달
```python
# ConfigLoader로 dict 추출
from cfg_utils import ConfigLoader

config = ConfigLoader(config_loader_cfg_path="configs/loader/config_loader_crawl.yaml")
webdriver_dict = config.to_dict(section="webdriver_manager")
crawl_dict = config.to_dict(section="crawl")

# Dict로 초기화
crawl = SyncCrawl(
    cfg_like_webdriver=webdriver_dict,
    cfg_like_crawl=crawl_dict,
    log_manager=LogManager(name="crawl", level="INFO")
)
```

---

## 🔧 설정 커스터마이징

### 1. Site별 Preset 생성 (권장)
```python
# modules/crawl_utils/presets/sites/mysite.py
from crawl_utils.models.policy import CrawlPolicy

def get_policy(method: str) -> dict:
    return {
        "detail": CrawlPolicy(
            site="mysite",
            method="detail",
            scroll={"strategy": "infinite", "max_scrolls": 20},
            extractor={
                "type": "js",
                "js_snippet": "return {...}"
            }
        ).model_dump()
    }.get(method)
```

### 2. crawl_default.yaml 수정
```yaml
# 모든 필드가 포함되어 있으므로 필요한 부분만 수정
crawl:
  scroll:
    strategy: "fixed"  # 기본값 변경
    scroll_count: 3
  
  wait:
    timeout_sec: 20.0  # 타임아웃 증가
  
  extractor:
    js_snippet: |
      // 커스텀 추출 로직
      return { /* ... */ };
```

### 3. webdriver_manager.yaml 수정
```yaml
# Firefox 프로필, 드라이버 경로 등 변경
webdriver_manager:
  provider: "firefox"
  firefox:
    profile_path: "C:/custom/firefox/profile"
    driver_path: "C:/drivers/geckodriver.exe"
```

---

## 📂 Config File Examples

### webdriver_manager.yaml (현재)
```yaml
webdriver_manager:
  name: "webdriver_manager"
  provider: "firefox"
  headless: false
  window_size:
    width: 1920
    height: 1080
  firefox:
    profile_path: "C:/Users/jaeho/AppData/Roaming/Mozilla/Firefox/Profiles/xxx"
    driver_path: "C:/Program Files/Mozilla Firefox/geckodriver.exe"
    preferences:
      dom.webdriver.enabled: false
      useAutomationExtension: false
```

### crawl_default.yaml (신규)
```yaml
crawl:
  name: "crawl"
  site: ""  # PresetManager가 자동 설정
  method: ""
  
  scroll:
    strategy: "infinite"
    max_scrolls: 10
    scroll_pause_sec: 1.0
  
  wait:
    hook: "css"
    selector: "body"
    timeout_sec: 10.0
  
  extractor:
    type: "js"
    js_snippet: |
      // 범용 데이터 추출
      return {
        title: document.querySelector('h1')?.innerText || '',
        images: Array.from(document.querySelectorAll('img'))
          .map(img => img.src).filter(Boolean),
        price: document.querySelector('[class*="price"]')?.innerText || ''
      };
  
  post_processor:
    target_dir: "{{output_dir}}/crawl/default"
    use_smart_normalizer: true
    rules: [...]
```

---

## 🚀 Quick Start

```python
from crawl_utils.adapter import SyncCrawl
from logs_utils import LogManager

# 1. 두 개의 정책으로 초기화
crawl = SyncCrawl(
    cfg_like_webdriver="modules/crawl_utils/configs/webdriver_manager.yaml",
    cfg_like_crawl="modules/crawl_utils/configs/crawl_default.yaml",
    log_manager=LogManager(name="sync_crawl", level="INFO")
)

# 2. Preset 있는 URL 크롤링
results = crawl.run(
    urls=["https://www.aliexpress.com/item/123.html"],
    provider="firefox"
)

# 3. Preset 없는 URL → fallback 사용
results = crawl.run(
    urls=["https://unknown-site.com/product/456"],
    provider="firefox"
)
```

---

## 🔍 Config Loading Flow

```
SyncCrawl.__init__(
    cfg_like_webdriver="webdriver_manager.yaml",
    cfg_like_crawl="crawl_default.yaml"
)
  ↓
  ├─ WebDriverManagerPolicy 로드 (Firefox 설정, 드라이버 경로 등)
  └─ CrawlPolicy 로드 (Fallback 정책)
  ↓
SyncCrawl.run(urls=["..."])
  ↓
  PresetManager.analyze_url(url) → (site, method, region)
  ↓
  PresetManager.get_crawl_policy(site, method) → CrawlPolicy dict OR None
  ↓
  IF Preset 없음 (None):
    └─ self.crawl_policy_fallback 사용 (cfg_like_crawl에서 로드된 것)
  ELSE:
    └─ Preset CrawlPolicy 사용
  ↓
  Crawling 실행
```

---

## ⚠️ 주의사항

1. **Two-Policy Pattern**:
   - cfg_like_webdriver: WebDriver 설정 (정적, 한 번만 로드)
   - cfg_like_crawl: Crawl 정책 (Preset 없을 때 fallback)
   - 두 개의 인자 모두 명시적으로 전달 권장

2. **Preset 우선순위**:
   - PresetManager의 site-specific 정책 > cfg_like_crawl fallback
   - Preset이 있으면 cfg_like_crawl은 사용 안 됨

3. **로깅**:
   - SyncCrawl은 LogManager를 외부에서 주입받습니다
   - logs_utils.LogManager 사용 (log_config는 참고용)

4. **환경변수**:
   - {{output_dir}}, {{root}} 등은 ConfigLoader의 paths.local.yaml에서 해석됩니다
   - CASHOP_PATHS 환경변수 필요

5. **None 허용**:
   - cfg_like_webdriver=None → 기본 webdriver_manager.yaml 사용
   - cfg_like_crawl=None → 기본 crawl_default.yaml 사용

---

## 📚 Related Documents

- `docs/SyncCrawl_PARAMETER_REVIEW.md` - Parameter 검토 리포트
- `modules/crawl_utils/README.md` - crawl_utils 모듈 문서
- `_code/ENVIRONMENT_VARIABLES.md` - 환경변수 설정 가이드
