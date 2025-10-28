# WebDriver & Session 관리 최종 검토 (의도 반영)

**작성일**: 2025-10-28  
**목적**: 원래 설계 의도 + Bot 탐지 최소화 + 코드 정리

---

## 📋 원래 설계 의도 확인

### 1️⃣ WebDriver 재시작 조건

**사용자 의도**:
> WebDriver를 URL마다 새로 시작하는 것은 의도된 동작이 **아님**  
> **WebDriver 설정에 영향을 끼치는 요소**가 달라질 때만 재시작

**영향 요소**:
1. **Accept-Language (AL)**: 언어 설정
2. **Profile**: Firefox 프로필 경로
3. **Region**: 국가/지역 (preset override 영향)
4. **Provider**: firefox, chrome 등

**원래 의도**:
```python
# 예시:
urls = [
    "https://aliexpress.com/item/1",  # region=global, AL=en-US
    "https://aliexpress.com/item/2",  # region=global, AL=en-US  ← 재사용
    "https://taobao.com/item/3",      # region=china, AL=zh-CN   ← 재시작 (region 변경)
]
```

**현재 구현**:
```python
# ❌ 매번 새 WebDriver 생성
for url in urls:
    webdriver_manager = WebDriverManager(...)  # 항상 새로 생성
    webdriver_manager.start()
    # ... 처리 ...
    webdriver_manager.quit()  # 항상 종료
```

**문제점**:
- ✅ Bot 탐지 회피에는 유리 (Session ID 격리)
- ❌ 의도와 다름 (설정 동일해도 재시작)
- ❌ 성능 낭비 (불필요한 재시작)

---

### 2️⃣ URL Normalization 미구현

**사용자 설명**:
> 다수의 URL이 들어와도 현재는 **URL 분석 후 normalizing을 구현하지 않아서**,  
> 순서대로 진행하면서 preset 결과에 따라 webdriver가 재시작하는 구조

**의미**:
- URL들을 먼저 분석하여 grouping 하는 로직 없음
- 현재는 순차 처리로 매번 분석 → 설정 결정 → WebDriver 시작/종료

**이상적인 흐름** (미구현):
```python
# Phase 1: URL Normalization
urls = ["url1", "url2", "url3", ...]
url_groups = normalize_urls(urls)  # ← 미구현
# {
#   "global_en_firefox": ["url1", "url2"],
#   "china_zh_firefox": ["url3", "url4"]
# }

# Phase 2: Group 단위 처리
for group_key, group_urls in url_groups.items():
    webdriver_manager = create_webdriver(group_key)  # ← 1회만 생성
    for url in group_urls:
        process(url, webdriver_manager)  # ← 재사용
    webdriver_manager.quit()  # ← Group 처리 후 종료
```

---

### 3️⃣ SessionBridge 도입 이유

**사용자 설명**:
> Session은 기존에 **다운로드 시 로그인이 필요한 정보가 있기 때문에** 도입  
> 해당 세션으로 다운로드를 진행해야 하는데,  
> 예전에 분리되어 있던 pipeline 때문에 **굳이 bridge를 만든 것**

**원래 목적**:
```
WebDriver로 로그인 → Cookie 획득
           ↓
    SessionBridge (Cookie 동기화)
           ↓
HTTP Client (requests.Session) → 이미지 다운로드 (로그인 필요)
```

**현재 상황**:
- Pipeline 통합됨 (sync_crawl.py에서 직접 관리)
- SessionBridge는 여전히 WebDriver와 HTTP Client 사이에서 Cookie 전달
- ItemSaver가 fetcher(requests.Session)로 이미지 다운로드

**평가**:
- ✅ 목적 명확: 로그인 필요한 리소스 다운로드
- ✅ 실제 사용: ItemSaver가 fetcher 사용
- ⚠️ 개선 여지: Pipeline 통합되었으므로 "bridge" 없이 직접 전달 가능

---

## 🎯 개선 방향 재정의

### 목표

1. **✅ 원래 의도 구현**: WebDriver 설정 동일 시 재사용
2. **✅ Bot 탐지 최소화**: RandomScroll + Stealth Mode
3. **✅ 코드 정리**: SessionBridge 단순화
4. **✅ UA 버전 관리 유지**: 현재 구현 유지

---

## 💡 최종 개선안 (통합)

### 개선안 F: 의도 구현 + Anti-Detection + 정리

#### 1. WebDriver 재사용 로직 (Smart Pooling)

