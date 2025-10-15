# 프로젝트 재구조화 계획

## 📋 현재 문제점

### 1️⃣ **역할 불명확**
- `scripts/` 폴더에 메인 스크립트, 테스트, 유틸리티가 혼재
- Service/Adapter/Runner 구분 없음
- 재사용 가능한 컴포넌트가 스크립트에 묶여있음

### 2️⃣ **파일 분류**

#### 현재 `scripts/` 내역:
```
📁 scripts/
├── 🚀 메인 스크립트 (실행용)
│   ├── xloto.py              # OTO 메인
│   ├── xlcrawl2.py           # Excel 크롤링 메인
│   └── oto.py                # OTO 구버전
│
├── 🔧 크롤링 도구 (Service로 이동 필요)
│   ├── crawl_session_managed.py   # SiteCrawler 클래스
│   └── crawl_two_step.py          # TwoStepCrawler 클래스
│
├── 🧪 테스트 파일
│   ├── test_js_snippet.py
│   ├── test_js_snippet_browser.py
│   ├── test_image_downloader.py
│   └── test_font_color_utils.py
│
├── ⚙️ 설정/유틸리티
│   ├── setup_env.py          # 환경 설정
│   └── paths.py              # 경로 유틸
│
└── 🗑️ 구버전/테스트
    ├── xlcrawl2_old.py
    ├── xlcrawl.py
    └── 0.TEST.py
```

---

## 🎯 재구조화 목표

### 분류 기준
1. **Main Scripts** (`scripts/`): 사용자가 직접 실행하는 엔트리포인트
2. **Services** (`modules/*/services/`): 비즈니스 로직, 재사용 가능한 클래스
3. **Adapters** (`modules/*/adapters/`): 외부 시스템 연동 (Excel, WebDriver 등)
4. **Utils** (`modules/*/utils/`): 헬퍼 함수, 유틸리티
5. **Tests** (`tests/`): 단위 테스트, 통합 테스트

---

## 📦 재구조화 계획

### Phase 1: 크롤링 관련 재구조화

#### 1️⃣ **Service 분리**

**이동: `crawl_session_managed.py` → `modules/crawl_utils/services/site_crawler.py`**
```python
# modules/crawl_utils/services/site_crawler.py
"""
사이트별 크롤링 Service

역할: 사이트별 검색/상세 크롤링 로직
의존성: CrawlPipeline, create_webdriver
재사용: 여러 메인 스크립트에서 호출 가능
"""

class SiteCrawler:
    """사이트별 크롤링 Service"""
    
    def crawl_search(self, query: str, max_pages: int) -> Path:
        """Step 1: 검색 결과 크롤링"""
        
    def crawl_detail(self, url: str) -> Dict:
        """Step 2: 상세 페이지 크롤링"""
        
    def crawl_detail_batch(self, urls: List[str]):
        """Step 2: 배치 크롤링"""
```

**이동: `manual_filter_urls()` → `modules/crawl_utils/utils/filter_utils.py`**
```python
# modules/crawl_utils/utils/filter_utils.py
"""
크롤링 결과 필터링 유틸리티

역할: 검색 결과 수동 선택, URL 필터링
"""

def manual_filter_urls(search_output_dir: Path) -> List[str]:
    """수동 필터링 UI"""

def filter_by_price(urls: List[str], min_price: float, max_price: float) -> List[str]:
    """가격 필터링"""
```

#### 2️⃣ **Adapter 분리**

**신규: `modules/xl_utils/adapters/crawl_adapter.py`**
```python
# modules/xl_utils/adapters/crawl_adapter.py
"""
Excel ↔ Crawl 연동 Adapter

역할: Excel에서 URL 추출, 결과를 Excel에 저장
의존성: XlController, SiteCrawler
"""

class XlCrawlAdapter:
    """Excel + 크롤링 통합"""
    
    def extract_urls_from_excel(self, sheet: str, column: str) -> List[str]:
        """Excel에서 URL 추출"""
    
    def update_download_status(self, urls: List[str], status: str):
        """다운로드 상태 업데이트"""
```

#### 3️⃣ **메인 스크립트 간소화**

