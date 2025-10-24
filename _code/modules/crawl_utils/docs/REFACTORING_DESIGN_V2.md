# crawl_utils 리팩토링 설계 v2.0

## 📋 개요

**목표:** crawl_utils를 image_utils 패턴에 맞춰 Adapter/EntryPoint 구조로 리팩토링하되, 기존 서비스 클래스들을 재활용하고 SRP를 준수합니다.

**핵심 원칙:**
1. ✅ **WebDriver Crawling vs Session 후처리 명확 구분**
2. ✅ **JS_snippet 우선 진행, DOM 향후 확장**
3. ✅ **cfg_utils 최신 버전 적용**
4. ✅ **fso_utils 정책 활용한 파일 관리**
5. ✅ **YAML 기반 적극적 정책 설립**
6. ✅ **공통 모듈 적극 활용 (data_utils, fso_utils, image_utils, cfg_utils, structured_data, structured_io)**

---

## 🏗️ 기존 구조 분석

### 현재 crawl_utils 구조:

```
crawl_utils/
├── adapter/
│   ├── crawl.py                    # Crawl Adapter (비즈니스 로직)
│   └── webdriver_manager.py        # WebDriver 관리
├── entry_point/
│   └── crawler.py                  # Crawler EntryPoint
├── core/
│   ├── policy.py                   # CrawlPolicy, CrawlerPolicy
│   ├── models.py                   # NormalizedItem, SavedArtifact 등
│   └── interfaces.py               # Protocol 정의
├── services/
│   ├── url_analyzer.py             # URL 분석 (site/method 추출)
│   ├── method_resolver.py          # Preset 선택 로직
│   ├── navigator.py                # 페이지 네비게이션 (SyncNavigator)
│   ├── sync_extractor.py           # 데이터 추출 (SyncJSExtractor, SyncDOMExtractor)
│   ├── normalizer.py               # Rule 기반 정규화 (DataNormalizer)
│   ├── smart_normalizer.py         # 자동 타입 추론 정규화 (SmartNormalizer)
│   ├── saver.py                    # 파일 저장 (SyncFileSaver - fso_utils 활용)
│   ├── fetcher.py                  # HTTP 리소스 다운로드 (SyncHTTPFetcher)
│   └── crawl_methods.py            # 메서드별 크롤링 (CrawlProductDetail, CrawlProductSearch)
└── configs/
    ├── crawl.yaml                  # URL → site/method 매핑
    ├── crawl_site_aliexpress_detail.yaml
    ├── crawl_site_aliexpress_search.yaml
    ├── crawl_site_taobao_detail.yaml
    └── crawl_site_taobao_search.yaml
```

### 기존 클래스 역할 정리:

| 클래스 | 역할 | 위치 | 재사용 여부 |
|--------|------|------|-------------|
| `UrlAnalyzer` | URL → site/method 추출 | services/ | ✅ 재사용 |
| `SyncNavigator` | 페이지 로드, 스크롤 | services/ | ✅ 재사용 |
| `SyncJSExtractor` | JS snippet 실행 → Dict 추출 | services/ | ✅ 재사용 |
| `SyncDOMExtractor` | DOM 선택자 → Dict 추출 | services/ | ✅ 재사용 (향후) |
| `SmartNormalizer` | Dict → NormalizedItem (자동 추론) | services/ | ✅ 재사용 |
| `DataNormalizer` | Dict → NormalizedItem (Rule 기반) | services/ | ⚠️ 통합 검토 |
| `SyncFileSaver` | NormalizedItem → 파일 저장 | services/ | ✅ 재사용 (PostProcessor로) |
| `SyncHTTPFetcher` | URL → bytes 다운로드 | services/ | ✅ 재사용 |
| `CrawlProductDetail` | 상품 상세 크롤링 | services/ | ⚠️ Adapter 내부로 통합 |
| `CrawlProductSearch` | 상품 검색 크롤링 | services/ | ⚠️ Adapter 내부로 통합 |

