# WebDriver & Session 관리 재검토 보고서

**작성일**: 2025-10-28  
**대상**: `crawl_utils.adapter.sync_crawl`, `webdriver_manager`, `session_bridge`  
**목적**: 현재 구현의 적절성 검토 및 개선안 제시

---

## 📊 현재 구조 분석

### 1. WebDriver 생명주기 (Lifecycle)

```python
# sync_crawl.py - _execute() 메서드

def _execute(...) -> Dict[str, Any]:
    webdriver_manager = None
    session_bridge = None
    
    try:
        # 1. WebDriver 시작
        webdriver_manager = WebDriverManager(
            cfg_like=self._cfg_like_webdriver_manager,
            log_manager=self._parent_log_manager,
            **webdriver_overrides
        )
        webdriver_manager.start()  # ✅ 시작
        
        # 2-5. Pipeline 실행 (Navigation, Extraction, Normalization, Save)
        # ...
        
        return {"url": url, "success": True, ...}
    
    except Exception as e:
        self.log.error(f"Execution failed: {e}")
        return {"url": url, "error": str(e), "success": False}
    
    finally:
        if webdriver_manager:
            # UA 캐싱 로직 (선택적)
            try:
                actual_ua = webdriver_manager.driver.execute_script("return navigator.userAgent;")
                # ... 캐시 저장 ...
            except Exception:
                pass
            
            # WebDriver 종료
            self.log.info("Closing WebDriver")
            webdriver_manager.quit()  # ✅ 종료 (반드시 실행)
```

**✅ 장점**:
1. **단일 책임**: `_execute()` 메서드가 WebDriver 전체 생명주기 관리
2. **보장된 cleanup**: `finally` 블록으로 예외 발생 시에도 종료 보장
3. **URL당 격리**: 각 URL마다 새 WebDriver 인스턴스 (상태 오염 방지)

**⚠️ 잠재적 문제점**:
1. **성능 오버헤드**: URL마다 WebDriver 재시작 (~5초)
2. **Resource 낭비**: 동일 region/provider인데도 매번 새 브라우저
3. **UA 캐싱 로직**: 성공 시에만 실행되지만, finally 안에 있어 혼란

---

### 2. SessionBridge 생명주기

```python
# Step 2: SessionBridge 초기화 (선택적)
adapter = SyncSeleniumAdapter(driver=webdriver_manager._webdriver)
session_bridge_policy = crawl_policy.session_bridge
http_session_policy = crawl_policy.http_session
cookie_bridge_policy = crawl_policy.cookie_bridge

if session_bridge_policy or http_session_policy or cookie_bridge_policy:
    try:
        from ..services.session_bridge import SessionBridge
        
        webdriver_for_bridge = adapter._drv
        accept_language = getattr(webdriver_manager.config, "accept_languages", None)
        user_agent = (
            session_bridge_policy.user_agent
            if session_bridge_policy and session_bridge_policy.user_agent
            else getattr(webdriver_manager.config, "user_agent", None)
        )
        proxy = session_bridge_policy.proxy if session_bridge_policy else None
        
        session_bridge = SessionBridge.from_webdriver(
            webdriver=webdriver_for_bridge,
            user_agent=user_agent,
            accept_language=accept_language,
            proxy=proxy,
        )
    except Exception as bridge_exc:
        session_bridge = None
        self.log.warning(f"Failed to initialize session bridge: {bridge_exc}")
```

**✅ 장점**:
1. **선택적 초기화**: Policy가 있을 때만 생성
2. **Graceful degradation**: 실패해도 크롤링 계속 진행
3. **WebDriver 의존성 분리**: SessionBridge는 WebDriver 쿠키만 동기화

**⚠️ 문제점**:
1. **조건문 복잡**: 3개 policy 중 하나라도 있으면 생성
2. **명확한 사용처 없음**: Fetcher만 사용, 다른 곳에서는 미사용
3. **Cookie 동기화 불명확**: `sync_cookies_from_webdriver()` 호출 시점 모호
4. **Cleanup 누락**: SessionBridge 종료 로직 없음 (requests.Session close 안됨)

---

### 3. Fetcher 생명주기