**간소화: `scripts/xlcrawl2.py`**
```python
# scripts/xlcrawl2.py (메인 스크립트)
"""
Excel 크롤링 자동화 메인

사용법:
    python scripts/xlcrawl2.py
"""

from crawl_utils.services.site_crawler import SiteCrawler
from xl_utils.adapters.crawl_adapter import XlCrawlAdapter

def main():
    # 1. Excel에서 URL 추출
    adapter = XlCrawlAdapter("configs/excel.yaml")
    urls = adapter.extract_urls_from_excel("Sheet1", "URL")
    
    # 2. 크롤링
    crawler = SiteCrawler("taobao")
    for url in urls:
        crawler.crawl_detail(url)
    
    # 3. Excel 업데이트
    adapter.update_download_status(urls, "완료")

if __name__ == "__main__":
    main()
```

---

### Phase 2: OTO 관련 재구조화

#### 1️⃣ **Service 분리**

**이동: `scripts/xloto.py` 클래스들 → `modules/image_utils/services/`**
```python
# modules/image_utils/services/oto_processor.py
"""
이미지 OTO 처리 Service

역할: 이미지 OCR, 번역, 오버레이
"""

class ImageOTOProcessor:
    def process_oto(self, image_path: Path, config: OTOConfig) -> Path:
        """OTO 전체 파이프라인"""

# modules/image_utils/services/casno_extractor.py
class CASNoExtractor:
    def extract_casno(self, text: str) -> Optional[str]:
        """CAS 번호 추출"""
```

#### 2️⃣ **Adapter 분리**

**이동: `modules/xl_utils/adapters/oto_adapter.py`**
```python
# modules/xl_utils/adapters/oto_adapter.py
"""
Excel ↔ OTO 연동 Adapter

역할: Excel에서 이미지 경로 읽기, 결과 저장
"""

class XlOTOAdapter:
    def get_image_paths(self, sheet: str) -> List[Path]:
        """Excel에서 이미지 경로 추출"""
    
    def save_oto_results(self, results: List[Dict]):
        """OTO 결과를 Excel에 저장"""
```

#### 3️⃣ **메인 스크립트 간소화**

**간소화: `scripts/xloto.py`**
```python
# scripts/xloto.py (메인 스크립트)
"""
Excel OTO 자동화 메인
"""

from image_utils.services.oto_processor import ImageOTOProcessor
from xl_utils.adapters.oto_adapter import XlOTOAdapter

def main():
    # 1. Excel에서 이미지 경로 추출
    adapter = XlOTOAdapter("configs/excel.yaml")
    image_paths = adapter.get_image_paths("Sheet1")
    
    # 2. OTO 처리
    processor = ImageOTOProcessor()
    results = []
    for path in image_paths:
        result = processor.process_oto(path, config)
        results.append(result)
    
    # 3. Excel에 저장
    adapter.save_oto_results(results)

if __name__ == "__main__":
    main()
```

---

### Phase 3: 테스트 파일 정리

#### 이동 계획:
```
scripts/test_*.py → tests/integration/
```

#### 새로운 구조:
```
tests/
├── unit/                      # 단위 테스트
│   ├── test_xl_utils.py
│   ├── test_crawl_utils.py
│   └── test_image_utils.py
│
├── integration/               # 통합 테스트
│   ├── test_xlcrawl_workflow.py      # xlcrawl2.py 테스트
│   ├── test_xloto_workflow.py        # xloto.py 테스트
│   ├── test_js_snippet.py            # JS 추출 테스트
│   └── test_image_downloader.py      # 이미지 다운로드 테스트
│
└── manual/                    # 수동 테스트
    ├── test_js_snippet_browser.py
    └── test_font_color_utils.py
```

---

## 📁 최종 디렉토리 구조

