# Crawl 설계 재조정 (사용자 피드백 반영)

## 📋 핵심 변경 사항

### 1. crawl_site_***.yaml에서 source 제거 ✅
- **문제:** source는 EntryPoint(Crawler)에서만 필요, Adapter에서는 불필요
- **해결:** crawl_site_***.yaml에서 source 섹션 제거
- **이유:** Adapter는 run(urls) 인자로 URL을 받음

### 2. URL 매핑을 .py로 관리 ✅
- **문제:** crawl_url_mapping.yaml을 별도로 읽는 것은 비효율적
- **해결:** presets/url_mapping.py로 Python dict로 관리
- **이유:** 
  - 코드 내부에서 직접 참조 (config_loader 불필요)
  - 유지보수 용이 (IDE 지원)
  - 동적 확장 가능

### 3. crawl_site_***.yaml의 역할 명확화 ✅
- **개념:** site + method 조합에 맞는 크롤링 정책
- **사용 시점:** ConfigLoader로 미리 로드 → Crawl Adapter에서 URL마다 적절한 정책 적용
- **예시:**
  ```python
  # ConfigLoader로 모든 site/method 정책 로드
  config = ConfigLoader("config_loader_crawl.yaml")
  
  # Crawl Adapter 생성 (모든 정책 보유)
  crawl = Crawl(config)
  
  # URL마다 적절한 정책 자동 선택
  crawl.run(["https://aliexpress.com/item/123"])  # → aliexpress_detail 정책 사용
  crawl.run(["https://taobao.com/item/456.htm"])  # → taobao_detail 정책 사용
  ```

### 4. Adapter 우선, Crawler는 향후 ⏳
- **Phase 1 (현재):** Adapter 구현 (run(urls) 인자로 URL 받음)
- **Phase 2 (향후):** Crawler 구현 (YAML에서 urls 읽음)
- **Crawler용 YAML 예시 (향후):**
  ```yaml
  # crawler_xlcrawl.yaml (프로젝트별)
  crawler:
    source:
      urls:
        - "https://aliexpress.com/item/123"
        - "https://taobao.com/item/456.htm"
    
    crawl:
      # crawl 설정은 config_loader에서 이미 로드됨
      # URL마다 자동으로 적절한 정책 선택
  ```

### 5. ConfigLoader Section 관리 재확인 ✅
- **현재 구조:**
  ```yaml
  # config_loader_crawl.yaml
  source:
    - src: ["configs/crawl_site_aliexpress_detail.yaml", "crawl"]
    - src: ["configs/crawl_site_taobao_detail.yaml", "crawl"]
  ```
- **문제:** 모든 파일이 동일한 section "crawl"을 사용 → 마지막 파일만 유효
- **해결 방안:**
  - Option A: 각 site/method를 별도 section으로 관리
  - Option B: 통합 preset 구조로 관리 (권장)

---

## 🏗️ 재설계된 구조

### 파일 구조
```
crawl_utils/
├── adapter/
│   └── crawl.py                    # Crawl Adapter (URL 인자로 받음)
├── entry_point/
│   └── crawler.py                  # Crawler EntryPoint (향후, YAML에서 URLs 읽음)
├── presets/
│   ├── url_mapping.py              # URL → site/method 매핑 (Python dict)
│   ├── aliexpress_detail.py        # AliExpress Detail 정책 (Python dict)
│   ├── taobao_detail.py            # Taobao Detail 정책
│   └── __init__.py                 # PresetManager 클래스
├── configs/
│   ├── config_loader_crawl.yaml    # ConfigLoader 설정 (향후 Crawler용)
│   └── crawl_test.yaml             # 테스트 전용
└── services/
    └── (기존 services 재사용)
```

### Preset 관리 (.py로 전환)

#### presets/url_mapping.py
```python
# presets/url_mapping.py
# URL → site/method 자동 매핑 설정

URL_MAPPING = {
    "site_domains": {
        "aliexpress": ["aliexpress.com", "aliexpress.ru", "aliexpress.us"],
        "taobao": ["taobao.com", "world.taobao.com", "item.taobao.com"],
        "tmall": ["tmall.com", "detail.tmall.com"],
        "1688": ["1688.com", "detail.1688.com"],
    },
    
    "method_patterns": {
        "detail": ["/item/", "/i/", ".htm", ".html", "/product/"],
        "search": ["/category/", "/search", "/wholesale/", "/w/wholesale"],
    }
}
```