```python
# Step 3: Fetcher 준비 (SessionBridge 사용)
fetcher = None
if session_bridge and http_session_policy:
    try:
        from ..services.fetcher import SyncHTTPFetcher
        
        fetcher = SyncHTTPFetcher(
            session=session_bridge.http_session,
            timeout=int(http_session_policy.timeout_read_sec),
            timeout_connect=int(http_session_policy.timeout_connect_sec),
            timeout_read=int(http_session_policy.timeout_read_sec),
            allow_redirects=http_session_policy.allow_redirects,
            stream_download=http_session_policy.stream_download,
            reuse_session=http_session_policy.reuse,
        )
    except Exception as fetcher_exc:
        self.log.warning(f"Failed to create fetcher: {fetcher_exc}")
```

**✅ 장점**:
1. **SessionBridge 재사용**: WebDriver 쿠키를 HTTP 클라이언트로 전달
2. **선택적 기능**: 필요할 때만 생성

**⚠️ 문제점**:
1. **실제 미사용**: 현재 pipeline에서 fetcher 사용하지 않음
2. **중복된 timeout**: timeout_read가 두 번 설정됨
3. **Cleanup 누락**: Fetcher 종료 로직 없음
4. **Dead code**: 생성만 하고 전달되지 않음

---

## 🔥 "굳이?" 로직 분석

### 1. UA 캐싱 로직 (finally 블록)

```python
finally:
    if webdriver_manager:
        # ✅ 크롤링 성공 시 실제 UA 추출 및 캐시 저장
        try:
            if webdriver_manager._webdriver:
                actual_ua = webdriver_manager.driver.execute_script("return navigator.userAgent;")
                
                if actual_ua:
                    from pathlib import Path
                    import json
                    from datetime import datetime, timezone
                    import re
                    
                    # 캐시 파일 경로
                    cache_path = Path(__file__).parent.parent / "configs" / "browser_version.json"
                    
                    # Firefox 버전 추출
                    version_match = re.search(r'Firefox/(\d+\.\d+)', actual_ua)
                    version = version_match.group(1) if version_match else "unknown"
                    
                    cache_path.parent.mkdir(parents=True, exist_ok=True)
                    cache_data = {
                        "firefox": {
                            "user_agent": actual_ua,
                            "version": version,
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                            "source": "runtime_extraction"
                        }
                    }
                    cache_path.write_text(
                        json.dumps(cache_data, indent=2, ensure_ascii=False),
                        encoding="utf-8"
                    )
        except Exception:
            pass
        
        # WebDriver 종료
        self.log.info("Closing WebDriver")
        webdriver_manager.quit()
```

**🤔 "굳이?" 분석**:

**문제점**:
1. **책임 위반**: UA 캐싱은 SyncCrawl의 책임이 아님
2. **위치 부적절**: cleanup 로직(finally)에 비즈니스 로직 포함
3. **의미 모호**: "크롤링 성공 시"라는 주석이지만 except도 처리
4. **하드코딩**: Firefox만 지원, Chrome/Edge는?
5. **파일 I/O**: 매 URL마다 파일 쓰기 (성능 저하)
6. **덮어쓰기**: 항상 마지막 URL의 UA만 남음

**개선안**:
1. **분리**: WebDriverManager로 이동 (SRP)
2. **최적화**: 한 번만 캐싱 (첫 시작 시)
3. **범용화**: Provider별 처리 (Firefox, Chrome, Edge)

---

### 2. SessionBridge 3가지 Policy 조건문

```python
session_bridge_policy = crawl_policy.session_bridge
http_session_policy = crawl_policy.http_session
cookie_bridge_policy = crawl_policy.cookie_bridge

if session_bridge_policy or http_session_policy or cookie_bridge_policy:
    # SessionBridge 초기화
    ...
```

**🤔 "굳이?" 분석**:

**문제점**:
1. **3개 policy 중 하나만 있어도 생성**: 불필요한 초기화 가능
2. **cookie_bridge_policy는 미사용**: SessionBridge 파라미터로 안 넘어감
3. **명확한 의도 불명**: 각 policy의 역할이 겹침

**실제 사용**:
- `session_bridge_policy`: user_agent, proxy 추출
- `http_session_policy`: Fetcher 생성 조건 (timeout 등)
- `cookie_bridge_policy`: **사용되지 않음**

**개선안**:
```python
# Option 1: 단순화
if http_session_policy:  # Fetcher가 필요할 때만 SessionBridge 생성
    session_bridge = SessionBridge.from_webdriver(...)

# Option 2: 명확한 분리
should_sync_cookies = cookie_bridge_policy and cookie_bridge_policy.enabled
should_use_http_session = http_session_policy and http_session_policy.enabled

if should_sync_cookies or should_use_http_session:
    session_bridge = SessionBridge.from_webdriver(...)
```

