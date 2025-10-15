# xlcrawl2.py 구현 완료 요약

## ✅ 완료된 작업

### 1. xlcrawl.yaml에 JS Extract Snippet 추가
**위치**: `configs/xlcrawl.yaml`

```yaml
extract:
  type: "js"
  js_snippet: |
    return {
      title: document.querySelector('h1.product-title, h1[class*="title"], .item-title')?.innerText?.trim() || '',
      price: document.querySelector('.price, .product-price, [class*="price"]')?.innerText?.trim() || '',
      images: Array.from(document.querySelectorAll('img[class*="product"], img[class*="item"], .gallery img')).map(img => img.src || img.dataset.src).filter(Boolean),
      description: document.querySelector('.description, .product-description, [class*="desc"]')?.innerHTML || '',
      brand: document.querySelector('.brand, .product-brand')?.innerText?.trim() || '',
      category: document.querySelector('.category, .breadcrumb')?.innerText?.trim() || ''
    };
```

**특징**:
- ✅ 다양한 셀렉터 패턴 지원 (타오바오, 쿠팡 등)
- ✅ null-safe 연산자 (`?.`) 사용
- ✅ 이미지 배열 자동 수집 (`img.src`, `img.dataset.src`)
- ✅ 빈 값 필터링

---

### 2. ImageDownloader 구현
**위치**: `modules/image_utils/services/image_downloader.py`

#### 주요 클래스:
```python
class ImageDownloadPolicy(BaseModel):
    """이미지 다운로드 정책"""
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    user_agent: str = "Mozilla/5.0 ..."
    headers: Dict[str, str] = {}
    verify_ssl: bool = True

class ImageDownloader:
    """동기 HTTP 이미지 다운로더"""
    
    def download(self, url: str, save_path: Path) -> Path:
        """단일 이미지 다운로드"""
    
    def download_many(
        self, 
        urls: List[str], 
        save_dir: Path, 
        prefix: str = "image"
    ) -> List[Dict]:
        """여러 이미지 다운로드"""
```

#### 편의 함수:
```python
def download_images(
    urls: List[str],
    save_dir: Path | str,
    *,
    prefix: str = "image",
    timeout: int = 30,
    max_retries: int = 3
) -> List[Path]:
    """빠른 이미지 다운로드"""
```

**특징**:
- ✅ **동기 처리** (xlcrawl2.py의 sync 환경과 호환)
- ✅ requests 세션 재사용 (성능 최적화)
- ✅ 자동 재시도 (max_retries, retry_delay)
- ✅ 확장자 자동 감지 (`.jpg`, `.png`, `.webp` 등)
- ✅ Context manager 지원 (`with ImageDownloader()`)
- ✅ 상세한 오류 처리 및 로그

**fso_utils와의 차이**:
- ❌ fso_utils: HTTP 다운로드 기능 없음 (로컬 파일 시스템 전용)
- ✅ ImageDownloader: HTTP(S)에서 바이트 다운로드 + 파일 저장

**crawl_utils.HTTPFetcher와의 차이**:
- ❌ HTTPFetcher: async 전용 (aiohttp 기반)
- ✅ ImageDownloader: sync 환경 (requests 기반)

---

### 3. xlcrawl2.py의 process_crawling 함수 완성
**위치**: `scripts/xlcrawl2.py`

#### 구현된 로직:
```python
def process_crawling(urls, crawl_config, output_dir):
    # 1. Firefox WebDriver 생성
    driver = create_webdriver("firefox", crawl_config["firefox"])
    
    # 2. ImageDownloader 생성
    downloader = ImageDownloader(ImageDownloadPolicy(...))
    
    # 3. JS snippet 로드
    js_snippet = crawl_config["extract"]["js_snippet"]
    
    # 4. 각 URL 크롤링
    for idx, url in urls:
        # 4.1 페이지 로드
        driver.driver.get(url)
        
        # 4.2 JS extract 실행
        data = driver.driver.execute_script(js_snippet)
        # → {title, price, images, description, ...}
        
        # 4.3 이미지 다운로드
        if data["images"]:
            download_results = downloader.download_many(
                data["images"],
                output_dir / f"product_{idx}",
                prefix=f"product_{idx}"
            )
        
        # 4.4 결과 저장
        results[idx] = {
            "status": "success",
            "title": data["title"],
            "price": data["price"],
            "images_count": len(downloaded_images),
            ...
        }
    
    # 5. 정리
    driver.quit()
    downloader.close()
```