---

## 🎯 리팩토링 설계

### 1. 클래스 구조 재설계

#### **PreProcessor / Extract / PostProcessor 통합 여부**

**결정: Adapter 내부에 Pipeline으로 통합 (image_utils 패턴)**

```python
# adapter/crawl.py
class Crawl:
    """Crawl Adapter - 순수 크롤링 로직 (WebDriver 크롤링만 담당)
    
    Pipeline:
    1. PreProcessor: URL 분석, 페이지 로드, 스크롤
    2. Extract: JS snippet 또는 DOM으로 데이터 추출 (Dict 반환)
    3. PostProcessor: Dict → NormalizedItem → 파일 저장
    
    책임:
    - URL 리스트를 받아 크롤링 실행
    - site/method 자동 감지 (UrlAnalyzer)
    - 메서드별 크롤링 로직 (Detail vs Search)
    - 추출된 데이터 정규화 및 저장
    - 저장된 파일 경로 반환
    """
    
    def __init__(self, cfg_like, *, log_manager=None, **overrides):
        # Policy 로드 (CrawlPolicy)
        self.policy = self._load_config(cfg_like, **overrides)
        
        # Services (Lazy-load)
        self._url_analyzer = None
        self._navigator = None
        self._extractor = None
        self._normalizer = None
        self._saver = None
    
    def run(self, urls: List[str], **runtime_context) -> Dict[str, Any]:
        """크롤링 실행 (Adapter의 핵심 API)
        
        Args:
            urls: 크롤링할 URL 리스트
            **runtime_context: 런타임 컨텍스트 (cas_no 등)
        
        Returns:
            {
                "extracted_data": List[Dict],  # JS snippet 결과
                "normalized_items": List[NormalizedItem],
                "saved_files": List[Path],  # 저장된 파일 경로
                "summary": {
                    "total_urls": int,
                    "success_urls": int,
                    "failed_urls": int,
                    "saved_files_count": int
                }
            }
        """
        results = {
            "extracted_data": [],
            "normalized_items": [],
            "saved_files": [],
            "summary": {}
        }
        
        # 1. PreProcessor: URL 분석
        site, method = self.url_analyzer.analyze(urls[0])
        
        # 2. 메서드별 크롤링 (Detail vs Search)
        if method == "detail":
            extracted_data = self._crawl_detail(urls, runtime_context)
        elif method == "search":
            extracted_data = self._crawl_search(urls, runtime_context)
        else:
            raise ValueError(f"Unknown method: {method}")
        
        results["extracted_data"] = extracted_data
        
        # 3. PostProcessor: 정규화 및 저장
        if self.policy.post_processor:
            normalized = self.normalizer.normalize_many(extracted_data)
            results["normalized_items"] = normalized
            
            save_summary = self.saver.save_many(normalized)
            results["saved_files"] = save_summary.all_paths()
        
        return results
```

**기존 클래스 재배치:**
- ✅ `UrlAnalyzer`, `SyncNavigator`, `SyncJSExtractor`: services/에서 재사용
- ✅ `SmartNormalizer`: services/에서 재사용 (PostProcessor로)
- ✅ `SyncFileSaver`: services/에서 재사용 (PostProcessor로)
- ⚠️ `CrawlProductDetail`, `CrawlProductSearch`: Adapter 내부 private 메서드로 통합
- ⚠️ `DataNormalizer`: SmartNormalizer와 통합 검토 (Rule vs 자동 추론)

---

### 2. Config 파일 구조

#### **YAML 파일 위치 및 역할**

**사용자 피드백 반영:**
- ✅ `crawl.yaml`, `crawl_test.yaml`: `modules/crawl_utils/configs/`에 위치
- ✅ WebDriver는 지역별 설정 관리 (기존 유지)
- ✅ Crawl은 site/method별 설정 관리