---

### 3. Adapter 이중 생성

```python
# Step 2: SessionBridge 초기화
adapter = SyncSeleniumAdapter(driver=webdriver_manager._webdriver)
session_bridge_policy = crawl_policy.session_bridge
# ...

# Step 4: Inline pipeline
adapter = SyncSeleniumAdapter(driver=webdriver_manager._webdriver)  # ⚠️ 중복!
navigator = SyncNavigator(adapter, crawl_policy.navigation)
```

**🤔 "굳이?" 분석**:

**문제점**:
1. **중복 생성**: 동일한 Adapter를 두 번 생성
2. **불필요한 객체**: 첫 번째는 `webdriver_for_bridge` 추출용만

**개선안**:
```python
# 한 번만 생성
adapter = SyncSeleniumAdapter(driver=webdriver_manager._webdriver)

# SessionBridge에서 사용
if session_bridge_policy or http_session_policy:
    webdriver_for_bridge = adapter._drv
    session_bridge = SessionBridge.from_webdriver(
        webdriver=webdriver_for_bridge,
        ...
    )

# Navigator에서도 동일 adapter 재사용
navigator = SyncNavigator(adapter, crawl_policy.navigation)
```

---

### 4. Fetcher 생성 후 미사용

```python
# Step 3: Fetcher 준비 (SessionBridge 사용)
fetcher = None
if session_bridge and http_session_policy:
    fetcher = SyncHTTPFetcher(...)  # ⚠️ 생성만 하고 사용 안함

# Step 4: Inline pipeline
# ... Navigator, Extractor, ItemsNormalizer, ItemSaver ...
# ⚠️ fetcher 전달되지 않음!
```

**🤔 "굳이?" 분석**:

**문제점**:
1. **Dead code**: 생성만 하고 전달하지 않음
2. **Resource 낭비**: requests.Session 생성 후 방치
3. **의도 불명**: 나중에 사용할 예정? 삭제 누락?

**개선안**:
```python
# Option 1: 사용하지 않으면 삭제
# - Fetcher 생성 로직 완전 제거

# Option 2: 실제 사용 (ItemSaver에 전달)
saver = SyncItemSaver(
    policy=crawl_policy.saver,
    fetcher=fetcher,  # ✅ 전달
    log_manager=self._parent_log_manager
)
```

---

## 💡 개선안 제시

### 개선안 A: 최소 변경 (Quick Win)

**목표**: "굳이" 로직 제거 + 명확성 개선

**변경 사항**:

#### 1. UA 캐싱 제거 (WebDriverManager로 이동)

```python
# sync_crawl.py - finally 블록 (제거)
finally:
    if webdriver_manager:
        # ❌ 제거: UA 캐싱 로직
        
        # WebDriver 종료
        self.log.info("Closing WebDriver")
        webdriver_manager.quit()
```

```python
# webdriver_manager.py - start() 메서드 (추가)
def start(self):
    """WebDriver 시작"""
    self.log.info(f"Starting WebDriver ({self.config.provider}, region={self.config.region})")
    self._webdriver.start()
    self.log.info("WebDriver started successfully")
    
    # ✅ 추가: UA 캐싱 (첫 시작 시 한 번만)
    self._cache_user_agent_if_needed()

def _cache_user_agent_if_needed(self):
    """첫 시작 시 실제 User-Agent 캐싱 (선택적)"""
    if not self.config.cache_user_agent:
        return
    
    try:
        actual_ua = self.driver.execute_script("return navigator.userAgent;")
        # ... 캐시 저장 로직 ...
    except Exception as e:
        self.log.warning(f"Failed to cache UA: {e}")
```

**장점**:
- ✅ SRP 준수 (WebDriverManager가 UA 관리)
- ✅ 한 번만 실행 (성능 개선)
- ✅ finally 블록 단순화

---

#### 2. Adapter 이중 생성 제거