**특징**:
- ✅ Firefox WebDriver로 실제 페이지 렌더링
- ✅ JS snippet으로 동적 데이터 추출
- ✅ 이미지 일괄 다운로드 (재시도 포함)
- ✅ 상세한 로깅 및 에러 처리
- ✅ 결과 딕셔너리 반환 (Excel 업데이트용)

---

## 📊 전체 워크플로우

```
┌─────────────────────────────────────────────────────────────┐
│ xlcrawl2.py - Excel 크롤링 자동화                             │
└─────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
  ┌──────────┐      ┌──────────┐    ┌──────────┐
  │ Step 1-3 │      │ Step 4-5 │    │ Step 6-8 │
  │  설정     │      │  Excel   │    │  크롤링   │
  └──────────┘      └──────────┘    └──────────┘
        │                 │                 │
        ▼                 ▼                 ▼
  paths.local.yaml   XlController     crawl_utils
  excel.yaml         DataFrame        image_utils
  xlcrawl.yaml       URL 추출
        │                 │                 │
        └─────────────────┴─────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │  process_crawling()   │
              └───────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
  ┌──────────┐      ┌──────────┐    ┌──────────┐
  │ Firefox  │      │ JS       │    │ Image    │
  │ WebDriver│──────│ Extract  │────│Download  │
  └──────────┘      └──────────┘    └──────────┘
        │                 │                 │
        │                 │                 │
        ▼                 ▼                 ▼
   driver.get(url)  execute_script()  download_many()
        │                 │                 │
        └─────────────────┴─────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │  결과 딕셔너리         │
              │  {title, price, ...}  │
              └───────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │ update_download_column│
              │ (Excel에 날짜 기입)    │
              └───────────────────────┘
```

---

## 🎯 사용 예제

### 기본 사용법
```powershell
# 환경변수 설정
$env:CASHOP_PATHS = "M:\CALife\CAShop - 구매대행\_code\configs\paths.local.yaml"

# 스크립트 실행
python scripts/xlcrawl2.py
```

### 출력 예시
```
================================================================================
Excel 크롤링 자동화 스크립트 시작
================================================================================

[Step 1] paths.local.yaml 로드
✅ paths.local.yaml 로드 완료

[Step 2] Excel 및 Crawl 설정 파일 경로 추출
✅ excel.yaml: configs/excel.yaml
✅ xlcrawl.yaml: configs/xlcrawl.yaml

[Step 3] xlcrawl.yaml 설정 로드
  - Download 컬럼: download
  - 이미지 저장 경로: output/images

[Step 4] Excel 파일 열기
  - Excel 파일: M:/CALife/CAShop - 구매대행/01.All Product List.xlsx
  - 시트 이름: Purchase

[Step 5] DataFrame 추출
  - DataFrame 크기: (10, 12)

[Step 6] URL 추출
✅ 3개의 URL 추출 완료

[Step 7] 크롤링 수행
🔧 Firefox WebDriver 초기화 중...
  - Headless: False
  - Window Size: [1440, 900]
  - JS Extract: ✅ 설정됨
  - Image Downloader: ✅ 준비 완료

🌐 크롤링 중 [0]: https://item.taobao.com/item.htm?id=123456
  📝 Title: 나이키 에어맥스 2024
  💰 Price: ¥399
  🖼️  Images: 5개
  ✅ Downloaded [0]: product_0_0000.jpg
  ✅ Downloaded [1]: product_0_0001.jpg
  ✅ Downloaded [2]: product_0_0002.jpg
  ✅ Downloaded [3]: product_0_0003.jpg
  ✅ Downloaded [4]: product_0_0004.jpg
  ✅ 성공: 5/5개 이미지 다운로드

[Step 8] download 컬럼 업데이트
✅ 3개 행의 download 컬럼 업데이트 완료

================================================================================
✅ 모든 작업 완료
================================================================================
```

