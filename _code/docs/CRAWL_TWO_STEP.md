# 사이트별 2-Step 크롤링 전략

## 📁 파일 구조

```
configs/
├── crawl_taobao_search.yaml       # Step 1: 검색 → 상품 정보
├── crawl_taobao_detail.yaml       # Step 2: 상세 → 이미지/텍스트
├── crawl_aliexpress_search.yaml   # Step 1: 검색 → 상품 정보
├── crawl_aliexpress_detail.yaml   # Step 2: 상세 → 이미지/텍스트
└── crawl_1688_search.yaml         # ...
```

---

## 🎯 2-Step 전략

### Step 1: Search (정보 추출)

**목적**: 검색 결과 페이지에서 **상품 메타데이터** 수집

**추출 항목**:
- ✅ 상품 상세 URL (핵심!)
- ✅ 썸네일 이미지
- ✅ 상품명
- ✅ 가격
- ✅ 판매량/평점
- ✅ 상점명

**JS Snippet 특징**:
```javascript
// 반환 타입: Array<Object>
items.push({
  product_url: "...",   // Step 2에서 사용
  thumbnail: "...",
  title: "...",
  price: "..."
});
```

**출력**:
```
_output/{site}/search/
  images/
    {site}_search_0_0_thumb.jpg
    {site}_search_0_1_thumb.jpg
  text/
    {site}_search_0_0_url.txt        ← Step 2에서 사용!
    {site}_search_0_0_title.txt
    {site}_search_0_0_price.txt
```

---

### Step 2: Detail (이미지/텍스트 전체 추출)

**목적**: 상세 페이지에서 **모든 비주얼/텍스트 콘텐츠** 수집

**추출 항목**:
- ✅ 메인 갤러리 이미지 (여러 장)
- ✅ 상세 설명 이미지 (여러 장)
- ✅ 리뷰 이미지
- ✅ 상품 제목/설명
- ✅ 가격 정보
- ✅ 속성 정보 (색상, 사이즈 등)
- ✅ 배송 정보

**JS Snippet 특징**:
```javascript
// 반환 타입: Object with arrays
return {
  images: [
    {url: "...", type: "main_gallery", alt: "..."},
    {url: "...", type: "description", alt: "..."}
  ],
  descriptions: [
    {content: "...", type: "title"},
    {content: "...", type: "description"}
  ]
};
```

**출력**:
```
_output/{site}/detail/
  images/
    {site}_detail_0_0.jpg           # 메인 이미지 1
    {site}_detail_0_1.jpg           # 메인 이미지 2
    {site}_detail_0_2.jpg           # 설명 이미지 1
  text/
    {site}_detail_0_0_type.txt      # "main_gallery"
    {site}_detail_0_1_type.txt      # "main_gallery"
    {site}_detail_0_2_type.txt      # "description"
    {site}_detail_0_0_text.txt      # 제목
    {site}_detail_0_1_text.txt      # 설명
```

---

## 🔄 독립 실행 흐름

### Workflow 1: 전체 자동화

```python
crawler = TwoStepCrawler("taobao")
crawler.run_full_workflow("nike shoes", max_pages=2)
```

```
1. Step 1 실행 (crawl_taobao_search.yaml)
   ↓
2. 상품 URL 추출 (_output/taobao/search/text/*_url.txt)
   ↓
3. Step 2 실행 (crawl_taobao_detail.yaml)
   ↓
4. 각 URL을 독립적으로 크롤링
   ↓
5. 전체 결과 집계
```

---

### Workflow 2: 단계별 실행

```python
crawler = TwoStepCrawler("aliexpress")

# 오늘은 Step 1만 실행
urls = crawler.step1_search("shoes", max_pages=5)
# → 100개 상품 URL 수집

# 내일 Step 2 실행 (저장된 URL 사용)
urls = load_urls_from_files("_output/aliexpress/search/text/*_url.txt")
crawler.step2_detail(urls[:10])  # 10개씩 나눠서
```

---

## 📊 사이트별 차이점

| 항목 | Taobao Search | Taobao Detail |
|------|---------------|---------------|
| **페이지** | 검색 결과 | 상품 상세 |
| **셀렉터** | `.item` | `#J_DetailMeta` |
| **스크롤** | 5회 | 10회 |
| **데이터** | 메타데이터 | 전체 콘텐츠 |
| **이미지** | 썸네일 1개 | 갤러리 10+개 |
| **출력** | `search/` | `detail/` |

---

## ✅ 장점

### 1️⃣ **독립성**
- Step 1 실패해도 Step 2 영향 없음
- 각 단계를 개별적으로 재실행 가능

### 2️⃣ **효율성**
- Step 1: 빠르게 많은 상품 스캔
- Step 2: 필요한 상품만 상세 크롤링

### 3️⃣ **유연성**
- Step 1 결과를 검토 후 Step 2 실행 결정
- URL을 필터링하거나 우선순위 지정 가능

### 4️⃣ **확장성**
- 새 사이트 추가: 2개 YAML만 생성
- 각 사이트 독립적으로 최적화

---

## 🎯 실전 시나리오

### 시나리오 1: 대량 상품 수집
```python
# Step 1: 1000개 상품 메타데이터 수집
crawler.step1_search("shoes", max_pages=20)

# 분석: 가격 낮은 순으로 정렬
urls = filter_by_price(load_urls())

# Step 2: 상위 50개만 상세 크롤링
crawler.step2_detail(urls[:50])
```

### 시나리오 2: 일일 모니터링
```python
# 매일 실행: 새 상품 체크
new_urls = crawler.step1_search("new arrivals", max_pages=1)

# 신규 상품만 상세 크롤링
for url in new_urls:
    if not already_crawled(url):
        crawler.step2_detail([url])
```

### 시나리오 3: 사이트 간 비교
```python
# 여러 사이트에서 동일 검색어
sites = ["taobao", "aliexpress", "1688"]

for site in sites:
    crawler = TwoStepCrawler(site)
    crawler.run_full_workflow("nike air max")

# 결과 비교
compare_results(sites)
```

---

## 🚀 다음 단계

1. **번역 통합**: Step 2 결과를 자동 번역
2. **Excel 연동**: Step 1 결과를 Excel로 내보내기
3. **중복 제거**: 동일 상품 필터링
4. **가격 추적**: 정기적으로 Step 1 반복

---

## 💡 핵심 정리

✅ **2개의 독립적인 YAML** = 2단계 크롤링
✅ **Search**: 빠르게 메타데이터 수집
✅ **Detail**: 깊게 전체 콘텐츠 추출
✅ **독립 실행**: 각 단계를 개별적으로 제어
✅ **사이트별 최적화**: HTML 구조에 맞춤
