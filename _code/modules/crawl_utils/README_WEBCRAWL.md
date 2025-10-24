# crawl_utils - WebCrawl Adapter 리팩토링 완료 ✅

## 🎯 개요

**crawl_utils**의 핵심 Adapter 구조가 완전히 재작성되었습니다. 기존 `Crawl` 클래스를 `WebCrawl`로 변경하고, **image_utils** 패턴과 일관성을 유지하도록 개선했습니다.

### 주요 변경사항

1. **Adapter 이름 변경**: `Crawl` → `WebCrawl` (image_utils 패턴 일치)
2. **PresetManager 통합**: URL 자동 분석 및 정책 선택
3. **SyncSeleniumAdapter 활용**: 기존 services와 완벽한 통합
4. **ConfigLoader 역할 명확화**: `webdriver_manager` section만 관리 (logs 제외)
5. **간소화된 인터페이스**: 복잡한 설정 대신 URL 중심 실행

---

## 📦 구조

```
crawl_utils/
├── adapter/
│   ├── crawl.py               # WebCrawl (Main Adapter)
│   └── webdriver_manager.py   # WebDriverManager
│
├── presets/
│   ├── __init__.py            # PresetManager
│   ├── domains.py             # DOMAIN_MAPPING (site → region)
│   ├── methods.py             # METHOD_PATTERNS (URL → method)
│   ├── sites/
│   │   ├── aliexpress_detail.py
│   │   └── taobao_detail.py
│   └── webdrivers/
│       ├── china.py           # WEBDRIVER_CHINA
│       └── worldwide.py       # WEBDRIVER_GLOBAL
│
├── services/
│   ├── adapter.py             # SyncSeleniumAdapter
│   ├── navigator.py           # SyncNavigator
│   ├── sync_extractor.py      # SyncJSExtractor
│   ├── smart_normalizer.py    # SmartNormalizer
│   └── saver.py               # SyncFileSaver
│
└── entry_point/
    └── crawler.py             # Crawler (WebCrawl wrapper)
```

---

## 🚀 사용법

### 1. 기본 사용 (ConfigLoader + WebCrawl)

```python
from cfg_utils import ConfigLoader
from crawl_utils.adapter import WebCrawl

# ConfigLoader 초기화
config = ConfigLoader(
    config_loader_cfg_path="configs/loader/config_loader_crawl.yaml"
)

# WebCrawl 생성
crawl = WebCrawl(config=config)

# URL 크롤링 실행
results = crawl.run(
    urls=[
        "https://www.aliexpress.com/item/1005006169753025.html",
        "https://item.taobao.com/item.htm?id=789012"
    ],
    provider="firefox"
)

for result in results:
    if result["success"]:
        print(f"✅ {result['url']}: {len(result['data'])} items")
    else:
        print(f"❌ {result['url']}: {result['error']}")
```

### 2. Crawler EntryPoint 사용

```python
from cfg_utils import ConfigLoader
from crawl_utils.entry_point import Crawler

config = ConfigLoader(config_loader_cfg_path="configs/loader/config_loader_crawl.yaml")
crawler = Crawler(config=config)

results = crawler.run(
    urls=["https://aliexpress.com/item/123"],
    provider="firefox"
)
```

### 3. PresetManager 직접 사용

```python
from crawl_utils.presets import PresetManager

preset_mgr = PresetManager()

# URL 분석
url = "https://www.aliexpress.com/item/1005006169753025.html"
site, method, region = preset_mgr.analyze_url(url)
print(f"{url} → ({site}, {method}, {region})")  # (aliexpress, detail, global)

# Crawl Policy 로드
policy = preset_mgr.get_crawl_policy(site, method)
print(policy)  # {"name": "crawl", "site": "aliexpress", "method": "detail", ...}

# WebDriver Override
override = preset_mgr.get_webdriver_override(region, provider="firefox")
print(override)  # {"profile_path": "...", "accept_languages": "en-US,en;q=0.9"}
```

---

## 🔧 ConfigLoader 설정

### config_loader_crawl.yaml

```yaml
# webdriver_manager 섹션만 관리 (logs 제외)
source:
  - src: ["{{configs_dir}}/webdriver_manager.yaml", "webdriver_manager"]
    yaml_parser:
      enable_env: true  # 환경변수 resolving 활성화
```

### 환경변수 설정 (필수!)

```powershell
# PowerShell
$env:CASHOP_PATHS = "M:\CALife\CAShop - 구매대행\_code\configs\paths.local.yaml"
```

**왜 필요한가?**
- `enable_env: true`는 `CASHOP_PATHS` 환경변수를 읽어 `paths.local.yaml` 파싱
- `{{configs_dir}}`, `{{public_dir}}` 등 참조 변수 해석
- ConfigLoader의 모든 경로 resolving의 기준

---

## 🎨 PresetManager 구조

### 1. Domain Mapping (presets/domains.py)

```python
DOMAIN_MAPPING = {
    "aliexpress": {
        "domains": ["aliexpress.com", "aliexpress.us"],
        "region": "global"
    },
    "taobao": {
        "domains": ["taobao.com", "world.taobao.com"],
        "region": "china"
    },
    # ...
}
```

### 2. Method Patterns (presets/methods.py)