#### presets/aliexpress_detail.py
```python
# presets/aliexpress_detail.py
# AliExpress Product Detail 크롤링 정책

ALIEXPRESS_DETAIL_POLICY = {
    "name": "crawl",
    "site": "aliexpress",
    "method": "detail",
    
    "scroll": {
        "strategy": "infinite",
        "max_scrolls": 15,
        "scroll_pause_sec": 1.0
    },
    
    "wait": {
        "hook": "css",
        "selector": "[class*='product'], .product-main",
        "timeout_sec": 25.0,
        "condition": "visibility"
    },
    
    "extractor": {
        "type": "js",
        "js_snippet": """
            const extractImages = () => {
                const images = [];
                document.querySelectorAll('.result-item img, .product-image img').forEach((img) => {
                    let url = img.getAttribute('data-src') || img.getAttribute('src') || '';
                    if (url.startsWith('//')) url = 'https:' + url;
                    if (/^https?:\/\//i.test(url)) images.push(url);
                });
                return images;
            };
            
            return {
                images: extractImages(),
                title: document.querySelector('.product-title-text, h1.product-title')?.innerText?.trim() || '',
                price: document.querySelector('.product-price-value')?.innerText?.trim() || '',
                category: document.querySelector('.breadcrumb-item:last-child')?.innerText?.trim() || 'uncategorized'
            };
        """
    },
    
    "post_processor": {
        "target_dir": "{{output_dir}}/crawl/aliexpress",
        "use_smart_normalizer": True,
        "rules": [
            {
                "kind": "image",
                "source": "images",
                "allow_empty": False,
                "dynamic_subdir": "{{cas_no}}/images",
                "fso_name_policy": {
                    "prefix": "ALI",
                    "tail_mode": "counter",
                    "counter_width": 3,
                    "extension": "jpg",
                    "sanitize": True,
                    "ensure_unique": True
                }
            }
        ]
    },
    
    "http_session": {
        "use_browser_headers": True,
        "headers": {
            "Accept-Language": "en-US,en;q=0.9,ko;q=0.8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    },
    
    "execution_mode": "sync",
    "concurrency": 1,
    "retries": 3,
    "retry_backoff_sec": 2.0,
    
    "log": {
        "enabled": True,
        "log_level": "INFO",
        "log_to_file": False
    }
}
```

#### presets/__init__.py (PresetManager)
```python
# presets/__init__.py
# Preset 관리 클래스

from typing import Dict, Any, Optional
from .url_mapping import URL_MAPPING
from .aliexpress_detail import ALIEXPRESS_DETAIL_POLICY
from .taobao_detail import TAOBAO_DETAIL_POLICY

class PresetManager:
    """Preset 관리 클래스
    
    URL → site/method 매핑 및 정책 로드를 담당합니다.
    """
    
    def __init__(self):
        self.url_mapping = URL_MAPPING
        self.policies = {
            ("aliexpress", "detail"): ALIEXPRESS_DETAIL_POLICY,
            ("taobao", "detail"): TAOBAO_DETAIL_POLICY,
            # 추가 site/method 조합...
        }
    
    def analyze_url(self, url: str) -> tuple[str, str]:
        """URL → (site, method) 추출
        
        Args:
            url: 크롤링할 URL
        
        Returns:
            (site, method) - 예: ("aliexpress", "detail")
        """
        # site 추출
        site = None
        for site_name, domains in self.url_mapping["site_domains"].items():
            if any(domain in url.lower() for domain in domains):
                site = site_name
                break
        
        # method 추출
        method = None
        for method_name, patterns in self.url_mapping["method_patterns"].items():
            if any(pattern in url.lower() for pattern in patterns):
                method = method_name
                break
        
        if not site or not method:
            raise ValueError(f"Cannot analyze URL: {url}")
        
        return site, method
    
    def get_policy(self, site: str, method: str) -> Optional[Dict[str, Any]]:
        """site/method에 맞는 정책 로드
        
        Args:
            site: Site identifier
            method: Method identifier
        
        Returns:
            Policy dict or None
        """
        return self.policies.get((site, method))
```

