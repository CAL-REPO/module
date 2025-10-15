# JS Snippet 결과물 분석

## 📋 crawl_refactor.yaml의 JS Snippet

### 코드
```javascript
const items = [];
document.querySelectorAll('.result-item img').forEach((img) => {
  let url = img.getAttribute('data-src') || img.getAttribute('src') || '';
  if (url.startsWith('//')) url = 'https:' + url;
  if (/^https?:\/\//i.test(url)) {
    items.push({ url, caption: img.getAttribute('alt') || '' });
  }
});
return items;
```

### 반환 타입
```typescript
Array<{
  url: string;      // 이미지 URL (https:// 또는 http://)
  caption: string;  // alt 속성 (없으면 빈 문자열)
}>
```

### 예시 결과
```json
[
  {
    "url": "https://example.com/image1.jpg",
    "caption": "Product 1"
  },
  {
    "url": "https://example.com/image2.jpg",
    "caption": "Product 2"
  },
  {
    "url": "https://example.com/image3.jpg",
    "caption": ""
  }
]
```

### 특징
- ✅ **배열 반환**: 여러 이미지를 한 번에 추출
- ✅ **프로토콜 정규화**: `//example.com` → `https://example.com`
- ✅ **URL 검증**: `https?://` 패턴만 허용
- ✅ **안전한 기본값**: caption이 없으면 빈 문자열

### 용도
- 검색 결과 페이지 (여러 상품)
- 갤러리 페이지 (여러 이미지)
- 리스트 페이지 (여러 항목)

---

## 📋 xlcrawl.yaml의 JS Snippet

### 코드
```javascript
return {
  title: document.querySelector('h1.product-title, h1[class*="title"], .item-title')?.innerText?.trim() || '',
  price: document.querySelector('.price, .product-price, [class*="price"]')?.innerText?.trim() || '',
  images: Array.from(document.querySelectorAll('img[class*="product"], img[class*="item"], .gallery img')).map(img => img.src || img.dataset.src).filter(Boolean),
  description: document.querySelector('.description, .product-description, [class*="desc"]')?.innerHTML || '',
  brand: document.querySelector('.brand, .product-brand')?.innerText?.trim() || '',
  category: document.querySelector('.category, .breadcrumb')?.innerText?.trim() || ''
};
```

### 반환 타입
```typescript
{
  title: string;        // 상품 제목
  price: string;        // 가격
  images: string[];     // 이미지 URL 배열
  description: string;  // 설명 (HTML)
  brand: string;        // 브랜드
  category: string;     // 카테고리
}
```

### 예시 결과
```json
{
  "title": "나이키 에어맥스 2024",
  "price": "¥399",
  "images": [
    "https://example.com/product/main.jpg",
    "https://example.com/product/detail1.jpg",
    "https://example.com/product/detail2.jpg"
  ],
  "description": "<p>상품 설명...</p>",
  "brand": "Nike",
  "category": "신발 > 운동화"
}
```

### 특징
- ✅ **객체 반환**: 단일 상품의 모든 정보
- ✅ **범용 셀렉터**: 다양한 사이트에 대응 (`class*="title"` 등)
- ✅ **null-safe**: `?.` 연산자로 안전한 접근
- ✅ **자동 trim**: 공백 제거
- ✅ **배열 필터링**: `filter(Boolean)`로 빈 값 제거

### 용도
- 상품 상세 페이지 (단일 상품)
- 블로그 포스트 (단일 게시물)
- 뉴스 기사 (단일 기사)

---

## 🔄 두 방식 비교

| 특성 | crawl_refactor.yaml | xlcrawl.yaml |
|------|---------------------|--------------|
| **반환 타입** | `Array<Object>` | `Object` |
| **용도** | 검색/리스트 페이지 | 상세 페이지 |
| **데이터 처리** | SmartNormalizer 자동 | 수동 처리 |
| **이미지 처리** | normalization.rules | ImageDownloader |
| **확장성** | 규칙 기반 자동화 | 스크립트 커스터마이징 |
| **복잡도** | 높음 (CrawlPipeline) | 낮음 (직접 처리) |

---

## 📊 normalization.rules 매핑

### crawl_refactor.yaml의 규칙

#### 규칙 1: 이미지
```yaml
- kind: "image"
  source: "payload.url"              # items[i].url
  static_section: "results"
  name_template: "{section}_{record_index}_{item_index}"
  extension: "jpg"
```

**처리 결과**:
```
items[0].url → results_0_0.jpg
items[1].url → results_0_1.jpg
items[2].url → results_0_2.jpg
```