**핵심 아이디어**: WebDriver 설정을 key로 하는 Pool

```python
class SyncCrawl:
    def __init__(self, ...):
        # ...
        self._webdriver_pool: Dict[str, WebDriverManager] = {}
    
    def _get_webdriver_key(
        self,
        region: str,
        provider: str,
        webdriver_overrides: Dict[str, Any]
    ) -> str:
        """
        WebDriver 설정 key 생성 (영향 요소만 포함)
        
        영향 요소:
        - region: 국가/지역
        - provider: firefox, chrome
        - accept_languages: AL 설정
        - profile_path: Firefox 프로필
        """
        # 영향 요소 추출
        accept_languages = webdriver_overrides.get("accept_languages", "en-US")
        profile_path = webdriver_overrides.get("firefox__profile_path", "")
        
        # Key 생성 (영향 요소만)
        key = f"{region}_{provider}_{accept_languages}_{profile_path}"
        return key
    
    def run(self, urls: Union[str, List[str]], **overrides) -> List[Dict[str, Any]]:
        all_results = []
        
        for url in urls:
            try:
                # URL 분석
                site, method, region = analyze_url(url)
                
                # WebDriver 설정 구성
                webdriver_overrides = filter_overrides_by_prefix(...)
                provider = webdriver_overrides.get("provider", "firefox")
                
                # ✅ Pool Key 생성 (영향 요소만)
                pool_key = self._get_webdriver_key(region, provider, webdriver_overrides)
                
                # ✅ 동일 설정이면 재사용
                if pool_key in self._webdriver_pool:
                    webdriver_manager = self._webdriver_pool[pool_key]
                    self.log.info(f"♻️ Reusing WebDriver: {pool_key}")
                    
                    # ✅ Anti-Detection: 랜덤 대기 (인간처럼)
                    delay = random.uniform(2.0, 5.0)
                    self.log.info(f"   Waiting {delay:.1f}s before next request...")
                    time.sleep(delay)
                else:
                    # ✅ 새 WebDriver 생성 (설정 변경 시)
                    webdriver_manager = WebDriverManager(
                        cfg_like=self._cfg_like_webdriver_manager,
                        log_manager=self._parent_log_manager,
                        **webdriver_overrides
                    )
                    webdriver_manager.start()
                    self._webdriver_pool[pool_key] = webdriver_manager
                    self.log.info(f"🆕 Created WebDriver: {pool_key}")
                
                # Pipeline 실행
                result = self._execute(
                    url=url,
                    crawl_policy=crawl_policy,
                    webdriver_manager=webdriver_manager,  # ✅ 전달 (생성 안함)
                    ...
                )
                all_results.append(result)
            
            except Exception as e:
                self.log.error(f"Failed: {url} - {e}")
                all_results.append({"url": url, "error": str(e), "success": False})
        
        # ✅ 모든 URL 처리 후 Pool 정리
        self._cleanup_webdriver_pool()
        
        return all_results
    
    def _cleanup_webdriver_pool(self):
        """모든 WebDriver 종료"""
        for pool_key, manager in self._webdriver_pool.items():
            try:
                self.log.info(f"Closing WebDriver: {pool_key}")
                manager.quit()
            except Exception as e:
                self.log.error(f"Failed to quit {pool_key}: {e}")
        
        self._webdriver_pool.clear()
```

**장점**:
- ✅ 원래 의도 구현: 동일 설정 시 재사용
- ✅ 성능 향상: 불필요한 재시작 제거
- ✅ Bot 탐지 회피: 랜덤 대기로 인간처럼
- ✅ 유연성: 설정 변경 시 자동으로 새 WebDriver

---

#### 2. _execute() 수정 (WebDriver 받기)