#### **Config Loader 전략**

```yaml
# configs/loader/config_loader_crawl.yaml
source:
  - src: ["{{configs_crawl_dir}}/crawl.yaml", "url_mapping"]
    yaml_parser:
      enable_env: true
  
  - src: ["{{configs_crawl_dir}}/crawl_site_{{site}}_{{method}}.yaml", "crawl"]
    yaml_parser:
      enable_env: true
    placeholder:
      site: "aliexpress"  # 런타임 오버라이드 가능
      method: "detail"
```

**파일 역할:**

1. **crawl.yaml**: URL → site/method 매핑
   ```yaml
   # crawl.yaml
   url_mapping:
     site_domains:
       aliexpress: ["aliexpress.com", "aliexpress.ru"]
       taobao: ["taobao.com", "world.taobao.com"]
     
     method_patterns:
       detail: ["/item/", ".htm"]
       search: ["/category/", "/search"]
   ```

2. **crawl_site_aliexpress_detail.yaml**: site=aliexpress, method=detail 전용 설정
   ```yaml
   # crawl_site_aliexpress_detail.yaml
   crawl:
     navigation:
       base_url: "https://www.aliexpress.com"
       page_param: "page"
       start_page: 1
       max_pages: 1
     
     scroll:
       strategy: "infinite"
       max_scrolls: 10
       scroll_pause_sec: 0.5
     
     wait:
       hook: "css"
       selector: ".product-image"
       timeout_sec: 10
     
     extractor:
       type: "js"
       js_snippet: |
         return {
           images: Array.from(document.querySelectorAll('.product-image img')).map(img => img.src),
           title: document.querySelector('.product-title').innerText,
           price: document.querySelector('.product-price').innerText
         };
     
     post_processor:
       target_dir: "{{output_dir}}/crawl"
       rules:
         - kind: "image"
           source: "images"
           fso_name_policy:
             prefix: "aliexpress"
             tail_mode: "counter"
             extension: "jpg"
   ```

3. **crawl_test.yaml**: 테스트 전용 설정
   ```yaml
   # crawl_test.yaml
   crawl:
     source:
       urls: ["file://test_data/mock_aliexpress_detail.html"]
       method: "detail"
     
     extractor:
       type: "js"
       js_snippet: |
         return {images: ["test1.jpg", "test2.jpg"]};
   ```

---

### 3. JS_snippet vs .js 파일 관리

#### **Preset 관리 방식 검토**

**질문:** Preset에 .js 파일 관리 시 이점은?

**분석:**
- **Option A: YAML inline** (현재 제안)
  - ✅ 설정이 한 곳에 집중 (가독성)
  - ✅ 간단한 snippet에 유리
  - ❌ 복잡한 JS 코드는 가독성 저하
  - ❌ 재사용 어려움

- **Option B: 별도 .js 파일**
  ```
  presets/
  ├── aliexpress/
  │   ├── detail.yaml       # extractor.js_snippet_file: "detail.js"
  │   └── detail.js
  ```
  - ✅ 복잡한 JS 코드 관리 용이
  - ✅ 재사용성 (여러 YAML에서 참조)
  - ✅ IDE 지원 (syntax highlight, lint)
  - ❌ 파일 분산 (관리 포인트 증가)

**결정: YAML inline 우선, 복잡한 경우 .js 파일 지원**

```yaml
# Option 1: inline (간단한 경우)
extractor:
  type: "js"
  js_snippet: |
    return {images: [...]};

# Option 2: 파일 참조 (복잡한 경우)
extractor:
  type: "js"
  js_snippet_file: "presets/aliexpress/detail.js"
```

**구현 시 우선순위:**
1. ✅ js_snippet inline 지원 (v1.0)
2. ⏳ js_snippet_file 지원 (v1.1 - 향후)

---

### 4. fso_utils 통합 방식

#### **PostProcessor에서 동적 파일 naming**

