# Crawl 설계 V4.0 (최종 확정)

## 📋 핵심 변경 사항 (V3 → V4)

### 1. Preset 구조 세분화 ✅
```
presets/
├── sites/              # Site별 크롤링 정책
│   ├── domains.py      # 도메인 → site 매핑
│   ├── methods.py      # URL 패턴 → method 매핑
│   ├── aliexpress_detail.py
│   └── taobao_detail.py
├── webdrivers/         # 지역별 WebDriver 정책
│   ├── china.py        # 중국 지역 (Taobao, Tmall, 1688)
│   ├── global.py       # 글로벌 지역 (AliExpress)
│   └── korea.py        # 한국 지역 (향후)
└── __init__.py         # PresetManager
```

### 2. Domain → Region(WebDriver) 매핑 ✅
- **문제:** URL 도메인에 따라 적절한 WebDriver region 선택 필요
- **해결:** domains.py에 domain → region 매핑 추가
- **예시:**
  ```python
  DOMAIN_MAPPING = {
      "aliexpress": {
          "domains": ["aliexpress.com", ...],
          "region": "global"  # ← WebDriver region
      },
      "taobao": {
          "domains": ["taobao.com", ...],
          "region": "china"
      }
  }
  ```

### 3. Crawl 인자 확장 ✅
- **기존:** `run(urls, **runtime_context)`
- **신규:** `run(urls, provider="firefox", **runtime_context)`
- **사용:**
  ```python
  crawl = Crawl()
  crawl.run(
      urls=["https://taobao.com/item/123.htm"],
      provider="firefox",  # WebDriver provider
      cas_no="12345"       # runtime_context
  )
  ```

### 4. URL + Provider → WebDriver 정책 선택 ✅
```python
# 1. URL 분석 → site, method, region
url = "https://taobao.com/item/123.htm"
site = "taobao"           # domains.py
method = "detail"         # methods.py
region = "china"          # domains.py (DOMAIN_MAPPING[site]["region"])

# 2. WebDriver 정책 선택
provider = "firefox"
webdriver_policy = presets.webdrivers.china.CHINA_FIREFOX_POLICY

# 3. Crawl 정책 선택
crawl_policy = presets.sites.taobao_detail.TAOBAO_DETAIL_POLICY

# 4. 정책 병합 → Crawl 실행
```

---

## 🏗️ 재설계된 Preset 구조

### 파일 구조
```
presets/
├── sites/                          # Site별 크롤링 정책
│   ├── __init__.py
│   ├── domains.py                  # 도메인 → site, region 매핑
│   ├── methods.py                  # URL 패턴 → method 매핑
│   ├── aliexpress_detail.py        # AliExpress Detail 정책
│   ├── taobao_detail.py            # Taobao Detail 정책
│   └── ...
├── webdrivers/                     # 지역별 WebDriver 정책
│   ├── __init__.py
│   ├── china.py                    # 중국 지역 (Firefox, Chrome)
│   ├── global.py                   # 글로벌 지역 (Firefox, Chrome)
│   └── ...
└── __init__.py                     # PresetManager
```

---

## 📦 Preset 파일 상세

### 1. presets/sites/domains.py
```python
# 도메인 → site, region 매핑

DOMAIN_MAPPING = {
    "aliexpress": {
        "domains": [
            "aliexpress.com",
            "aliexpress.ru",
            "aliexpress.us",
            "ae01.alicdn.com",
        ],
        "region": "global",  # WebDriver region
    },
    
    "taobao": {
        "domains": [
            "taobao.com",
            "world.taobao.com",
            "item.taobao.com",
        ],
        "region": "china",
    },
    
    "tmall": {
        "domains": [
            "tmall.com",
            "detail.tmall.com",
        ],
        "region": "china",
    },
    
    "1688": {
        "domains": [
            "1688.com",
            "detail.1688.com",
        ],
        "region": "china",
    },
}
```

### 2. presets/sites/methods.py
```python
# URL 패턴 → method 매핑

METHOD_PATTERNS = {
    "detail": [
        "/item/",
        "/i/",
        ".htm",
        ".html",
        "/product/",
        "/detail/",
        "/goods/",
    ],
    
    "search": [
        "/category/",
        "/search",
        "/wholesale/",
        "/w/wholesale",
        "/s?",
        "/search?",
    ],
}
```