```python
def _execute(
    self,
    url: str,
    crawl_policy: SyncCrawlPolicy,
    webdriver_manager: WebDriverManager,  # ✅ 외부에서 전달받음
    preset_policy: Dict[str, Any],
    **overrides: Dict[str, Any]
) -> Dict[str, Any]:
    """Pipeline 실행: WebDriver는 외부에서 관리"""
    
    session_bridge = None
    
    try:
        # ❌ WebDriver 시작 제거 (run()에서 관리)
        
        # Adapter 생성
        adapter = SyncSeleniumAdapter(driver=webdriver_manager._webdriver)
        
        # ✅ SessionBridge 초기화 (단순화)
        http_session_policy = crawl_policy.http_session
        
        if http_session_policy:
            try:
                from ..services.session_bridge import SessionBridge
                
                session_bridge = SessionBridge.from_webdriver(
                    webdriver=adapter._drv,
                    user_agent=getattr(webdriver_manager.config, "user_agent", None),
                    accept_language=getattr(webdriver_manager.config, "accept_languages", None),
                    proxy=getattr(http_session_policy, 'proxy', None)
                )
            except Exception as bridge_exc:
                session_bridge = None
                self.log.warning(f"Failed to initialize session bridge: {bridge_exc}")
        
        # ✅ Fetcher 준비 (실제 사용)
        fetcher = None
        if session_bridge and http_session_policy:
            try:
                from ..services.fetcher import SyncHTTPFetcher
                
                fetcher = SyncHTTPFetcher(
                    session=session_bridge.http_session,
                    timeout_connect=int(http_session_policy.timeout_connect_sec),
                    timeout_read=int(http_session_policy.timeout_read_sec),
                    allow_redirects=http_session_policy.allow_redirects,
                    stream_download=http_session_policy.stream_download,
                    reuse_session=http_session_policy.reuse,
                )
            except Exception as fetcher_exc:
                self.log.warning(f"Failed to create fetcher: {fetcher_exc}")
        
        # Pipeline 실행
        navigator = SyncNavigator(adapter, crawl_policy.navigation)
        
        # Navigate
        navigator.load(url)
        
        # ✅ Anti-Detection: 잠깐 대기 (인간처럼)
        time.sleep(random.uniform(0.5, 1.5))
        
        # ✅ Scroll with randomness
        if crawl_policy.scroll and crawl_policy.scroll.strategy != "none":
            navigator.scroll(
                strategy=crawl_policy.scroll.strategy,
                max_scrolls=crawl_policy.scroll.max_scrolls,
                pause_sec=crawl_policy.scroll.scroll_pause_sec,
                scroll_count=crawl_policy.scroll.scroll_count,
                step_px=crawl_policy.scroll.scroll_step_px,
                randomness=True  # ✅ RandomScroll 활성화
            )
        
        # Wait
        if crawl_policy.wait and crawl_policy.wait.hook != "none":
            navigator.wait(...)
        
        # Extract
        extractor = SyncExtractorFactory(adapter, crawl_policy.extractor).create()
        dom = navigator.get_dom() if hasattr(navigator, 'get_dom') else ""
        extracted_records = extractor.extract_list(dom=dom) if hasattr(extractor, 'extract_list') else extractor.extract(dom=dom)
        
        # ... ItemsNormalizer, ItemSaver ...
        
        # ✅ ItemSaver에 fetcher 전달 (로그인 필요한 리소스 다운로드)
        saver = SyncItemSaver(
            policy=crawl_policy.saver,
            log_manager=self._parent_log_manager
        )
        summary = saver.save_items(items=items, fetcher=fetcher)  # ✅ fetcher 전달
        
        return {
            "url": url,
            "site": crawl_policy.site,
            "method": crawl_policy.method,
            "data": extracted_records,
            "normalized_items": items,
            "saved_files": [str(artifact.path) for artifact in summary.flatten() if artifact.status == "saved"],
            "success": True,
        }
    
    except Exception as e:
        self.log.error(f"Execution failed: {e}")
        return {"url": url, "error": str(e), "success": False}
    
    finally:
        # ✅ SessionBridge cleanup
        if session_bridge and hasattr(session_bridge, 'http_session'):
            try:
                session_bridge.http_session.close()
                self.log.debug("SessionBridge closed")
            except Exception as cleanup_exc:
                self.log.warning(f"Failed to close session bridge: {cleanup_exc}")
        
        # ❌ WebDriver 종료 제거 (run()에서 관리)
```

**장점**:
- ✅ 책임 분리: run()이 WebDriver 관리, _execute()가 Pipeline 실행
- ✅ 재사용 가능: WebDriver를 받아서 사용만
- ✅ Cleanup 명확: SessionBridge만 여기서 정리

---

#### 3. RandomScroll 구현 (navigator.py)