**사용자 요구사항:**
- ✅ JS 결과 아이템 내부 데이터를 사용한 동적 파일 naming
- ✅ 폴더명도 동적으로 설정 (외부 인자로)

**설계:**

```yaml
# crawl_site_aliexpress_detail.yaml
post_processor:
  target_dir: "{{output_dir}}/crawl/{{cas_no}}"  # 외부 인자 {{cas_no}}
  
  rules:
    - kind: "image"
      source: "images"  # KeyPath: JS 결과의 images 필드
      
      # 동적 파일명 (JS 결과 내부 데이터 사용)
      fso_name_policy:
        prefix: "{{item.title}}"  # JS 결과의 title 필드 사용
        suffix: "{{item.price}}"  # JS 결과의 price 필드 사용
        tail_mode: "counter"
        extension: "jpg"
      
      # 동적 폴더명 (런타임 인자 사용)
      dynamic_subdir: "{{cas_no}}/images"  # cas_no는 run() 인자
```

**구현 코드:**

```python
# services/smart_normalizer.py (개선)
class SmartNormalizer:
    def normalize(
        self,
        extracted: Dict[str, Any],
        *,
        section: str = "default",
        runtime_context: Optional[Dict] = None  # ✨ 추가
    ) -> List[NormalizedItem]:
        """
        Args:
            runtime_context: 런타임 컨텍스트 (cas_no 등)
                - 파일명/폴더명 템플릿에서 사용
        """
        # 템플릿 변수 결합 (JS 결과 + 런타임 컨텍스트)
        template_vars = {
            **extracted,  # JS 결과: title, price 등
            **(runtime_context or {})  # 런타임: cas_no 등
        }
        
        # fso_name_policy.prefix 템플릿 렌더링
        # "{{item.title}}" → "Nike Air Max"
        name_hint = self._render_template(
            template=rule.fso_name_policy.prefix,
            context=template_vars
        )
```

---

### 5. 테스트 전략

#### **Mock HTML 우선 진행**

```
_code/modules/crawl_utils/tests/
├── test_data/
│   ├── mock_aliexpress_detail.html
│   ├── mock_taobao_detail.html
│   └── mock_search_results.html
├── test_crawl_adapter.py
└── test_crawl_entry_point.py
```

**test_crawl_adapter.py:**
```python
# Adapter 단독 테스트 (Mock HTML)
def test_crawl_adapter_with_mock_html():
    # Mock HTML 파일 경로
    mock_url = "file://tests/test_data/mock_aliexpress_detail.html"
    
    # Crawl Adapter 생성
    crawl = Crawl(cfg_like={
        "extractor": {
            "type": "js",
            "js_snippet": "return {images: ['test.jpg']};"
        }
    })
    
    # 크롤링 실행
    results = crawl.run(urls=[mock_url])
    
    # 검증
    assert len(results["extracted_data"]) == 1
    assert results["extracted_data"][0]["images"] == ["test.jpg"]
```

---

## 🚀 구현 순서

### Phase 1: Core Policy 리팩토링
1. ✅ `CrawlPolicy` 개선 (PostProcessorPolicy 추가)
2. ✅ `PostProcessorRule` 설계 (fso_utils 통합)
3. ✅ 동적 파일명/폴더명 템플릿 지원

### Phase 2: Adapter 구현
1. ✅ `Crawl.run()` 메서드 구현 (Pipeline 통합)
2. ✅ `_crawl_detail()`, `_crawl_search()` 메서드 (기존 CrawlProductDetail 로직 통합)
3. ✅ PostProcessor 통합 (SmartNormalizer + SyncFileSaver)

### Phase 3: Config 파일 작성
1. ✅ `crawl.yaml` (URL 매핑)
2. ✅ `crawl_site_aliexpress_detail.yaml`
3. ✅ `crawl_site_taobao_detail.yaml`
4. ✅ `crawl_test.yaml` (Mock HTML 기반)