### 3. presets/webdrivers/china.py
```python
# 중국 지역 WebDriver 정책

CHINA_FIREFOX_POLICY = {
    "provider": "firefox",
    "region": "china",
    
    "firefox": {
        "profile_path": "M:/Firefox_Profile/CRAWL_CHINA",
        "use_webdriver_manager": True,
        "binary_location": None,
        "preferences": {
            "intl.accept_languages": "zh-CN,zh,en-US,en",
            "general.useragent.locale": "zh-CN",
        },
        "options": [
            "--disable-blink-features=AutomationControlled",
        ],
    },
    
    "log": {
        "enabled": True,
        "log_level": "INFO",
    }
}

CHINA_CHROME_POLICY = {
    "provider": "chrome",
    "region": "china",
    
    "chrome": {
        "profile_path": "M:/Chrome_Profile/CRAWL_CHINA",
        # ...
    },
}
```

### 4. presets/webdrivers/global.py
```python
# 글로벌 지역 WebDriver 정책

GLOBAL_FIREFOX_POLICY = {
    "provider": "firefox",
    "region": "global",
    
    "firefox": {
        "profile_path": "M:/Firefox_Profile/CRAWL_GLOBAL",
        "use_webdriver_manager": True,
        "binary_location": None,
        "preferences": {
            "intl.accept_languages": "en-US,en,ko",
            "general.useragent.locale": "en-US",
        },
        "options": [
            "--disable-blink-features=AutomationControlled",
        ],
    },
    
    "log": {
        "enabled": True,
        "log_level": "INFO",
    }
}
```

---

## 🔄 PresetManager V4.0

### presets/__init__.py

```python
from typing import Dict, Any, Optional, Tuple

from .sites.domains import DOMAIN_MAPPING
from .sites.methods import METHOD_PATTERNS
from .sites.aliexpress_detail import ALIEXPRESS_DETAIL_POLICY
from .sites.taobao_detail import TAOBAO_DETAIL_POLICY

from .webdrivers.china import CHINA_FIREFOX_POLICY, CHINA_CHROME_POLICY
from .webdrivers.global import GLOBAL_FIREFOX_POLICY, GLOBAL_CHROME_POLICY


class PresetManager:
    """Preset 관리 클래스 V4.0
    
    주요 기능:
    1. URL 분석 → (site, method, region)
    2. (site, method) → 크롤링 정책 선택
    3. (region, provider) → WebDriver 정책 선택
    4. 정책 동적 등록 및 확장
    """
    
    def __init__(self):
        # 도메인 매핑
        self.domain_mapping = DOMAIN_MAPPING
        
        # 메서드 패턴
        self.method_patterns = METHOD_PATTERNS
        
        # 크롤링 정책 {(site, method): policy}
        self.crawl_policies = {
            ("aliexpress", "detail"): ALIEXPRESS_DETAIL_POLICY,
            ("taobao", "detail"): TAOBAO_DETAIL_POLICY,
        }
        
        # WebDriver 정책 {(region, provider): policy}
        self.webdriver_policies = {
            ("china", "firefox"): CHINA_FIREFOX_POLICY,
            ("china", "chrome"): CHINA_CHROME_POLICY,
            ("global", "firefox"): GLOBAL_FIREFOX_POLICY,
            ("global", "chrome"): GLOBAL_CHROME_POLICY,
        }
    
    def analyze_url(self, url: str) -> Tuple[str, str, str]:
        """URL 분석 → (site, method, region)
        
        Args:
            url: 크롤링할 URL
        
        Returns:
            (site, method, region)
            - site: "aliexpress", "taobao" 등
            - method: "detail", "search" 등
            - region: "global", "china" 등
        
        Example:
            >>> manager = PresetManager()
            >>> site, method, region = manager.analyze_url("https://taobao.com/item/123.htm")
            >>> print(site, method, region)
            ('taobao', 'detail', 'china')
        """
        url_lower = url.lower()
        
        # 1. Site + Region 추출
        site = None
        region = None
        for site_name, config in self.domain_mapping.items():
            if any(domain in url_lower for domain in config["domains"]):
                site = site_name
                region = config["region"]
                break
        
        if not site or not region:
            raise ValueError(f"Cannot identify site/region from URL: {url}")
        
        # 2. Method 추출
        method = None
        for method_name, patterns in self.method_patterns.items():
            if any(pattern in url_lower for pattern in patterns):
                method = method_name
                break
        
        if not method:
            raise ValueError(f"Cannot identify method from URL: {url}")
        
        return site, method, region
    
    def get_crawl_policy(self, site: str, method: str) -> Optional[Dict[str, Any]]:
        """크롤링 정책 로드
        
        Args:
            site: Site identifier
            method: Method identifier
        
        Returns:
            Crawl policy dict or None
        """
        return self.crawl_policies.get((site, method))
    
    def get_webdriver_policy(
        self,
        region: str,
        provider: str
    ) -> Optional[Dict[str, Any]]:
        """WebDriver 정책 로드
        
        Args:
            region: Region identifier ("global", "china", etc.)
            provider: Provider identifier ("firefox", "chrome", etc.)
        
        Returns:
            WebDriver policy dict or None
        
        Example:
            >>> manager = PresetManager()
            >>> policy = manager.get_webdriver_policy("china", "firefox")
            >>> print(policy["firefox"]["profile_path"])
            'M:/Firefox_Profile/CRAWL_CHINA'
        """
        return self.webdriver_policies.get((region, provider))
```