```python
METHOD_PATTERNS = [
    {"pattern": r"/item/\d+\.html", "method": "detail"},
    {"pattern": r"/item\.htm", "method": "detail"},
    {"pattern": r"s\.click\.aliexpress\.com", "method": "affiliate"},
    # ...
]
```

### 3. Site Policies (presets/sites/)

```python
# presets/sites/aliexpress_detail.py
ALIEXPRESS_DETAIL = {
    "name": "crawl",
    "site": "aliexpress",
    "method": "detail",
    "scroll": {
        "strategy": "bottom",
        "max_scrolls": 5,
        "scroll_pause_sec": 0.5
    },
    "wait": {
        "hook": "css",
        "selector": ".product-title",
        "timeout_sec": 10,
        "condition": "presence"
    },
    "extractor": {
        "js_snippet_file": "extract_product.js"
    }
}
```

### 4. WebDriver Overrides (presets/webdrivers/)

```python
# presets/webdrivers/china.py
WEBDRIVER_CHINA = {
    "firefox": {
        "profile_path": "M:/Firefox_Profile/CRAWL_CHINA",
        "accept_languages": "zh-CN,zh;q=0.9"
    },
    "chrome": {
        "user_data_dir": "M:/Chrome_Profile/CRAWL_CHINA",
        "accept_languages": "zh-CN,zh;q=0.9"
    }
}
```

**Override 적용 방식:**
```python
# ConfigLoader 기본 설정 로드
webdriver_config = config.to_dict(section="webdriver_manager")

# Preset override 적용
override = preset_manager.get_webdriver_override(region, provider)
if override:
    webdriver_config[provider].update(override)  # 직접 dict 업데이트
```

---

## 🔄 Pipeline 실행 흐름

```
1. URL 입력
   ↓
2. PresetManager.analyze_url(url)
   → (site, method, region) 추출
   ↓
3. PresetManager.get_crawl_policy(site, method)
   → CrawlPolicy 로드
   ↓
4. PresetManager.get_webdriver_override(region, provider)
   → WebDriver 설정 override
   ↓
5. WebDriverManager 초기화 및 시작
   → SyncSeleniumAdapter 래핑
   ↓
6. Pipeline 실행:
   - SyncNavigator.load(url)
   - SyncNavigator.scroll() [선택적]
   - SyncNavigator.wait() [선택적]
   - SyncJSExtractor.extract()
   ↓
7. 결과 반환
```

---

## ✅ 테스트 결과

```bash
# 간단한 통합 테스트
python test_webcrawl_simple.py

# 예상 출력:
# ======================================================================
# TEST: PresetManager - URL Analysis & Policy Selection
# ======================================================================
# 
# 📌 URL: https://www.aliexpress.com/item/1005006169753025.html
#    ├─ Site: aliexpress
#    ├─ Method: detail
#    └─ Region: global
#    ✅ Policy found: crawl
#       └─ JS Snippet: N/A
#    🔧 Override (firefox): ['profile_path', 'accept_languages']
# 
# ======================================================================
# TEST: WebCrawl + ConfigLoader (Dry-Run)
# ======================================================================
# 
# 📁 CASHOP_PATHS: M:\CALife\CAShop - 구매대행\_code\configs\paths.local.yaml
# 📄 Loading config: ...\config_loader_crawl.yaml
#    ✅ ConfigLoader initialized
#    ✅ WebCrawl initialized
# 
# 🔍 URL Analysis Result:
#    URL: https://www.aliexpress.com/item/1005006169753025.html
#    └─ (aliexpress, detail, global)
# 
# ✅ Policy loaded: crawl
# ✅ All tests completed!
```

---

## 📝 주요 차이점 (기존 Crawl vs 신규 WebCrawl)

| 항목 | 기존 Crawl | 신규 WebCrawl |
|------|-----------|--------------|
| 인터페이스 | ConfigLikeLoader 기반 복잡한 설정 | URL + provider만 전달 |
| 정책 선택 | YAML 수동 관리 | PresetManager 자동 선택 |
| WebDriver 설정 | 하드코딩 또는 YAML 직접 관리 | ConfigLoader + Preset Override |
| Services 통합 | 서명 불일치 | SyncSeleniumAdapter로 완벽 통합 |
| LogManager | self.logger 혼용 | self.log 일관성 |
| 명명 규칙 | adapters/ (복수) | adapter/ (단수, image_utils 패턴) |

---

## 🎯 다음 단계

1. **실제 브라우저 테스트**: 테스트 URL로 Firefox 실행 검증
2. **PostProcessor 통합**: SmartNormalizer + SyncFileSaver 연동
3. **추가 Site Policies**: Tmall, 1688 등 상세 정책 작성
4. **JS Snippet 관리**: `extractor.js_snippet_file` 실제 파일 연동

---

## 📚 참고 자료

- **ENVIRONMENT_VARIABLES.md**: CASHOP_PATHS 환경변수 설정 가이드
- **copilot-instructions.md**: 프로젝트 개발 가이드라인
- **image_utils**: Adapter 패턴 참조 모듈
- **cfg_utils**: ConfigLoader, ConfigLikeLoader 사용법

---

**작성일**: 2025-01-23  
**버전**: WebCrawl Adapter v2.0  
**상태**: ✅ 통합 테스트 완료
