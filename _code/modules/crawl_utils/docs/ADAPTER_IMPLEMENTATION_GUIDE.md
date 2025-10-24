# Crawl Adapter 구현 가이드 (v2.0)

## 📋 구현 개요

Crawl Adapter를 리팩토링하여 PreProcessor → Extract → PostProcessor pipeline을 구현합니다.

---

## 🏗️ 클래스 구조

### Crawl (adapter/crawl.py)

```python
class Crawl:
    """Crawl Adapter - 순수 크롤링 로직 (WebDriver 크롤링만 담당)
    
    Pipeline:
    1. PreProcessor: URL 분석, 페이지 로드, 스크롤
    2. Extract: JS snippet 실행 → Dict 반환
    3. PostProcessor: Dict → NormalizedItem → 파일 저장
    
    Services (재사용):
    - UrlAnalyzer: URL → site/method 추출
    - SyncNavigator: 페이지 로드, 스크롤
    - SyncJSExtractor: JS snippet 실행
    - SmartNormalizer: Dict → NormalizedItem (자동 타입 추론)
    - SyncFileSaver: NormalizedItem → 파일 저장
    """
    
    def __init__(self, cfg_like, *, log_manager=None, **overrides):
        self.policy = self._load_config(cfg_like, **overrides)
        self.log = self._setup_logger(log_manager)
        
        # Services (Lazy-load)
        self._url_analyzer = None
        self._navigator = None
        self._extractor = None
        self._normalizer = None
        self._saver = None
    
    def run(self, urls: List[str], **runtime_context) -> Dict[str, Any]:
        """크롤링 실행 (핵심 API)
        
        Args:
            urls: 크롤링할 URL 리스트
            **runtime_context: 런타임 컨텍스트 (cas_no 등)
        
        Returns:
            {
                "extracted_data": List[Dict],  # JS snippet 결과
                "normalized_items": List[NormalizedItem],
                "saved_files": List[Path],
                "summary": {...}
            }
        """
        # 1. PreProcessor: URL 분석
        site, method = self._analyze_urls(urls)
        
        # 2. Extract: 메서드별 크롤링
        extracted_data = self._crawl_by_method(urls, method, runtime_context)
        
        # 3. PostProcessor: 정규화 및 저장
        saved_files = self._post_process(extracted_data, runtime_context)
        
        return {
            "extracted_data": extracted_data,
            "saved_files": saved_files,
            "summary": {...}
        }
```

---

## 📦 Services 재사용 계획

### 1. UrlAnalyzer (services/url_analyzer.py)
- ✅ 재사용: 그대로 사용
- 역할: URL → (site, method) 추출
- 호출: `_analyze_urls()` 메서드

### 2. SyncNavigator (services/navigator.py)
- ✅ 재사용: 그대로 사용
- 역할: 페이지 로드, 스크롤
- 호출: `_crawl_detail()`, `_crawl_search()` 메서드

### 3. SyncJSExtractor (services/sync_extractor.py)
- ✅ 재사용: 그대로 사용
- 역할: JS snippet 실행 → Dict 반환
- 호출: `_extract_data()` 메서드

### 4. SmartNormalizer (services/smart_normalizer.py)
- ⚠️ 개선 필요: runtime_context 지원
- 역할: Dict → NormalizedItem (자동 타입 추론)
- 호출: `_normalize_data()` 메서드

**개선 사항:**
```python
# services/smart_normalizer.py
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
        # 템플릿 변수 결합
        template_vars = {
            **extracted,  # JS 결과: title, price 등
            **(runtime_context or {})  # 런타임: cas_no 등
        }
        
        # fso_name_policy 템플릿 렌더링
        name_hint = self._render_template(
            template=rule.fso_name_policy.get("prefix", ""),
            context=template_vars
        )
```

### 5. SyncFileSaver (services/saver.py)
- ⚠️ 개선 필요: PostProcessorPolicy 지원
- 역할: NormalizedItem → 파일 저장
- 호출: `_save_files()` 메서드

**개선 사항:**
```python
# services/saver.py
class SyncFileSaver:
    def __init__(self, policy: PostProcessorPolicy):  # ✨ 변경
        self.policy = policy
    
    def save_many(
        self,
        items: List[NormalizedItem],
        runtime_context: Optional[Dict] = None  # ✨ 추가
    ) -> SaveSummary:
        """
        Args:
            runtime_context: 런타임 컨텍스트 (dynamic_subdir 템플릿용)
        """
        # dynamic_subdir 템플릿 렌더링
        subdir = self._render_template(
            template=rule.dynamic_subdir or "",
            context=runtime_context or {}
        )
```

---

## 🔄 Pipeline 구현 상세

### Phase 1: PreProcessor (URL 분석)

```python
def _analyze_urls(self, urls: List[str]) -> Tuple[str, str]:
    """URL 분석 → site/method 추출
    
    Returns:
        (site, method) - 예: ("aliexpress", "detail")
    """
    if not urls:
        raise ValueError("No URLs provided")
    
    # UrlAnalyzer로 첫 번째 URL 분석
    site, method = self.url_analyzer.analyze(urls[0])
    
    # policy 업데이트 (auto-detection)
    self.policy.site = site
    self.policy.method = method
    
    self.log.info(f"Auto-detected: site='{site}', method='{method}'")
    
    return site, method
```

