# WebDriver Anti-Detection 가이드 (간소화)

## 🎯 핵심 전략

### 자동화 탐지 회피 3대 요소
1. **User-Agent (UA)**: Firefox YAML에서 고정 설정
2. **Accept-Language (AL)**: Firefox YAML에서 사이트별 맞춤
3. **세션 관리**: 자동 저장/복원으로 로그인 유지

### 설계 철학
- ❌ **복잡한 랜덤 풀**: 불필요 (UA/AL 고정 사용)
- ❌ **중복 지연 로직**: policy에 이미 있음 (retry_backoff_sec)
- ✅ **간소화된 스크립트**: crawl_utils 모듈 활용
- ✅ **YAML 중심 관리**: 모든 설정은 YAML에서

---

## 📁 파일 구조

```
configs/
├── firefox_taobao.yaml           # Taobao용 Firefox 설정
├── firefox_aliexpress.yaml       # AliExpress용 Firefox 설정
├── crawl_taobao_search.yaml      # Step 1: 검색
├── crawl_taobao_detail.yaml      # Step 2: 상세
└── ...

modules/crawl_utils/utils/
└── anti_detection.py             # UA/AL 풀, 설정 생성기

scripts/
└── crawl_session_managed.py      # 세션 관리형 크롤러

data/session/
├── firefox_taobao.json           # Taobao 세션 (자동 생성)
├── firefox_aliexpress.json       # AliExpress 세션
└── ...
```

---

## 🚀 사용 방법 (간소화)

### 1️⃣ **Firefox YAML에서 UA/AL 직접 관리**

**`configs/firefox_taobao.yaml`**:
```yaml
firefox:
  # 세션 관리
  session_path: "data/session/firefox_taobao.json"
  save_session: true
  
  # UA/AL 고정 (변경 필요시 여기서 직접 수정)
  user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0"
  accept_languages: "zh-CN,zh;q=0.9,ko;q=0.8,en;q=0.7"
  
  # Anti-Detection
  disable_automation: true
  dom_enabled: false
  resist_fingerprint_enabled: false
```

**`configs/firefox_aliexpress.yaml`**:
```yaml
firefox:
  session_path: "data/session/firefox_aliexpress.json"
  save_session: true
  
  user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0"
  accept_languages: "en-US,en;q=0.9,ko;q=0.8"
  
  disable_automation: true
```

**`configs/crawl_{site}_search.yaml`** - 지연/재시도:
```yaml
crawl:
  # 이미 정책에 포함됨
  retries: 3
  retry_backoff_sec: 2.0  # 재시도 간 지연
  
  scroll:
    scroll_pause_sec: 1.0  # 스크롤 지연
```

---

### 2️⃣ **Step 1: 검색 결과 크롤링 (간소화)**

```python
from scripts.crawl_session_managed import SiteCrawler

# 간단한 크롤러
crawler = SiteCrawler("taobao")

# Step 1 실행 (crawl_utils가 모두 처리)
search_dir = crawler.crawl_search("nike shoes", max_pages=2)
# ✅ firefox_taobao.yaml의 UA/AL 자동 적용
# ✅ policy의 retry/delay 자동 적용
# ✅ 세션 자동 저장
```

**출력**:
```
_output/taobao/search/
  images/
    tb_search_0_0_thumb.jpg       # 썸네일
    tb_search_0_1_thumb.jpg
  text/
    tb_search_0_0_url.txt         # 상품 URL
    tb_search_0_0_title.txt       # 상품명
    tb_search_0_0_price.txt       # 가격
    tb_search_0_0_shop.txt        # 상점명
```

---

### 3️⃣ **수동 필터링 (중요!)**

```python
from scripts.crawl_session_managed import manual_filter_urls

# 검색 결과 검토 및 선택
selected_urls = manual_filter_urls(search_dir)
```

**출력**:
```
🔍 수동 필터링 단계
==================
발견된 상품: 15개

1. 나이키 에어맥스 270 남성용 운동화
   가격: ¥399
   URL: https://item.taobao.com/item.htm?id=12345...

2. 나이키 조던 1 레트로 하이
   가격: ¥599
   URL: https://item.taobao.com/item.htm?id=67890...

...

크롤링할 상품 번호를 입력하세요 (예: 1,3,5 또는 1-5):
> 1,2,5

✅ 3개 상품 선택됨
```

---

### 4️⃣ **Step 2: 상세 페이지 크롤링 (간소화)**

```python
# 선택된 상품만 크롤링 (간단!)
crawler.crawl_detail_batch(selected_urls)
# ✅ 모든 설정은 YAML에서
# ✅ retry/delay는 policy에서 자동 처리
```

**실행 로그**:
```
[TAOBAO] Step 2: Detail (3개)
==================================

[1/3] https://item.taobao.com/item.htm?id=12345...
  ✓ 이미지: 12, 텍스트: 8

[2/3] https://item.taobao.com/item.htm?id=67890...
  ✓ 이미지: 15, 텍스트: 10

[3/3] https://item.taobao.com/item.htm?id=99999...
  ✓ 이미지: 10, 텍스트: 7

==================================
✅ 전체: 이미지 37개, 텍스트 25개
```

**출력**:
```
_output/taobao/detail/
  images/
    tb_detail_0_0.jpg             # 메인 이미지 1
    tb_detail_0_1.jpg             # 메인 이미지 2
    tb_detail_0_2.jpg             # 설명 이미지 1
    ...
  text/
    tb_detail_0_0_type.txt        # "main_gallery"
    tb_detail_0_0_text.txt        # 제목
    tb_detail_0_1_text.txt        # 설명
    ...
```