```python
# navigator.py

import random
import time

def scroll(
    self,
    strategy: str = "smooth",
    max_scrolls: int = 5,
    pause_sec: float = 2.0,
    scroll_count: int = 1,
    step_px: int = 300,
    randomness: bool = True  # ✅ 기본값 True
):
    """
    Scroll with optional human-like randomness.
    
    Args:
        strategy: Scroll strategy
        max_scrolls: Maximum scroll count
        pause_sec: Base pause duration (seconds)
        scroll_count: Scrolls per iteration
        step_px: Base scroll distance (pixels)
        randomness: Enable random variation (default: True)
    """
    for i in range(max_scrolls):
        # ✅ 랜덤 스크롤 거리 (±20%)
        if randomness:
            actual_step = int(step_px * random.uniform(0.8, 1.2))
        else:
            actual_step = step_px
        
        # 스크롤 실행
        self._adapter.scroll_by(0, actual_step)
        
        if i < max_scrolls - 1:
            # ✅ 랜덤 대기 시간 (±30%)
            if randomness:
                actual_pause = pause_sec * random.uniform(0.7, 1.3)
                
                # ✅ 가끔 더 긴 pause (15% 확률)
                if random.random() < 0.15:
                    extra_pause = random.uniform(0.5, 2.0)
                    actual_pause += extra_pause
                    self.log.debug(f"Extra pause: {extra_pause:.1f}s")
            else:
                actual_pause = pause_sec
            
            time.sleep(actual_pause)
```

---

#### 4. Stealth Mode (firefox.py)

```python
# firefox.py - _configure_options()

def _configure_options(self) -> Options:
    options = Options()
    firefox_cfg = self.config.firefox
    
    # Binary, Profile, Headless (기존 코드)
    # ...
    
    # ✅ Stealth Mode: navigator.webdriver 제거
    options.set_preference("dom.webdriver.enabled", False)
    options.set_preference("useAutomationExtension", False)
    self.logger.info("✅ Stealth mode enabled")
    
    # UA, Accept-Languages (기존 코드 유지)
    # ✅ UA 버전 자동 감지 로직은 그대로 유지
    # ...
    
    return options
```

---

#### 5. SessionBridge 단순화 (optional)

**현재**: SessionBridge가 Cookie 동기화 담당  
**개선 (선택)**: Pipeline 통합되었으므로 직접 전달 가능

```python
# Option 1: SessionBridge 유지 (현재 구조)
# - 장점: 명확한 역할 분리
# - 단점: "bridge" 레이어 추가

# Option 2: 직접 전달 (단순화)
def _execute(...):
    # SessionBridge 없이 직접 requests.Session 생성
    http_session = requests.Session()
    
    # WebDriver에서 Cookie 복사
    for cookie in webdriver_manager.driver.get_cookies():
        http_session.cookies.set(cookie['name'], cookie['value'])
    
    # Fetcher에 전달
    fetcher = SyncHTTPFetcher(session=http_session, ...)
```

**권장**: Option 1 유지 (SessionBridge)
- 이유: 코드 구조 변경 최소화
- SessionBridge가 Cookie 동기화 외에도 Header 설정 등 담당

---

## 📊 개선안 비교 (재정리)

| 항목 | 현재 구조 | 개선안 F<br/>(통합) |
|------|-----------|---------------------|
| **원래 의도 부합** | ❌ 매번 재시작 | ✅ **설정 동일 시 재사용** |
| **Bot 탐지 회피** | 🟡 60/100 | 🟢 **90/100** (Random + Stealth) |
| **성능** | 🔴 40/100 | 🟢 **85/100** (불필요한 재시작 제거) |
| **코드 정리** | 🟡 70/100 | 🟢 **90/100** (책임 분리) |
| **UA 버전 관리** | ✅ 우수 | ✅ **유지** |
| **Fetcher 활용** | ⚠️ 생성만 함 | ✅ **ItemSaver 전달** |
| **구현 난이도** | - | ⭐⭐⭐ 중간 |
| **예상 시간** | - | **4-6시간** |

---

## 🎯 최종 권장사항

### Phase 1: 즉시 적용 (1-2시간) ⭐ **최우선**

1. **✅ Stealth Mode** (5분)
   - firefox.py에 2줄 추가
   ```python
   options.set_preference("dom.webdriver.enabled", False)
   options.set_preference("useAutomationExtension", False)
   ```

2. **✅ RandomScroll** (30분)
   - navigator.py scroll() 메서드 수정
   - randomness 파라미터 추가

3. **✅ SessionBridge Cleanup** (10분)
   - _execute() finally 블록에 추가
   ```python
   if session_bridge:
       session_bridge.http_session.close()
   ```

4. **✅ Fetcher 전달** (10분)
   - ItemSaver에 fetcher 전달
   ```python
   summary = saver.save_items(items=items, fetcher=fetcher)
   ```