### Phase 4: 테스트
1. ✅ Mock HTML 파일 작성
2. ✅ `test_crawl_adapter.py` 작성
3. ✅ `test_crawl_entry_point.py` 작성

### Phase 5: 문서화
1. ✅ README 업데이트
2. ✅ 사용 예시 작성

---

## 📝 질문 4 답변: Preset 관리

**질문:** "Preset에 js 파일 관리 시 어떤 이점이 있는지? 코드 내부가 간단해지는지? 매핑 방식은 yaml에 파일이름을 주입하여 가능한지? 2번 질문과의 차이점이 뭔지?"

**답변:**

### Preset .js 파일 관리의 이점:

1. **복잡한 JS 코드 관리 용이**
   - YAML inline: 50줄 이상 JS 코드 시 가독성 저하
   - .js 파일: IDE 지원 (syntax highlight, lint, format)

2. **재사용성**
   - 여러 YAML에서 동일한 .js 파일 참조 가능
   - 예: `aliexpress/detail.js`를 여러 설정에서 공유

3. **버전 관리**
   - .js 파일 단위로 변경 이력 추적 용이
   - YAML inline은 diff 시 전체 블록 변경

### 코드 간단해지는지?

**Before (YAML inline):**
```yaml
extractor:
  type: "js"
  js_snippet: |
    // 50줄 JS 코드...
    return {...};
```

**After (.js 파일):**
```yaml
extractor:
  type: "js"
  js_snippet_file: "presets/aliexpress/detail.js"
```

→ ✅ YAML이 간단해지고, JS 코드는 별도 파일에서 IDE 지원 받음

### 매핑 방식:

```python
# adapter/crawl.py
def _load_js_snippet(self, extractor_policy):
    if extractor_policy.js_snippet:
        return extractor_policy.js_snippet
    elif extractor_policy.js_snippet_file:
        js_path = Path(extractor_policy.js_snippet_file)
        return js_path.read_text(encoding="utf-8")
    else:
        raise ValueError("js_snippet or js_snippet_file required")
```

### 2번 질문과의 차이점:

- **2번 (YAML inline 우선)**: 간단한 JS snippet은 YAML에 inline으로 유지
- **Preset .js 파일**: 복잡한 경우에만 .js 파일로 분리

→ **결론: 두 방식 모두 지원, YAML inline 우선 (v1.0), .js 파일 향후 지원 (v1.1)**

---

## 📌 핵심 결정 사항 요약

| 항목 | 결정 | 근거 |
|------|------|------|
| **PreProcessor/Extract/PostProcessor** | Adapter 내부 통합 | image_utils 패턴, SRP 준수하되 과도한 분리 지양 |
| **JS_snippet 관리** | YAML inline 우선, .js 파일 향후 지원 | 간단한 경우 inline, 복잡한 경우 파일 분리 |
| **fso_utils 통합** | PostProcessor에서 자동화 | 동적 파일명/폴더명 템플릿 지원 |
| **Config 위치** | `modules/crawl_utils/configs/` | 모듈 리팩토링에 집중 |
| **테스트** | Mock HTML 우선 | 빠르고 안정적인 테스트 |
| **기존 클래스** | services/ 재사용 | UrlAnalyzer, SyncNavigator, SyncJSExtractor, SmartNormalizer, SyncFileSaver 재사용 |

---

## 🎯 다음 단계

1. ✅ **Core Policy 리팩토링** (CrawlPolicy에 PostProcessorPolicy 추가)
2. ✅ **Adapter 구현** (Crawl.run() Pipeline 통합)
3. ✅ **Config YAML 작성** (crawl.yaml, crawl_site_*.yaml)
4. ✅ **테스트 작성** (Mock HTML 기반)
5. ✅ **문서화** (README 업데이트)

---

**작성일:** 2025-10-23  
**작성자:** GitHub Copilot (CAShop - 구매대행 프로젝트)