---

## 🔧 Crawl Adapter V4.0 구현

### adapter/crawl.py

```python
class Crawl:
    """Crawl Adapter V4.0
    
    URL + Provider 기반 자동 정책 선택:
    1. URL 분석 → (site, method, region)
    2. WebDriver 정책 선택 (region, provider)
    3. Crawl 정책 선택 (site, method)
    4. WebDriver 초기화 → 크롤링 실행
    """
    
    def __init__(self, cfg_like=None, **overrides):
        # PresetManager
        self.preset_manager = PresetManager()
        
        # Base policy (선택사항)
        self.base_policy = self._load_config(cfg_like, **overrides)
        
        # LogManager
        self.log = self._setup_logger()
        
        # WebDriver 인스턴스 (Lazy-load)
        self._webdriver = None
    
    def run(
        self,
        urls: List[str],
        provider: str = "firefox",
        **runtime_context
    ) -> Dict[str, Any]:
        """크롤링 실행
        
        Args:
            urls: 크롤링할 URL 리스트
            provider: WebDriver provider ("firefox", "chrome")
            **runtime_context: 런타임 컨텍스트 (cas_no 등)
        
        Returns:
            {
                "extracted_data": List[Dict],
                "saved_files": List[Path],
                "summary": {...}
            }
        
        Example:
            >>> crawl = Crawl()
            >>> results = crawl.run(
            ...     urls=["https://taobao.com/item/123.htm"],
            ...     provider="firefox",
            ...     cas_no="12345"
            ... )
        """
        all_results = []
        all_saved_files = []
        
        # URL마다 처리
        for url in urls:
            try:
                # 1. URL 분석
                site, method, region = self.preset_manager.analyze_url(url)
                self.log.info(f"URL: {url}")
                self.log.info(f"  → site='{site}', method='{method}', region='{region}'")
                
                # 2. WebDriver 정책 선택
                webdriver_policy = self.preset_manager.get_webdriver_policy(
                    region, provider
                )
                if not webdriver_policy:
                    raise ValueError(f"No WebDriver policy for ({region}, {provider})")
                
                # 3. Crawl 정책 선택
                crawl_policy = self.preset_manager.get_crawl_policy(site, method)
                if not crawl_policy:
                    raise ValueError(f"No Crawl policy for ({site}, {method})")
                
                # 4. WebDriver 초기화 (region별 정책 적용)
                if not self._webdriver or self._current_region != region:
                    self._init_webdriver(webdriver_policy)
                    self._current_region = region
                
                # 5. 크롤링 실행 (단일 URL)
                result = self._crawl_single_url(
                    url=url,
                    crawl_policy=crawl_policy,
                    runtime_context=runtime_context
                )
                
                all_results.append(result["extracted_data"])
                all_saved_files.extend(result["saved_files"])
                
            except Exception as e:
                self.log.error(f"Failed to crawl {url}: {e}")
                continue
        
        return {
            "extracted_data": all_results,
            "saved_files": all_saved_files,
            "summary": {
                "total_urls": len(urls),
                "success_urls": len(all_results),
                "saved_files_count": len(all_saved_files)
            }
        }
    
    def _init_webdriver(self, webdriver_policy: Dict[str, Any]) -> None:
        """WebDriver 초기화 (region별 정책 적용)
        
        Args:
            webdriver_policy: WebDriver 정책 dict
        """
        from ..adapter.webdriver_manager import WebDriverManager
        
        # 기존 WebDriver 종료
        if self._webdriver:
            self._webdriver.quit()
        
        # 새 WebDriver 생성 (정책 주입)
        self._webdriver = WebDriverManager(cfg_like=webdriver_policy)
        self._webdriver.start()
        
        self.log.info(f"WebDriver initialized: {webdriver_policy['region']}")
    
    def _crawl_single_url(
        self,
        url: str,
        crawl_policy: Dict[str, Any],
        runtime_context: Dict
    ) -> Dict[str, Any]:
        """단일 URL 크롤링
        
        Args:
            url: 크롤링할 URL
            crawl_policy: Crawl 정책 dict
            runtime_context: 런타임 컨텍스트
        
        Returns:
            {"extracted_data": Dict, "saved_files": List[Path]}
        """
        # CrawlPolicy 생성
        from ..core.policy import CrawlPolicy
        policy = CrawlPolicy(**crawl_policy)
        
        # Navigator, Extractor 생성
        navigator = self._create_navigator(policy)
        extractor = self._create_extractor(policy)
        
        # PreProcessor: 페이지 로드
        navigator.goto(url)
        
        if policy.scroll.strategy != "none":
            navigator.scroll(
                strategy=policy.scroll.strategy,
                max_scrolls=policy.scroll.max_scrolls
            )
        
        if policy.wait.hook != "none":
            navigator.wait(
                selector=policy.wait.selector,
                timeout=policy.wait.timeout_sec
            )
        
        # Extract: JS snippet 실행
        extracted_data = extractor.extract()
        
        # PostProcessor: 정규화 및 저장
        saved_files = []
        if policy.post_processor:
            saved_files = self._post_process(
                extracted_data, policy.post_processor, runtime_context
            )
        
        return {
            "extracted_data": extracted_data,
            "saved_files": saved_files
        }
```