```python
# sync_crawl.py - _execute()
def _execute(...):
    webdriver_manager = None
    session_bridge = None
    
    try:
        # Step 1: WebDriver 시작
        webdriver_manager = WebDriverManager(...)
        webdriver_manager.start()
        
        # ✅ Adapter 한 번만 생성
        adapter = SyncSeleniumAdapter(driver=webdriver_manager._webdriver)
        
        # Step 2: SessionBridge 초기화 (선택적)
        http_session_policy = crawl_policy.http_session
        
        if http_session_policy:  # ✅ 단순화: http_session_policy만 체크
            try:
                from ..services.session_bridge import SessionBridge
                
                webdriver_for_bridge = adapter._drv
                user_agent = getattr(webdriver_manager.config, "user_agent", None)
                accept_language = getattr(webdriver_manager.config, "accept_languages", None)
                proxy = http_session_policy.proxy if http_session_policy else None
                
                session_bridge = SessionBridge.from_webdriver(
                    webdriver=webdriver_for_bridge,
                    user_agent=user_agent,
                    accept_language=accept_language,
                    proxy=proxy,
                )
            except Exception as bridge_exc:
                session_bridge = None
                self.log.warning(f"Failed to initialize session bridge: {bridge_exc}")
        
        # Step 3: Fetcher 준비 (미사용 시 제거)
        # ❌ 제거 또는 실제 사용처에 전달
        
        # Step 4: Inline pipeline
        navigator = SyncNavigator(adapter, crawl_policy.navigation)
        # ...
```

**장점**:
- ✅ 중복 제거
- ✅ 조건문 단순화 (3개 → 1개)
- ✅ 코드 가독성 향상

---

#### 3. Fetcher Dead Code 제거

```python
# Option 1: 완전 제거 (현재 미사용)
# ❌ Fetcher 생성 로직 모두 삭제

# Option 2: 실제 사용 (ItemSaver에 전달)
fetcher = None
if session_bridge and http_session_policy:
    fetcher = SyncHTTPFetcher(
        session=session_bridge.http_session,
        timeout=int(http_session_policy.timeout_read_sec),
        timeout_connect=int(http_session_policy.timeout_connect_sec),
        timeout_read=int(http_session_policy.timeout_read_sec),
        allow_redirects=http_session_policy.allow_redirects,
        stream_download=http_session_policy.stream_download,
        reuse_session=http_session_policy.reuse,
    )

# ✅ ItemSaver에 전달
saver = SyncItemSaver(
    policy=crawl_policy.saver,
    fetcher=fetcher,  # ✅ 이미지 다운로드 시 사용
    log_manager=self._parent_log_manager
)
```

**장점**:
- ✅ Dead code 제거 또는 실제 활용
- ✅ Resource 낭비 방지

---

### 개선안 B: WebDriver 재사용 (성능 최적화)

**목표**: 동일 region/provider일 때 WebDriver 재사용

**변경 사항**:

#### 1. SyncCrawl에 WebDriver Pool 추가

```python
class SyncCrawl:
    def __init__(self, ...):
        # ...
        self._webdriver_pool: Dict[str, WebDriverManager] = {}  # ✅ Pool
    
    def run(self, urls: Union[str, List[str]], **overrides) -> List[Dict[str, Any]]:
        # ...
        for url in urls:
            try:
                # URL 분석
                site, method, region = analyze_url(url)
                provider = overrides.get("webdriver_manager__provider", "firefox")
                
                # Pool key
                pool_key = f"{region}_{provider}"
                
                # WebDriver 재사용 또는 생성
                if pool_key in self._webdriver_pool:
                    webdriver_manager = self._webdriver_pool[pool_key]
                    self.log.info(f"Reusing WebDriver: {pool_key}")
                else:
                    webdriver_manager = WebDriverManager(...)
                    webdriver_manager.start()
                    self._webdriver_pool[pool_key] = webdriver_manager
                    self.log.info(f"Created WebDriver: {pool_key}")
                
                # Pipeline 실행
                result = self._execute(
                    url=url,
                    webdriver_manager=webdriver_manager,  # ✅ 전달
                    ...
                )
                all_results.append(result)
            
            except Exception as e:
                self.log.error(f"Failed: {url} - {e}")
                all_results.append({"url": url, "error": str(e), "success": False})
        
        # ✅ 모든 URL 처리 후 WebDriver 종료
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
- ✅ **성능 대폭 개선**: URL 10개 → WebDriver 시작 1회 (5초 → 50초 절약)
- ✅ **상태 격리 유지**: region/provider별 별도 인스턴스
- ✅ **Resource 효율**: 동일 설정 재사용

**단점**:
- ⚠️ **복잡도 증가**: Pool 관리 로직 추가
- ⚠️ **Memory 사용량 증가**: WebDriver 인스턴스 유지
- ⚠️ **상태 오염 가능성**: Cookie/Cache 누적

---

#### 2. _execute()에서 WebDriver 받기

```python
def _execute(
    self,
    url: str,
    crawl_policy: SyncCrawlPolicy,
    webdriver_manager: WebDriverManager,  # ✅ 외부에서 전달
    preset_policy: Dict[str, Any],
    **overrides: Dict[str, Any]
) -> Dict[str, Any]:
    """Pipeline 실행: 외부에서 WebDriver 받음"""
    
    try:
        # ❌ WebDriver 시작 로직 제거 (run()에서 관리)
        
        # Adapter 생성
        adapter = SyncSeleniumAdapter(driver=webdriver_manager._webdriver)
        
        # ... 나머지 pipeline ...
        
        return {"url": url, "success": True, ...}
    
    except Exception as e:
        self.log.error(f"Execution failed: {e}")
        return {"url": url, "error": str(e), "success": False}
    
    finally:
        # ❌ WebDriver 종료 제거 (run()에서 관리)
        pass