### Phase 2: Extract (JS snippet 실행)

```python
def _crawl_by_method(
    self,
    urls: List[str],
    method: str,
    runtime_context: Dict
) -> List[Dict[str, Any]]:
    """메서드별 크롤링 브랜칭
    
    Args:
        urls: 크롤링할 URL 리스트
        method: "detail" 또는 "search"
        runtime_context: 런타임 컨텍스트
    
    Returns:
        List of extracted data dictionaries
    """
    if method == "detail":
        return self._crawl_detail(urls, runtime_context)
    elif method == "search":
        return self._crawl_search(urls, runtime_context)
    else:
        raise ValueError(f"Unknown method: {method}")

def _crawl_detail(self, urls: List[str], runtime_context: Dict) -> List[Dict]:
    """상품 상세 페이지 크롤링
    
    기존 CrawlProductDetail 로직 통합
    """
    results = []
    
    for url in urls:
        try:
            # 1. 페이지 로드
            self.navigator.goto(url)
            
            # 2. 스크롤 (무한 스크롤 페이지)
            if self.policy.scroll.strategy != "none":
                self.navigator.scroll(
                    strategy=self.policy.scroll.strategy,
                    max_scrolls=self.policy.scroll.max_scrolls
                )
            
            # 3. Wait (이미지 로드 대기)
            if self.policy.wait.hook != "none":
                self.navigator.wait(
                    selector=self.policy.wait.selector,
                    timeout=self.policy.wait.timeout_sec
                )
            
            # 4. JS snippet 실행
            extracted = self.extractor.extract()
            
            results.append(extracted)
            
        except Exception as e:
            self.log.error(f"Failed to crawl {url}: {e}")
            continue
    
    return results
```

### Phase 3: PostProcessor (정규화 + 저장)

```python
def _post_process(
    self,
    extracted_data: List[Dict],
    runtime_context: Dict
) -> List[Path]:
    """정규화 및 저장
    
    Args:
        extracted_data: JS snippet 결과
        runtime_context: 런타임 컨텍스트 (cas_no 등)
    
    Returns:
        List of saved file paths
    """
    if not self.policy.post_processor:
        self.log.info("No post_processor configured, skipping")
        return []
    
    # 1. 정규화 (Dict → NormalizedItem)
    normalized_items = self._normalize_data(extracted_data, runtime_context)
    
    # 2. 저장 (NormalizedItem → 파일)
    saved_files = self._save_files(normalized_items, runtime_context)
    
    return saved_files

def _normalize_data(
    self,
    extracted_data: List[Dict],
    runtime_context: Dict
) -> List[NormalizedItem]:
    """Dict → NormalizedItem 변환
    
    SmartNormalizer 또는 DataNormalizer 사용
    """
    if self.policy.post_processor.use_smart_normalizer:
        # SmartNormalizer (자동 타입 추론)
        return self.normalizer.normalize_many(
            records=extracted_data,
            runtime_context=runtime_context
        )
    else:
        # DataNormalizer (Rule 기반)
        return self.data_normalizer.normalize(
            records=extracted_data
        )

def _save_files(
    self,
    normalized_items: List[NormalizedItem],
    runtime_context: Dict
) -> List[Path]:
    """NormalizedItem → 파일 저장
    
    SyncFileSaver 사용
    """
    save_summary = self.saver.save_many(
        items=normalized_items,
        runtime_context=runtime_context
    )
    
    saved_paths = save_summary.all_paths()
    
    self.log.success(f"Saved {len(saved_paths)} files")
    
    return saved_paths
```

---

## ✅ 구현 체크리스트

### Phase 1: Services 개선
- [ ] SmartNormalizer.normalize()에 runtime_context 인자 추가
- [ ] SmartNormalizer에 템플릿 렌더링 메서드 추가 (`_render_template()`)
- [ ] SyncFileSaver.__init__()에 PostProcessorPolicy 지원 추가
- [ ] SyncFileSaver.save_many()에 runtime_context 인자 추가
- [ ] SyncFileSaver에 dynamic_subdir 템플릿 렌더링 추가

### Phase 2: Crawl Adapter 리팩토링
- [ ] `_analyze_urls()` 메서드 구현
- [ ] `_crawl_by_method()` 메서드 구현
- [ ] `_crawl_detail()` 메서드 구현 (기존 CrawlProductDetail 로직 통합)
- [ ] `_crawl_search()` 메서드 구현 (기존 CrawlProductSearch 로직 통합)
- [ ] `_post_process()` 메서드 구현
- [ ] `_normalize_data()` 메서드 구현
- [ ] `_save_files()` 메서드 구현

### Phase 3: Properties (Lazy-load)
- [ ] `url_analyzer` property 구현
- [ ] `navigator` property 구현
- [ ] `extractor` property 구현
- [ ] `normalizer` property 구현
- [ ] `saver` property 구현

---

## 🔍 다음 단계

1. ✅ SmartNormalizer 개선 (runtime_context 지원)
2. ✅ SyncFileSaver 개선 (PostProcessorPolicy 지원)
3. ✅ Crawl Adapter 리팩토링 (Pipeline 구현)
4. ⏳ 테스트 작성 (Mock HTML 기반)

---

**작성일:** 2025-10-23  
**작성자:** GitHub Copilot
