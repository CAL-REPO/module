# xlcrawl2.py 완전 구현을 위한 개선 계획

## 📋 현재 상태 분석

### ✅ 완료된 부분
1. **환경 설정 및 초기화**
   - ✅ `load_paths_config()` - paths.local.yaml 로드
   - ✅ `get_config_paths()` - excel.yaml, xlcrawl.yaml 경로 추출
   - ✅ ConfigLoader + BaseParserPolicy 통합

2. **Excel 처리**
   - ✅ `XlController` - Excel 파일 열기
   - ✅ `to_dataframe()` - DataFrame 추출
   - ✅ `extract_urls_from_dataframe()` - URL 추출
   - ✅ `update_download_column()` - 날짜 기입

3. **WebDriver 설정**
   - ✅ Firefox WebDriver 정책 (xlcrawl.yaml)
   - ✅ `create_webdriver("firefox", config)` - WebDriver 생성

### ⚠️ 미완성 부분 (process_crawling 함수)

```python
# 현재 구현 (process_crawling 함수 내부)
driver.driver.get(url)  # ✅ 페이지 로드만 됨

# TODO: 실제 크롤링 로직
# - JS extract 실행
# - 이미지 다운로드
# - 상품 정보 추출
```

---

## 🎯 개선이 필요한 Utils 및 Adapter

### 1. **crawl_utils 개선 사항**

#### 1.1 DetailEntryPoint 활용 (추천)
**위치**: `modules/crawl_utils/services/entry_points/detail.py`

**현재 상태**:
- ✅ 상세페이지 크롤링 엔트리포인트 존재
- ✅ Navigator, SmartNormalizer, FileSaver 통합
- ⚠️ **async 전용** - xlcrawl2.py는 sync 환경

**개선 방안**:
```python
# Option 1: SyncCrawlRunner 사용
from crawl_utils import SyncCrawlRunner, DetailEntryPoint

runner = SyncCrawlRunner(DetailEntryPoint(navigator, policy))
result = runner.run(url="https://example.com/product/123")

# Option 2: asyncio.run() 래핑
import asyncio
entry_point = DetailEntryPoint(navigator, policy)
result = asyncio.run(entry_point.run(url))
```

**필요한 작업**:
- [ ] `SyncCrawlRunner` + `DetailEntryPoint` 통합 테스트
- [ ] xlcrawl2.py에서 사용 예제 추가

---

#### 1.2 Navigator 동기화 래퍼
**위치**: `modules/crawl_utils/services/navigator.py`

**현재 상태**:
```python
class SeleniumNavigator:
    async def load(self, url: str) -> None: ...
    async def wait(self, hook, selector, timeout, condition) -> None: ...
    async def execute_js(self, script: str) -> Any: ...
```

**문제점**:
- xlcrawl2.py는 sync 환경 (`with XlController` 사용)
- DetailEntryPoint는 async 전용

**개선 방안**:
```python
# 새 파일: modules/crawl_utils/services/sync_navigator.py
class SyncSeleniumNavigator:
    """동기 환경을 위한 Navigator 래퍼"""
    
    def __init__(self, driver):
        self.driver = driver
    
    def load(self, url: str) -> None:
        self.driver.get(url)
    
    def wait(self, hook, selector, timeout, condition) -> None:
        # WebDriverWait 사용
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By
        
        if hook == "css":
            by = By.CSS_SELECTOR
        elif hook == "xpath":
            by = By.XPATH
        else:
            return
        
        wait = WebDriverWait(self.driver, timeout)
        if condition == "visibility":
            wait.until(EC.visibility_of_element_located((by, selector)))
        else:
            wait.until(EC.presence_of_element_located((by, selector)))
    
    def execute_js(self, script: str) -> Any:
        return self.driver.execute_script(script)
```

**필요한 작업**:
- [ ] `SyncSeleniumNavigator` 클래스 생성
- [ ] `SyncDetailEntryPoint` 또는 기존 DetailEntryPoint에서 async 제거
- [ ] xlcrawl2.py에서 사용

---

#### 1.3 JS Extract Snippet 관리
**위치**: `configs/xlcrawl.yaml` + 새 파일 필요

**현재 상태**:
```yaml
# xlcrawl.yaml
extract:
  patterns:  # XPath 패턴 (DOM 추출용)
    title: "//h1[@class='product-title']"
    images: "//img[@class='product-image']/@src"
```

**문제점**:
- DetailEntryPoint는 `ExtractorType.JS` + `js_snippet` 필요
- 현재 patterns는 XPath (DOM 추출용)