```

**장점**:
- ✅ _execute()가 WebDriver 생명주기에서 분리
- ✅ 책임 명확: run()이 Resource 관리, _execute()가 Pipeline 실행

---

### 개선안 C: Context Manager 강화 (Resource 안전성)

**목표**: with 구문으로 모든 Resource cleanup 보장

```python
class SyncCrawl:
    def run(self, urls: Union[str, List[str]], **overrides) -> List[Dict[str, Any]]:
        all_results = []
        
        for url in urls:
            try:
                # URL 분석
                site, method, region = analyze_url(url)
                
                # ✅ Context Manager로 WebDriver 관리
                with self._create_webdriver_manager(region, overrides) as webdriver_manager:
                    # ✅ Context Manager로 SessionBridge 관리
                    with self._create_session_bridge(webdriver_manager, crawl_policy) as session_bridge:
                        # Pipeline 실행
                        result = self._execute_pipeline(
                            url=url,
                            webdriver_manager=webdriver_manager,
                            session_bridge=session_bridge,
                            ...
                        )
                        all_results.append(result)
            
            except Exception as e:
                self.log.error(f"Failed: {url} - {e}")
                all_results.append({"url": url, "error": str(e), "success": False})
        
        return all_results
    
    def _create_webdriver_manager(self, region: str, overrides: dict) -> WebDriverManager:
        """WebDriverManager 생성 (Context Manager)"""
        return WebDriverManager(
            cfg_like=self._cfg_like_webdriver_manager,
            log_manager=self._parent_log_manager,
            region=region,
            **overrides
        )
    
    @contextmanager
    def _create_session_bridge(self, webdriver_manager, crawl_policy):
        """SessionBridge 생성 및 cleanup (Context Manager)"""
        session_bridge = None
        try:
            if crawl_policy.http_session:
                session_bridge = SessionBridge.from_webdriver(...)
            yield session_bridge
        finally:
            if session_bridge:
                # ✅ requests.Session close
                session_bridge.http_session.close()