---

## 🔄 Crawl Adapter 구현 (재설계)

### adapter/crawl.py

```python
# adapter/crawl.py
from ..presets import PresetManager

class Crawl:
    """Crawl Adapter - URL마다 적절한 정책 자동 선택
    
    사용 예시:
        >>> crawl = Crawl()  # 기본 PresetManager 사용
        >>> results = crawl.run([
        ...     "https://aliexpress.com/item/123",
        ...     "https://taobao.com/item/456.htm"
        ... ], cas_no="12345")
    """
    
    def __init__(
        self,
        cfg_like: Optional[Any] = None,
        *,
        log_manager: Optional[LogManager] = None,
        **overrides
    ):
        # PresetManager 초기화
        self.preset_manager = PresetManager()
        
        # 기본 정책 (cfg_like로 오버라이드 가능)
        self.base_policy = self._load_config(cfg_like, **overrides)
        
        # LogManager
        self.log = self._setup_logger(log_manager)
    
    def run(self, urls: List[str], **runtime_context) -> Dict[str, Any]:
        """URL마다 적절한 정책을 자동 선택하여 크롤링
        
        Args:
            urls: 크롤링할 URL 리스트
            **runtime_context: 런타임 컨텍스트 (cas_no 등)
        
        Returns:
            {
                "extracted_data": List[Dict],
                "saved_files": List[Path],
                "summary": {...}
            }
        """
        all_results = []
        all_saved_files = []
        
        for url in urls:
            try:
                # 1. URL 분석 → site/method 추출
                site, method = self.preset_manager.analyze_url(url)
                self.log.info(f"URL: {url} → site='{site}', method='{method}'")
                
                # 2. site/method에 맞는 정책 로드
                policy_dict = self.preset_manager.get_policy(site, method)
                if not policy_dict:
                    self.log.warning(f"No policy for ({site}, {method}), skipping")
                    continue
                
                # 3. Policy 병합 (base_policy + preset_policy + overrides)
                merged_policy = self._merge_policies(
                    self.base_policy,
                    CrawlPolicy(**policy_dict)
                )
                
                # 4. 크롤링 실행 (단일 URL)
                result = self._crawl_single_url(url, merged_policy, runtime_context)
                
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
    
    def _crawl_single_url(
        self,
        url: str,
        policy: CrawlPolicy,
        runtime_context: Dict
    ) -> Dict[str, Any]:
        """단일 URL 크롤링 (정책 적용)
        
        Args:
            url: 크롤링할 URL
            policy: 적용할 CrawlPolicy
            runtime_context: 런타임 컨텍스트
        
        Returns:
            {"extracted_data": Dict, "saved_files": List[Path]}
        """
        # 기존 _crawl_detail() 로직 재사용
        # ...
```

---

## 📝 핵심 포인트 정리

### 1. source 제거 ✅
- crawl_site_***.yaml에서 source 섹션 제거
- Adapter는 run(urls) 인자로만 URL 받음

### 2. URL 매핑 .py 관리 ✅
- presets/url_mapping.py로 Python dict 관리
- ConfigLoader 불필요, 코드 내부에서 직접 참조

### 3. crawl_site_*** 역할 명확화 ✅
- site + method 조합별 크롤링 정책
- PresetManager에서 Python dict로 관리
- URL마다 적절한 정책 자동 선택

### 4. Adapter 우선, Crawler 향후 ⏳
- Phase 1: Adapter 구현 (run(urls) 인자)
- Phase 2: Crawler 구현 (YAML에서 urls 읽음)

### 5. ConfigLoader Section 관리 ✅
- **현재 방식 (YAML):** 마지막 파일만 유효 → 문제
- **신규 방식 (.py):** PresetManager에서 dict로 관리 → 해결

---

## 🎯 다음 단계

1. ✅ presets/ 디렉토리 생성
2. ✅ presets/url_mapping.py 작성
3. ✅ presets/aliexpress_detail.py 작성
4. ✅ presets/__init__.py (PresetManager) 작성
5. ✅ adapter/crawl.py 리팩토링 (PresetManager 통합)

---

**작성일:** 2025-10-23  
**작성자:** GitHub Copilot