---

## 📝 핵심 포인트 정리

### 1. Preset 구조 세분화 ✅
- `presets/sites/`: 크롤링 정책 (domains.py, methods.py, site별 정책)
- `presets/webdrivers/`: WebDriver 정책 (지역별, provider별)

### 2. Domain → Region 매핑 ✅
- `domains.py`: 도메인 → site, region 매핑
- 예: `taobao.com` → `site="taobao"`, `region="china"`

### 3. URL + Provider → 정책 선택 ✅
```python
# URL 분석
site, method, region = analyze_url(url)

# WebDriver 정책
webdriver_policy = get_webdriver_policy(region, provider)

# Crawl 정책
crawl_policy = get_crawl_policy(site, method)
```

### 4. WebDriver 지역별 정책 Override ✅
- 중국 지역: `CRAWL_CHINA` 프로필, 중국어 locale
- 글로벌 지역: `CRAWL_GLOBAL` 프로필, 영어 locale

---

## 🎯 다음 단계

1. ✅ presets/sites/ 디렉토리 생성 및 파일 작성
2. ✅ presets/webdrivers/ 디렉토리 생성 및 파일 작성
3. ✅ PresetManager V4.0 구현
4. ✅ Crawl Adapter V4.0 구현
5. ⏳ 테스트 작성

---

**작성일:** 2025-10-23  
**작성자:** GitHub Copilot