#### 규칙 2: 텍스트 (캡션)
```yaml
- kind: "text"
  source: "payload.caption"          # items[i].caption
  static_section: "results"
  name_template: "{section}_{record_index}_{item_index}_caption"
  allow_empty: false                 # 빈 캡션 제외
```

**처리 결과**:
```
items[0].caption → results_0_0_caption.txt
items[1].caption → results_0_1_caption.txt
items[2].caption → (제외됨 - 빈 문자열)
```

---

## 🎯 사용 시나리오

### Scenario 1: 타오바오 검색 결과 크롤링 (crawl_refactor.yaml)

```yaml
extractor:
  type: "js"
  js_snippet: |
    const items = [];
    document.querySelectorAll('.item .pic img').forEach((img) => {
      let url = img.getAttribute('data-src') || img.src || '';
      if (url.startsWith('//')) url = 'https:' + url;
      if (/^https?:\/\//i.test(url)) {
        items.push({
          url,
          caption: img.alt || '',
          price: img.closest('.item')?.querySelector('.price')?.innerText || ''
        });
      }
    });
    return items;

normalization:
  rules:
    - kind: "image"
      source: "payload.url"
      static_section: "taobao_search"
    - kind: "text"
      source: "payload.price"
      static_section: "taobao_search"
      name_template: "{section}_{item_index}_price"
```

**장점**:
- ✅ 자동 정규화 및 파일 저장
- ✅ 규칙 기반으로 확장 가능
- ✅ SmartNormalizer가 타입 자동 추론

---

### Scenario 2: 타오바오 상품 상세 크롤링 (xlcrawl.yaml)

```yaml
extract:
  type: "js"
  js_snippet: |
    return {
      title: document.querySelector('.tb-detail-hd h1')?.innerText?.trim() || '',
      price: document.querySelector('.tb-rmb-num')?.innerText?.trim() || '',
      images: Array.from(document.querySelectorAll('#J_ImgBooth img')).map(img => img.src).filter(Boolean),
      description: document.querySelector('#J_DivItemDesc')?.innerHTML || ''
    };
```

**장점**:
- ✅ 간단한 구조 (dict 직접 처리)
- ✅ xlcrawl2.py에서 즉시 사용 가능
- ✅ ImageDownloader로 수동 제어

---

## 🚀 실전 예제

### crawl_refactor.yaml 스타일 (복잡한 자동화)

```python
from crawl_utils import CrawlPipeline, SyncCrawlRunner, CrawlPolicy

# YAML 설정 로드
policy = CrawlPolicy.from_yaml("configs/crawl_refactor.yaml")

# Pipeline 생성
pipeline = CrawlPipeline(
    navigator=navigator,
    policy=policy
)

# 자동 실행 (JS extract → normalize → save)
runner = SyncCrawlRunner(pipeline)
summary = runner.run()

# 결과
print(f"이미지: {len(summary.artifacts['image'])}개")
print(f"텍스트: {len(summary.artifacts['text'])}개")
```

### xlcrawl.yaml 스타일 (간단한 수동 처리)

```python
from crawl_utils import create_webdriver
from image_utils import ImageDownloader

# WebDriver 생성
driver = create_webdriver("firefox", config)
driver.driver.get(url)

# JS extract 실행
data = driver.driver.execute_script(js_snippet)
# → {title, price, images, description}

# 이미지 다운로드
downloader = ImageDownloader(policy)
results = downloader.download_many(
    data["images"],
    save_dir,
    prefix="product"
)

# 결과 처리
print(f"Title: {data['title']}")
print(f"Price: {data['price']}")
print(f"Images: {len(results)}개 다운로드")
```

---

## ✅ 결론

### crawl_refactor.yaml의 JS snippet
- **반환**: `Array<{url, caption}>`
- **처리**: SmartNormalizer + normalization.rules
- **용도**: 자동화된 대량 크롤링
- **복잡도**: 높음
- **유연성**: 규칙 기반 확장

### xlcrawl.yaml의 JS snippet
- **반환**: `{title, price, images[], description, ...}`
- **처리**: 직접 dict 처리
- **용도**: Excel 기반 간단한 크롤링
- **복잡도**: 낮음
- **유연성**: 코드 직접 수정

### 선택 기준
1. **대량 자동화** → crawl_refactor.yaml
2. **Excel 연동** → xlcrawl.yaml
3. **간단한 크롤링** → xlcrawl.yaml
4. **복잡한 정규화** → crawl_refactor.yaml

둘 다 강력하며, 프로젝트 요구사항에 따라 선택하면 됩니다! 🎯