---

## � UA/AL 변경 방법 (고정 관리)

### Firefox YAML에서 직접 수정

필요시 `configs/firefox_{site}.yaml` 파일을 편집:

```yaml
# 예: 탐지되면 UA 변경
user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"

# 또는 AL 변경
accept_languages: "zh-CN,zh-TW;q=0.9,zh;q=0.8,en;q=0.7"
```

### UA/AL 예시 (참고용)

`modules/crawl_utils/utils/anti_detection.py`:
```python
# Firefox UA 예시
FIREFOX_UA_EXAMPLES = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

# AL 예시
ACCEPT_LANGUAGE_EXAMPLES = {
    "korean": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "chinese": "zh-CN,zh;q=0.9,ko;q=0.8,en;q=0.7",
    "english": "en-US,en;q=0.9,ko;q=0.8",
}
```

### 재시도/지연 설정 (Policy)

`configs/crawl_{site}_search.yaml`:
```yaml
crawl:
  retries: 3                 # 실패 시 재시도
  retry_backoff_sec: 2.0     # 재시도 간 지연 (초)
  
  scroll:
    scroll_pause_sec: 1.0    # 스크롤 지연
  
  wait:
    timeout_sec: 15.0        # 대기 시간
```

---

## 💾 세션 관리

### 세션 저장
```python
# WebDriver 종료 시 자동 저장
driver = create_webdriver("firefox", config)
# ... 작업 ...
driver.close()  # ← 여기서 세션 저장
```

**저장 내용** (`data/session/firefox_taobao.json`):
```json
{
  "cookies": [
    {"name": "_tb_token_", "value": "xxx", "domain": ".taobao.com"},
    {"name": "cookie2", "value": "yyy", "domain": ".taobao.com"}
  ],
  "local_storage": {...},
  "session_storage": {...}
}
```

### 세션 복원
```python
# WebDriver 생성 시 자동 복원
driver = create_webdriver("firefox", config)
# → data/session/firefox_taobao.json 로드
# → 쿠키/스토리지 복원
# → 로그인 상태 유지됨!
```

---

## 🎯 실전 워크플로우 (간소화)

### Scenario 1: 기본 워크플로우

```python
from scripts.crawl_session_managed import SiteCrawler, manual_filter_urls

# 1. 검색
crawler = SiteCrawler("taobao")
search_dir = crawler.crawl_search("nike shoes", max_pages=3)

# 2. 수동 필터링
selected_urls = manual_filter_urls(search_dir)

# 3. 상세 크롤링
crawler.crawl_detail_batch(selected_urls)
# ✅ 간단! 모든 설정은 YAML에서
```

### Scenario 2: 사이트 간 전환

```python
# Taobao
taobao = SiteCrawler("taobao")
taobao.crawl_search("shoes", max_pages=2)

# AliExpress (독립된 세션/설정)
ali = SiteCrawler("aliexpress")
ali.crawl_search("shoes", max_pages=2)
```

### Scenario 3: 단일 상품 크롤링

```python
crawler = SiteCrawler("taobao")

# 특정 URL만 크롤링
result = crawler.crawl_detail("https://item.taobao.com/...")
print(f"이미지: {result['images']}, 텍스트: {result['texts']}")
```

---

## ⚙️ Anti-Detection 체크리스트 (간소화)

### ✅ Firefox YAML 필수 설정
```yaml
firefox:
  disable_automation: true       # navigator.webdriver 제거
  dom_enabled: false             # dom.webdriver.enabled = false
  save_session: true             # 세션 저장/복원
  headless: false                # GUI 모드 (탐지 적음)
  
  user_agent: "Mozilla/5.0 ..."  # 고정 UA
  accept_languages: "zh-CN,..."  # 사이트별 맞춤
```

### ✅ Crawl YAML 필수 설정
```yaml
crawl:
  retries: 3                     # 재시도
  retry_backoff_sec: 2.0         # 재시도 간 지연
  
  scroll:
    scroll_pause_sec: 1.0        # 스크롤 지연
  
  wait:
    timeout_sec: 15.0            # 대기 시간
```

### ⚠️ 주의사항
- UA/AL 변경 필요시 → Firefox YAML 직접 수정
- 지연 조정 필요시 → Crawl YAML의 policy 수정
- 세션 백업: `copy data\session\firefox_taobao.json backup\`
- Headless 사용 지양 (탐지 확률 높음)

---

## 📊 요약 (간소화)

| 항목 | 관리 위치 | 설명 |
|------|----------|------|
| **UA/AL** | `firefox_{site}.yaml` | 고정 값, 직접 수정 |
| **재시도/지연** | `crawl_{site}_*.yaml` | policy에서 관리 |
| **세션** | `data/session/*.json` | 자동 저장/복원 |
| **크롤러** | `crawl_session_managed.py` | 간소화된 스크립트 |
| **필터링** | `manual_filter_urls()` | Step 1 → Step 2 |

---

## 💡 핵심 정리 (간소화)

1. ✅ **UA/AL 고정** → Firefox YAML에서 직접 관리
2. ✅ **재시도/지연** → Policy에 이미 있음 (중복 제거)
3. ✅ **간소화된 스크립트** → crawl_utils 모듈 활용
4. ✅ **수동 필터링** → Step 1/2 독립 실행
5. ✅ **세션 관리** → 자동 저장/복원

→ **YAML 중심 관리 + 간소화된 코드!** 🎯