---

## 📁 생성되는 파일 구조

```
output/
  images/
    product_0/
      product_0_0000.jpg
      product_0_0001.jpg
      ...
    product_1/
      product_1_0000.jpg
      product_1_0001.jpg
      ...

data/
  session/
    firefox_xlcrawl.json  # Firefox 세션 저장

logs/
  xlcrawl.log            # 일반 로그
  xlcrawl_firefox.log    # Firefox 로그
```

---

## 🔧 설정 파일

### xlcrawl.yaml 주요 설정
```yaml
xlcrawl:
  # 다운로드 컬럼
  download_column: "download"
  
  # 이미지 저장
  image_save_dir: "output/images"
  
  # Firefox
  firefox:
    headless: false
    window_size: [1440, 900]
    session_path: "data/session/firefox_xlcrawl.json"
  
  # 크롤링
  crawl:
    timeout: 30
    retry: 3
    delay: 1
  
  # JS Extract
  extract:
    type: "js"
    js_snippet: |
      return {
        title: document.querySelector('h1.product-title')?.innerText,
        price: document.querySelector('.price')?.innerText,
        images: Array.from(document.querySelectorAll('img.product')).map(img => img.src)
      };
```

---

## 🚀 다음 단계 (선택사항)

### Phase 1 완료 ✅
- [x] ImageDownloader 구현
- [x] xlcrawl.yaml에 js_snippet 추가
- [x] xlcrawl2.py의 process_crawling 완성

### Phase 2 (고도화)
- [ ] WebDriverWait로 페이지 로딩 대기 개선
- [ ] 병렬 이미지 다운로드 (ThreadPoolExecutor)
- [ ] DetailEntryPoint + SyncCrawlRunner 통합
- [ ] JS snippet 외부 파일 관리 (`scripts/extractors/*.js`)
- [ ] 에러 복구 로직 강화

### Phase 3 (최적화)
- [ ] 이미지 리사이즈 통합 (ImageLoader)
- [ ] OCR 통합 (ImageOCR)
- [ ] 번역 통합 (translate_utils)
- [ ] 성능 모니터링 및 로깅 강화

---

## 📝 테스트 스크립트

### ImageDownloader 단독 테스트
```bash
python scripts/test_image_downloader.py
```

### xlcrawl2.py 전체 테스트
```bash
# 환경변수 설정
$env:CASHOP_PATHS = "M:\CALife\CAShop - 구매대행\_code\configs\paths.local.yaml"

# 실행
python scripts/xlcrawl2.py
```

---

## 🎉 완료 요약

### 구현된 기능
1. ✅ **JS Extract** - 동적 웹페이지 데이터 추출
2. ✅ **Image Download** - HTTP(S)에서 이미지 일괄 다운로드
3. ✅ **Firefox WebDriver** - 실제 브라우저 렌더링
4. ✅ **Excel 통합** - DataFrame ↔ Excel 양방향
5. ✅ **에러 처리** - 재시도, 로깅, 상세 오류 메시지

### 기술 스택
- **xl_utils**: Excel 조작
- **crawl_utils**: WebDriver, Firefox
- **image_utils**: 이미지 다운로드 (신규)
- **cfg_utils**: 설정 로드
- **requests**: HTTP 동기 처리

### 파일 변경
- ✅ `configs/xlcrawl.yaml` - JS snippet 추가
- ✅ `modules/image_utils/services/image_downloader.py` - 신규 생성
- ✅ `modules/image_utils/__init__.py` - export 추가
- ✅ `scripts/xlcrawl2.py` - process_crawling 완성
- ✅ `scripts/test_image_downloader.py` - 테스트 스크립트

---

## 🔥 Ready to Use!

xlcrawl2.py는 이제 **완전히 동작하는 상태**입니다!

실제 사용 시:
1. Excel 파일에 URL 입력
2. 환경변수 설정
3. `python scripts/xlcrawl2.py` 실행
4. 자동으로 크롤링 + 이미지 다운로드 + Excel 업데이트