**개선 방안**:
```yaml
# xlcrawl.yaml 개선
extract:
  type: "js"  # "dom", "js", "api"
  
  # JS snippet 직접 정의
  js_snippet: |
    return {
      title: document.querySelector('h1.product-title')?.innerText,
      price: document.querySelector('span.price')?.innerText,
      images: Array.from(document.querySelectorAll('img.product-image')).map(img => img.src),
      description: document.querySelector('div.description')?.innerHTML
    };
  
  # 또는 JS 파일 경로
  js_file: "scripts/extract_taobao.js"
```

**필요한 작업**:
- [ ] xlcrawl.yaml에 `extract.type`, `extract.js_snippet` 추가
- [ ] 또는 별도 JS 파일 관리 시스템 (scripts/extractors/*.js)
- [ ] DetailEntryPoint에서 js_snippet 로드

---

### 2. **image_utils 개선 사항**

#### 2.1 이미지 다운로드 함수
**위치**: `modules/image_utils/` (새 모듈 필요)

**현재 상태**:
- ✅ `ImageLoader` - 로컬 이미지 로드/복사/리사이즈
- ✅ `ImageOCR` - OCR 처리
- ✅ `ImageOverlay` - 텍스트 오버레이
- ❌ **URL에서 이미지 다운로드 기능 없음**

**필요한 기능**:
```python
# 새 파일: modules/image_utils/services/image_downloader.py
class ImageDownloader:
    """URL에서 이미지 다운로드"""
    
    def __init__(self, policy: ImageDownloadPolicy):
        self.policy = policy
    
    def download(self, url: str, save_path: Path) -> Path:
        """단일 이미지 다운로드"""
        response = requests.get(url, timeout=self.policy.timeout)
        response.raise_for_status()
        
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(response.content)
        
        return save_path
    
    def download_many(self, urls: List[str], save_dir: Path) -> List[Path]:
        """여러 이미지 다운로드"""
        results = []
        for i, url in enumerate(urls):
            filename = f"image_{i:04d}{self._get_extension(url)}"
            save_path = save_dir / filename
            try:
                self.download(url, save_path)
                results.append(save_path)
            except Exception as e:
                print(f"Download failed: {url} - {e}")
        return results
```

**필요한 작업**:
- [ ] `ImageDownloadPolicy` 정책 생성
- [ ] `ImageDownloader` 클래스 구현
- [ ] `image_utils/__init__.py`에 export 추가
- [ ] xlcrawl.yaml에 download 정책 추가

---

#### 2.2 crawl_utils.FileSaver와 통합
**위치**: `modules/crawl_utils/services/saver.py`

**현재 상태**:
```python
class FileSaver:
    async def save_many(self, items: List[NormalizedItem], fetcher: ResourceFetcher) -> SaveSummary:
        """이미지 다운로드 + 저장"""
        # fetcher.fetch(url) 사용
```

**개선 방안**:
```python
# xlcrawl2.py에서 FileSaver 직접 사용
from crawl_utils.services.saver import FileSaver
from crawl_utils.services.fetcher import HTTPFetcher

fetcher = HTTPFetcher()
saver = FileSaver(storage_policy)

# NormalizedItem으로 변환 필요
items = [
    NormalizedItem(
        kind="image",
        url=img_url,
        section="product_123",
        name="image_001",
        extension="jpg"
    )
    for img_url in image_urls
]

# 비동기 다운로드
import asyncio
summary = asyncio.run(saver.save_many(items, fetcher))
```

**필요한 작업**:
- [ ] xlcrawl2.py에서 NormalizedItem 생성 로직 추가
- [ ] FileSaver 사용 예제 추가
- [ ] 또는 동기 버전 `SyncFileSaver` 생성

---

### 3. **xl_utils 개선 사항 (선택)**

#### 3.1 DataFrame에서 컬럼 인덱스 안전하게 가져오기
**위치**: `scripts/xlcrawl2.py` (update_download_column 함수)

**현재 문제**:
```python
col_idx = df.columns.get_loc(download_col) + 1  # 오류 가능성
# get_loc()은 int | slice | ndarray 반환 가능
```

**개선 방안**:
```python
def get_excel_column_index(df: pd.DataFrame, col_name: str) -> int:
    """DataFrame 컬럼 → Excel 컬럼 인덱스 (1-based)"""
    loc = df.columns.get_loc(col_name)
    
    if isinstance(loc, int):
        return loc + 1
    elif isinstance(loc, slice):
        return loc.start + 1
    else:
        # ndarray인 경우 첫 번째 True 인덱스
        return int(loc.argmax()) + 1
```

**필요한 작업**:
- [ ] `xl_utils/helpers/` 에 유틸 함수 추가
- [ ] xlcrawl2.py에서 사용

---

## 📝 xlcrawl2.py 완전 구현 시나리오

### Scenario A: DetailEntryPoint + SyncCrawlRunner (추천)

```python
# scripts/xlcrawl2.py
from crawl_utils import create_webdriver, SyncCrawlRunner, CrawlPolicy
from crawl_utils.services.entry_points import DetailEntryPoint
from crawl_utils.services.sync_navigator import SyncSeleniumNavigator

def process_crawling(urls, crawl_config, output_dir):
    # 1. WebDriver 생성
    driver = create_webdriver("firefox", crawl_config["firefox"])
    
    # 2. Navigator 생성
    navigator = SyncSeleniumNavigator(driver.driver)
    
    # 3. CrawlPolicy 생성
    policy = CrawlPolicy.from_dict(crawl_config["crawl_policy"])
    
    # 4. DetailEntryPoint 생성
    entry_point = DetailEntryPoint(navigator, policy)
    
    # 5. SyncCrawlRunner로 실행
    runner = SyncCrawlRunner(entry_point)
    
    results = {}
    for idx, url in urls:
        try:
            summary = runner.run(url, product_id=f"product_{idx}")
            results[idx] = {
                "status": "success",
                "images": len(summary.artifacts.get("image", [])),
                "texts": len(summary.artifacts.get("text", []))
            }
        except Exception as e:
            results[idx] = {"status": "failed", "error": str(e)}
    
    driver.quit()
    return results
```

**장점**:
- ✅ 기존 crawl_utils 인프라 최대 활용
- ✅ SmartNormalizer 자동 타입 추론
- ✅ FileSaver 자동 저장

**필요한 작업**:
- [ ] `SyncSeleniumNavigator` 구현
- [ ] `SyncCrawlRunner` + `DetailEntryPoint` 통합 확인
- [ ] xlcrawl.yaml에 CrawlPolicy 섹션 추가

---

### Scenario B: 직접 WebDriver + Manual Extract (간단)

```python
# scripts/xlcrawl2.py
from crawl_utils import create_webdriver
from image_utils import ImageDownloader

def process_crawling(urls, crawl_config, output_dir):
    # 1. WebDriver 생성
    driver = create_webdriver("firefox", crawl_config["firefox"])
    
    # 2. ImageDownloader 생성
    downloader = ImageDownloader(crawl_config["image_download"])
    
    results = {}
    for idx, url in urls:
        try:
            # 페이지 로드
            driver.driver.get(url)
            
            # JS extract 실행
            js_snippet = crawl_config["extract"]["js_snippet"]
            data = driver.driver.execute_script(js_snippet)
            
            # 이미지 다운로드
            if "images" in data:
                save_dir = output_dir / f"product_{idx}"
                image_paths = downloader.download_many(data["images"], save_dir)
                
                results[idx] = {
                    "status": "success",
                    "title": data.get("title"),
                    "images": len(image_paths)
                }
        except Exception as e:
            results[idx] = {"status": "failed", "error": str(e)}
    
    driver.quit()
    return results
```

**장점**:
- ✅ 구현 간단
- ✅ 동기 환경에서 바로 사용 가능

**단점**:
- ❌ SmartNormalizer, FileSaver 등 기존 인프라 미활용
- ❌ 수동 구현 필요

**필요한 작업**:
- [ ] `ImageDownloader` 구현
- [ ] xlcrawl.yaml에 `extract.js_snippet` 추가

---

## 🎯 최종 우선순위

### Phase 1: 기본 동작 (Scenario B 기반)
1. [ ] `ImageDownloader` 구현
   - `modules/image_utils/services/image_downloader.py`
   - `ImageDownloadPolicy` 정책
2. [ ] xlcrawl.yaml에 `js_snippet` 추가
3. [ ] xlcrawl2.py에서 직접 WebDriver + JS extract
4. [ ] 테스트 및 디버깅

**예상 시간**: 2-3시간

---

### Phase 2: crawl_utils 통합 (Scenario A 기반)
1. [ ] `SyncSeleniumNavigator` 구현
   - `modules/crawl_utils/services/sync_navigator.py`
2. [ ] `SyncDetailEntryPoint` 또는 기존 DetailEntryPoint 동기화
3. [ ] xlcrawl.yaml에 CrawlPolicy 섹션 추가
4. [ ] xlcrawl2.py에서 DetailEntryPoint + SyncCrawlRunner 사용
5. [ ] 테스트 및 디버깅

**예상 시간**: 4-6시간

---

### Phase 3: 고도화
1. [ ] JS extract snippet 외부 파일 관리 (`scripts/extractors/*.js`)
2. [ ] 재시도 로직 강화
3. [ ] 에러 핸들링 개선
4. [ ] 로깅 강화 (logs_utils 통합)
5. [ ] 성능 최적화 (병렬 다운로드)

**예상 시간**: 4-8시간

---

## 📌 즉시 실행 가능한 작업 (Quick Wins)

### 1. xlcrawl.yaml에 js_snippet 추가
```yaml
extract:
  type: "js"
  js_snippet: |
    return {
      title: document.querySelector('h1.product-title')?.innerText || '',
      price: document.querySelector('span.price')?.innerText || '',
      images: Array.from(document.querySelectorAll('img.product-image')).map(img => img.src),
      description: document.querySelector('div.description')?.innerHTML || ''
    };
```

### 2. ImageDownloader 기본 구현
```python
# modules/image_utils/services/image_downloader.py
import requests
from pathlib import Path
from typing import List
from pydantic import BaseModel, Field

class ImageDownloadPolicy(BaseModel):
    timeout: int = Field(30, description="Download timeout (seconds)")
    max_retries: int = Field(3, description="Max retry count")
    user_agent: str = Field("Mozilla/5.0", description="User-Agent header")

class ImageDownloader:
    def __init__(self, policy: ImageDownloadPolicy | dict):
        if isinstance(policy, dict):
            policy = ImageDownloadPolicy(**policy)
        self.policy = policy
    
    def download(self, url: str, save_path: Path) -> Path:
        """단일 이미지 다운로드"""
        headers = {"User-Agent": self.policy.user_agent}
        response = requests.get(url, headers=headers, timeout=self.policy.timeout)
        response.raise_for_status()
        
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(response.content)
        
        return save_path
    
    def download_many(self, urls: List[str], save_dir: Path, prefix: str = "image") -> List[Path]:
        """여러 이미지 다운로드"""
        results = []
        for i, url in enumerate(urls):
            ext = Path(url).suffix or ".jpg"
            filename = f"{prefix}_{i:04d}{ext}"
            save_path = save_dir / filename
            
            try:
                self.download(url, save_path)
                results.append(save_path)
                print(f"  ✅ Downloaded: {filename}")
            except Exception as e:
                print(f"  ❌ Failed: {url} - {e}")
        
        return results
```

### 3. xlcrawl2.py 기본 크롤링 로직
```python
# process_crawling 함수 내부 수정
def process_crawling(urls, crawl_config, output_dir):
    from image_utils.services.image_downloader import ImageDownloader, ImageDownloadPolicy
    
    # WebDriver 생성
    driver = create_webdriver("firefox", crawl_config["firefox"])
    
    # ImageDownloader 생성
    download_policy = ImageDownloadPolicy(
        timeout=crawl_config.get("crawl", {}).get("timeout", 30)
    )
    downloader = ImageDownloader(download_policy)
    
    # JS snippet 로드
    js_snippet = crawl_config.get("extract", {}).get("js_snippet", "return {};")
    
    results = {}
    for idx, url in urls:
        print(f"\n🌐 크롤링 중 [{idx}]: {url}")
        
        try:
            # 페이지 로드
            driver.driver.get(url)
            
            # JS extract 실행
            data = driver.driver.execute_script(js_snippet)
            
            # 이미지 다운로드
            images = data.get("images", [])
            if images:
                save_dir = output_dir / f"product_{idx}"
                image_paths = downloader.download_many(images, save_dir)
                
                results[idx] = {
                    "status": "success",
                    "title": data.get("title", ""),
                    "price": data.get("price", ""),
                    "images_count": len(image_paths),
                    "timestamp": datetime.now().isoformat()
                }
                print(f"  ✅ 성공: {data.get('title')} - {len(image_paths)}개 이미지")
            else:
                results[idx] = {
                    "status": "success",
                    "title": data.get("title", ""),
                    "images_count": 0
                }
        
        except Exception as e:
            print(f"  ❌ 실패: {e}")
            results[idx] = {"status": "failed", "error": str(e)}
    
    driver.quit()
    return results
```

---

## 🚀 다음 단계

### 즉시 실행:
1. **ImageDownloader 구현** → `modules/image_utils/services/image_downloader.py`
2. **xlcrawl.yaml 업데이트** → `extract.js_snippet` 추가
3. **xlcrawl2.py 수정** → process_crawling 함수 완성
4. **테스트 실행** → 실제 URL로 크롤링 테스트

### 장기 계획:
- DetailEntryPoint + SyncCrawlRunner 통합
- JS snippet 외부 파일 관리
- 병렬 다운로드 최적화