```
m:\CALife\CAShop - 구매대행\_code/

├── 📂 scripts/                        # 🚀 메인 엔트리포인트만
│   ├── xlcrawl2.py                   # Excel 크롤링 메인
│   ├── xloto.py                      # OTO 메인
│   ├── setup_env.py                  # 환경 설정
│   └── [삭제 예정]
│       ├── crawl_session_managed.py  → modules/crawl_utils/services/
│       ├── crawl_two_step.py         → modules/crawl_utils/services/
│       ├── test_*.py                 → tests/integration/
│       └── *_old.py, 0.TEST.py       → 삭제
│
├── 📂 modules/                        # 📦 재사용 가능 모듈
│   │
│   ├── 📂 crawl_utils/
│   │   ├── services/
│   │   │   ├── site_crawler.py       # SiteCrawler (이동)
│   │   │   └── pipeline.py           # CrawlPipeline (기존)
│   │   ├── adapters/
│   │   │   └── [신규 필요시 추가]
│   │   └── utils/
│   │       ├── filter_utils.py       # manual_filter_urls (이동)
│   │       └── anti_detection.py     # 참고용 (기존)
│   │
│   ├── 📂 xl_utils/
│   │   ├── services/
│   │   │   └── controller.py         # XlController (기존)
│   │   ├── adapters/                 # 🆕 신규
│   │   │   ├── crawl_adapter.py      # Excel ↔ Crawl
│   │   │   └── oto_adapter.py        # Excel ↔ OTO
│   │   └── utils/
│   │       └── ...
│   │
│   ├── 📂 image_utils/
│   │   ├── services/
│   │   │   ├── oto_processor.py      # ImageOTOProcessor (이동)
│   │   │   ├── casno_extractor.py    # CASNoExtractor (이동)
│   │   │   └── image_downloader.py   # (기존)
│   │   ├── adapters/
│   │   │   └── ocr_adapter.py        # OCR 연동
│   │   └── utils/
│   │       └── ...
│   │
│   └── 📂 translate_utils/
│       ├── services/
│       │   └── translator.py         # (기존)
│       └── adapters/
│           └── ...
│
├── 📂 tests/                          # 🧪 테스트
│   ├── unit/
│   ├── integration/                  # test_*.py 이동
│   └── manual/
│
└── 📂 configs/                        # ⚙️ 설정
    ├── excel.yaml
    ├── xlcrawl.yaml
    ├── firefox_taobao.yaml
    └── ...
```

---

## 🔧 리팩토링 순서

### Step 1: 크롤링 Service 분리 (우선순위 높음)
1. `crawl_session_managed.py` → `modules/crawl_utils/services/site_crawler.py`
2. `manual_filter_urls()` → `modules/crawl_utils/utils/filter_utils.py`
3. `scripts/xlcrawl2.py` 간소화

### Step 2: Excel Adapter 생성
1. `modules/xl_utils/adapters/crawl_adapter.py` 생성
2. `extract_urls_from_dataframe()`, `update_download_column()` 이동
3. `scripts/xlcrawl2.py`에서 Adapter 사용

### Step 3: OTO Service 분리
1. `ImageOTOProcessor` → `modules/image_utils/services/oto_processor.py`
2. `CASNoExtractor` → `modules/image_utils/services/casno_extractor.py`
3. `modules/xl_utils/adapters/oto_adapter.py` 생성
4. `scripts/xloto.py` 간소화

### Step 4: 테스트 파일 이동
1. `scripts/test_*.py` → `tests/integration/`
2. `tests/` 구조화

### Step 5: 정리
1. `*_old.py`, `0.TEST.py` 삭제
2. `__init__.py` 업데이트
3. Import 경로 수정
4. 문서 업데이트

---

## 📝 마이그레이션 가이드

### Before (현재)
```python
# scripts/xlcrawl2.py (270줄)
def load_paths_config(): ...
def get_config_paths(): ...
def extract_urls_from_dataframe(): ...
def process_crawling(): ...
def update_download_column(): ...
def main(): ...
```

### After (목표)
```python
# scripts/xlcrawl2.py (50줄)
from crawl_utils.services.site_crawler import SiteCrawler
from xl_utils.adapters.crawl_adapter import XlCrawlAdapter

def main():
    adapter = XlCrawlAdapter()
    urls = adapter.extract_urls()
    
    crawler = SiteCrawler("taobao")
    crawler.crawl_detail_batch(urls)
    
    adapter.update_status(urls, "완료")
```

---

## ✅ 리팩토링 효과

### 1️⃣ **명확한 역할 분리**
- **Scripts**: 실행만 (50줄 이내)
- **Services**: 비즈니스 로직 (재사용 가능)
- **Adapters**: 외부 연동 (Excel, WebDriver)
- **Utils**: 헬퍼 함수

### 2️⃣ **재사용성 향상**
- `SiteCrawler`를 여러 스크립트에서 사용 가능
- `XlCrawlAdapter`를 다른 워크플로우에서 재사용

### 3️⃣ **테스트 용이성**
- Service 단위 테스트 가능
- Adapter 모킹 가능
- 통합 테스트 분리

### 4️⃣ **유지보수성**
- 파일 위치로 역할 파악 가능
- Import 경로로 의존성 명확
- 변경 영향 범위 제한

---

## 🚀 실행 계획

**지금 바로 시작하시겠습니까?**

1. ✅ Step 1 실행: 크롤링 Service 분리
2. ⏭️ Step 2 대기: Excel Adapter 생성
3. ⏭️ Step 3 대기: OTO Service 분리
4. ⏭️ Step 4 대기: 테스트 이동
5. ⏭️ Step 5 대기: 정리

어느 단계부터 진행할까요?