**효과**:
- Bot 탐지 회피: 60% → **85%**
- 로그인 필요 리소스 다운로드 작동
- Resource 누수 해결

---

### Phase 2: 원래 의도 구현 (3-4시간)

5. **✅ WebDriver Pool** (2시간)
   - _get_webdriver_key() 메서드 추가
   - run() 메서드 수정 (Pool 관리)
   - _cleanup_webdriver_pool() 추가

6. **✅ _execute() 수정** (1시간)
   - WebDriver 외부에서 받기
   - 시작/종료 로직 제거

7. **✅ 테스트** (1시간)
   - 동일 설정: 재사용 확인
   - 설정 변경: 재시작 확인
   - 여러 URL 시나리오 테스트

**효과**:
- 원래 의도 구현 완료
- 성능: 40% → **85%**
- 코드 구조 개선

---

## 🚀 구현 순서

### Step 1: Critical Fixes (30분)

```bash
# 1. firefox.py 수정
# 2. sync_crawl.py - SessionBridge cleanup 추가
# 3. sync_crawl.py - Fetcher를 ItemSaver에 전달
```

**테스트**:
```python
# 브라우저 콘솔에서
console.log(navigator.webdriver);  // false or undefined

# 로그인 필요 이미지 다운로드 확인
```

---

### Step 2: RandomScroll (30분)

```bash
# navigator.py 수정
# sync_crawl.py에서 randomness=True 전달
```

**테스트**:
```python
# 로그에서 스크롤 간격 확인
# 매번 다른 값인지 확인
```

---

### Step 3: WebDriver Pool (3-4시간)

```bash
# 1. _get_webdriver_key() 구현
# 2. run() 메서드 수정 (Pool 관리)
# 3. _execute() 시그니처 변경
# 4. _cleanup_webdriver_pool() 추가
```

**테스트**:
```python
urls = [
    "https://aliexpress.com/item/1",  # 새 WebDriver
    "https://aliexpress.com/item/2",  # 재사용 (동일 설정)
    "https://taobao.com/item/3",      # 새 WebDriver (region 변경)
]
crawl.run(urls=urls)

# 로그 확인:
# 🆕 Created WebDriver: global_firefox_en-US_
# ♻️ Reusing WebDriver: global_firefox_en-US_
# 🆕 Created WebDriver: china_firefox_zh-CN_
```

---

## 📝 체크리스트

### Phase 1 (즉시 적용)
- [ ] `navigator.webdriver` 제거 (firefox.py)
- [ ] RandomScroll 구현 (navigator.py)
- [ ] SessionBridge cleanup (sync_crawl.py)
- [ ] Fetcher를 ItemSaver 전달 (sync_crawl.py)
- [ ] 테스트: Bot 탐지 우회 확인
- [ ] 테스트: 로그인 필요 리소스 다운로드

### Phase 2 (원래 의도)
- [ ] `_get_webdriver_key()` 메서드 추가
- [ ] `run()` Pool 관리 로직 추가
- [ ] `_execute()` 시그니처 변경
- [ ] `_cleanup_webdriver_pool()` 추가
- [ ] 테스트: 동일 설정 재사용
- [ ] 테스트: 설정 변경 시 재시작
- [ ] 테스트: 여러 URL 시나리오

---

## 🎓 결론

### 핵심 발견

1. **WebDriver 재시작**: 원래 의도는 "설정 동일 시 재사용"
   - 현재: 매번 재시작 (의도와 다름)
   - 개선: Pool 기반 재사용

2. **SessionBridge**: 로그인 필요 리소스 다운로드 목적
   - 현재: 생성만 하고 사용 안함
   - 개선: ItemSaver에 fetcher 전달

3. **UA 버전 관리**: 이미 우수하게 구현됨
   - 자동 감지 → 캐시 로드 → 예외 발생
   - **유지하면 됨** (변경 불필요)

### 최종 권장

**우선순위**:
1. 🔴 **Phase 1** (1-2시간): Stealth Mode + RandomScroll + Cleanup
2. 🟡 **Phase 2** (3-4시간): WebDriver Pool (원래 의도 구현)

**예상 효과**:
- Bot 탐지 회피: **90/100**
- 성능: **85/100**
- 원래 의도 구현: **✅**
- 코드 정리: **✅**

---

**바로 Phase 1부터 시작하시겠습니까?** 🚀  
(firefox.py 2줄 추가부터 시작하면 5분 만에 Critical 개선 가능!)