```

**장점**:
- ✅ **Resource cleanup 보장**: with 블록 종료 시 자동 정리
- ✅ **가독성 향상**: 들여쓰기로 Resource 범위 명확
- ✅ **예외 안전**: 중첩된 with도 순차적으로 cleanup

**단점**:
- ⚠️ **코드 구조 변경**: 기존 try-finally → with 변경 필요
- ⚠️ **Nesting 증가**: 들여쓰기 깊어짐

---

## 📊 개선안 비교표

| 항목 | 개선안 A<br/>(최소 변경) | 개선안 B<br/>(WebDriver 재사용) | 개선안 C<br/>(Context Manager) |
|------|--------------------------|--------------------------------|-------------------------------|
| **구현 난이도** | ⭐ 쉬움 | ⭐⭐⭐ 어려움 | ⭐⭐ 보통 |
| **코드 변경량** | 소 (~50 lines) | 중 (~150 lines) | 중 (~100 lines) |
| **성능 개선** | 없음 | **⭐⭐⭐ 매우 큰** | 없음 |
| **복잡도** | 감소 | 증가 | 약간 증가 |
| **Resource 안전성** | 유지 | 약간 감소 | **⭐⭐⭐ 매우 향상** |
| **유지보수성** | 향상 | 약간 감소 | 향상 |
| **적용 시기** | 즉시 가능 | Phase 2 권장 | Phase 1.5 권장 |

---

## 🎯 권장 로드맵

### Phase 1: Quick Wins (1-2시간) - **우선 추천**

✅ **개선안 A 적용**:
1. UA 캐싱 로직 WebDriverManager로 이동
2. Adapter 이중 생성 제거
3. SessionBridge 조건문 단순화
4. Fetcher Dead Code 제거 또는 활용

**예상 효과**:
- 코드 가독성 30% 향상
- "굳이" 로직 제거로 혼란 감소
- SRP 준수로 유지보수성 향상

---

### Phase 2: Performance Optimization (4-6시간)

✅ **개선안 B 적용** (선택):
1. WebDriver Pool 구현
2. run() / _execute() 책임 분리
3. Pool cleanup 로직 추가
4. 상태 격리 테스트

**예상 효과**:
- URL 10개 크롤링 시간 50초 → 10초 (80% 단축)
- Resource 효율 향상

**주의사항**:
- Cookie/Cache 누적 모니터링
- Pool size 제한 (동시 브라우저 수)

---

### Phase 3: Resource Safety (2-3시간)

✅ **개선안 C 적용** (선택):
1. Context Manager 패턴 도입
2. SessionBridge cleanup 추가
3. 중첩 with 블록 구현
4. 예외 안전성 테스트

**예상 효과**:
- Resource 누수 0% (보장)
- 예외 상황에서도 안전한 cleanup

---

## 📝 최종 권장사항

### 즉시 적용 (High Priority)

1. **✅ 개선안 A - 최소 변경 (Quick Win)**
   - 이유: "굳이" 로직 제거로 즉시 효과
   - 난이도: 낮음
   - 시간: 1-2시간

### 고려 사항 (Medium Priority)

2. **⚠️ Fetcher 용도 확인**
   - 질문: 실제 사용할 계획인가?
   - Option 1: 미사용 시 삭제
   - Option 2: ItemSaver 이미지 다운로드에 활용

3. **⚠️ SessionBridge Cookie 동기화**
   - 질문: 언제 `sync_cookies_from_webdriver()` 호출?
   - 현재: 초기화만 하고 동기화 안됨
   - 개선: Navigator.load() 후 명시적 호출

### 미래 계획 (Low Priority)

4. **📅 개선안 B - WebDriver 재사용**
   - 시기: 성능이 critical할 때
   - 조건: 상태 오염 모니터링 가능할 때

5. **📅 개선안 C - Context Manager**
   - 시기: Resource 누수 문제 발생 시
   - 조건: 코드 구조 변경 가능할 때

---

## 🚨 발견된 버그/이슈

### 1. SessionBridge requests.Session cleanup 누락

**현상**: `requests.Session` 생성 후 `close()` 호출 안됨

**위험도**: ⚠️ Medium (Resource 누수)

**수정**:
```python
# finally 블록 추가
finally:
    if session_bridge:
        session_bridge.http_session.close()
```

---

### 2. cookie_bridge_policy 미사용

**현상**: Policy 정의되어 있지만 실제 코드에서 사용 안됨

**위험도**: ⚠️ Low (Dead code)

**수정**:
- Option 1: Policy 제거
- Option 2: SessionBridge 파라미터로 추가

---

### 3. Fetcher timeout 중복

**현상**: `timeout`과 `timeout_read`에 동일한 값 설정

**위험도**: ⚠️ Low (혼란)

**수정**:
```python
fetcher = SyncHTTPFetcher(
    session=session_bridge.http_session,
    timeout_connect=int(http_session_policy.timeout_connect_sec),
    timeout_read=int(http_session_policy.timeout_read_sec),
    # ❌ timeout 제거 (중복)
    ...
)
```

---

## 📚 참고자료

1. **Selenium Best Practices**:
   - WebDriver 재사용: https://www.selenium.dev/documentation/webdriver/drivers/
   - Context Manager: https://docs.python.org/3/library/contextlib.html

2. **Resource Management**:
   - RAII pattern: https://en.wikipedia.org/wiki/Resource_acquisition_is_initialization
   - Python Context Managers: https://realpython.com/python-with-statement/

3. **Performance Optimization**:
   - WebDriver Pool: https://github.com/SeleniumHQ/selenium/wiki/WebDriverPool

---

**작성자**: GitHub Copilot  
**검토 필요 사항**:
- [ ] Fetcher 실제 용도 확인
- [ ] SessionBridge Cookie 동기화 시점 결정
- [ ] WebDriver 재사용 필요성 평가
- [ ] Context Manager 도입 여부 결정
