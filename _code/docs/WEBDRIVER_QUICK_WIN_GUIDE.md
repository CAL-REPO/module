# 개선안 A - Quick Win 구현 가이드

**적용 난이도**: ⭐ 쉬움  
**예상 시간**: 1-2시간  
**코드 변경량**: 약 50 lines

---

## 변경사항 요약

1. ✅ Adapter 이중 생성 제거
2. ✅ SessionBridge 조건문 단순화
3. ✅ SessionBridge cleanup 추가
4. ✅ Fetcher Dead Code 처리 결정 필요
5. ✅ UA 캐싱 로직 이동 (선택적)

---

## 1. Adapter 이중 생성 제거

### 현재 코드 (문제)

```python
# sync_crawl.py - _execute() 메서드

def _execute(...):
    try:
        # Step 1: WebDriver 시작
        webdriver_manager = WebDriverManager(...)
        webdriver_manager.start()
        
        # Step 2: SessionBridge 초기화
        adapter = SyncSeleniumAdapter(driver=webdriver_manager._webdriver)  # ← 첫 번째
        session_bridge_policy = crawl_policy.session_bridge
        # ... SessionBridge 생성 ...
        
        # Step 4: Inline pipeline
        adapter = SyncSeleniumAdapter(driver=webdriver_manager._webdriver)  # ← 두 번째 (중복!)
        navigator = SyncNavigator(adapter, crawl_policy.navigation)
```

### 개선 코드

```python
def _execute(...):
    try:
        # Step 1: WebDriver 시작
        webdriver_manager = WebDriverManager(...)
        webdriver_manager.start()
        
        # ✅ Adapter 한 번만 생성
        adapter = SyncSeleniumAdapter(driver=webdriver_manager._webdriver)
        
        # Step 2: SessionBridge 초기화
        http_session_policy = crawl_policy.http_session
        
        if http_session_policy:
            try:
                from ..services.session_bridge import SessionBridge
                
                webdriver_for_bridge = adapter._drv  # ✅ 생성된 adapter 재사용
                user_agent = getattr(webdriver_manager.config, "user_agent", None)
                accept_language = getattr(webdriver_manager.config, "accept_languages", None)
                proxy = http_session_policy.proxy if hasattr(http_session_policy, 'proxy') else None
                
                session_bridge = SessionBridge.from_webdriver(
                    webdriver=webdriver_for_bridge,
                    user_agent=user_agent,
                    accept_language=accept_language,
                    proxy=proxy,
                )
            except Exception as bridge_exc:
                session_bridge = None
                self.log.warning(f"Failed to initialize session bridge: {bridge_exc}")
        
        # Step 4: Inline pipeline
        navigator = SyncNavigator(adapter, crawl_policy.navigation)  # ✅ 동일 adapter 재사용
        # ...
```

---

## 2. SessionBridge 조건문 단순화

### 현재 코드 (복잡)

```python
session_bridge_policy = crawl_policy.session_bridge
http_session_policy = crawl_policy.http_session
cookie_bridge_policy = crawl_policy.cookie_bridge

if session_bridge_policy or http_session_policy or cookie_bridge_policy:
    # SessionBridge 초기화
    ...
```

**문제점**:
- 3개 policy 확인하지만 `cookie_bridge_policy`는 실제 사용 안됨
- `session_bridge_policy`는 user_agent/proxy만 추출용

### 개선 코드 (단순)

```python
http_session_policy = crawl_policy.http_session

if http_session_policy:  # ✅ 실제 사용되는 policy만 체크
    try:
        from ..services.session_bridge import SessionBridge
        
        # user_agent/proxy는 WebDriverManager 설정 또는 http_session_policy에서 추출
        user_agent = getattr(webdriver_manager.config, "user_agent", None)
        accept_language = getattr(webdriver_manager.config, "accept_languages", None)
        proxy = getattr(http_session_policy, 'proxy', None)
        
        session_bridge = SessionBridge.from_webdriver(
            webdriver=adapter._drv,
            user_agent=user_agent,
            accept_language=accept_language,
            proxy=proxy,
        )
    except Exception as bridge_exc:
        session_bridge = None
        self.log.warning(f"Failed to initialize session bridge: {bridge_exc}")
```

---

## 3. SessionBridge cleanup 추가

### 현재 코드 (문제)

```python
def _execute(...):
    webdriver_manager = None
    session_bridge = None
    
    try:
        # ... pipeline 실행 ...
        return {"url": url, "success": True, ...}
    
    except Exception as e:
        return {"url": url, "error": str(e), "success": False}
    
    finally:
        if webdriver_manager:
            # WebDriver 종료
            webdriver_manager.quit()
        
        # ⚠️ session_bridge cleanup 누락!
```

### 개선 코드

```python
def _execute(...):
    webdriver_manager = None
    session_bridge = None
    
    try:
        # ... pipeline 실행 ...
        return {"url": url, "success": True, ...}
    
    except Exception as e:
        return {"url": url, "error": str(e), "success": False}
    
    finally:
        # ✅ SessionBridge cleanup 추가 (WebDriver보다 먼저)
        if session_bridge and hasattr(session_bridge, 'http_session'):
            try:
                session_bridge.http_session.close()
                self.log.debug("SessionBridge HTTP session closed")
            except Exception as cleanup_exc:
                self.log.warning(f"Failed to close session bridge: {cleanup_exc}")
        
        # WebDriver 종료
        if webdriver_manager:
            self.log.info("Closing WebDriver")
            webdriver_manager.quit()
```

**이유**:
- `requests.Session`은 연결 풀을 유지하므로 명시적 `close()` 필요
- WebDriver보다 먼저 종료 (의존성 순서)

---

## 4. Fetcher 처리 결정

### Option 1: Dead Code 제거 (미사용 시)

```python
# ❌ Step 3: Fetcher 준비 - 전체 제거
# fetcher = None
# if session_bridge and http_session_policy:
#     try:
#         from ..services.fetcher import SyncHTTPFetcher
#         fetcher = SyncHTTPFetcher(...)
#     except Exception as fetcher_exc:
#         self.log.warning(f"Failed to create fetcher: {fetcher_exc}")
```

**조건**: 현재 ItemSaver가 Fetcher를 사용하지 않는 경우

---

### Option 2: ItemSaver에 전달 (활용 시)

```python
# Step 3: Fetcher 준비
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

# ... (pipeline) ...

# Phase 5: ItemSaver
saver = SyncItemSaver(
    policy=crawl_policy.saver,
    fetcher=fetcher,  # ✅ 전달
    log_manager=self._parent_log_manager
)
```

**조건**: ItemSaver가 이미지 다운로드 시 HTTP 세션 사용하는 경우

**확인 필요**: `SyncItemSaver.__init__()` 시그니처에 `fetcher` 파라미터 있는지?

---

## 5. UA 캐싱 로직 이동 (선택적)

### 현재 코드 (finally 블록)

```python
finally:
    if webdriver_manager:
        # ✅ 크롤링 성공 시 실제 UA 추출 및 캐시 저장
        try:
            if webdriver_manager._webdriver:
                actual_ua = webdriver_manager.driver.execute_script("return navigator.userAgent;")
                
                if actual_ua:
                    # ... 캐시 파일 저장 로직 (20+ lines) ...
        except Exception:
            pass
        
        # WebDriver 종료
        webdriver_manager.quit()
```

### 개선 코드 - finally 블록 단순화

```python
finally:
    # ✅ SessionBridge cleanup
    if session_bridge and hasattr(session_bridge, 'http_session'):
        try:
            session_bridge.http_session.close()
        except Exception as cleanup_exc:
            self.log.warning(f"Failed to close session bridge: {cleanup_exc}")
    
    # WebDriver 종료
    if webdriver_manager:
        self.log.info("Closing WebDriver")
        webdriver_manager.quit()
```

### WebDriverManager에 기능 이동

```python
# webdriver_manager.py

class WebDriverManager:
    def __init__(self, cfg_like, *, log_manager=None, **overrides):
        self.config = self._load_config(cfg_like, **overrides)
        # ...
        self._ua_cached = False  # ✅ 캐싱 상태 추적
    
    def start(self):
        """WebDriver 시작"""
        self.log.info(f"Starting WebDriver ({self.config.provider}, region={self.config.region})")
        self._webdriver.start()
        self.log.info("WebDriver started successfully")
        
        # ✅ UA 캐싱 (첫 시작 시 한 번만)
        if self.config.cache_user_agent and not self._ua_cached:
            self._cache_user_agent()
    
    def _cache_user_agent(self):
        """실제 User-Agent 추출 및 캐싱"""
        try:
            actual_ua = self.driver.execute_script("return navigator.userAgent;")
            
            if actual_ua and self.config.provider == "firefox":
                from pathlib import Path
                import json
                from datetime import datetime, timezone
                import re
                
                cache_path = Path(__file__).parent.parent / "configs" / "browser_version.json"
                
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
                
                self._ua_cached = True
                self.log.debug(f"✅ Cached User-Agent: Firefox/{version}")
        
        except Exception as e:
            self.log.warning(f"Failed to cache User-Agent: {e}")
```

### Policy에 필드 추가

```python
# provider/policy.py

class WebDriverManagerPolicy(BaseModel):
    # ... 기존 필드 ...
    
    cache_user_agent: bool = Field(
        default=False,
        description="첫 시작 시 실제 User-Agent 캐싱 여부"
    )
```

---

## 적용 체크리스트

### Phase 1: 코드 수정

- [ ] **1. Adapter 이중 생성 제거**
  - [ ] `sync_crawl.py` Line ~565: 첫 번째 adapter 생성
  - [ ] `sync_crawl.py` Line ~625: 두 번째 adapter 제거
  - [ ] SessionBridge에서 `adapter._drv` 사용

- [ ] **2. SessionBridge 조건문 단순화**
  - [ ] `session_bridge_policy`, `cookie_bridge_policy` 제거
  - [ ] `if http_session_policy:` 조건으로 단순화
  - [ ] user_agent/proxy는 WebDriverManager.config에서 추출

- [ ] **3. SessionBridge cleanup 추가**
  - [ ] `finally` 블록에 `session_bridge.http_session.close()` 추가
  - [ ] WebDriver 종료 전에 실행
  - [ ] 예외 처리 추가

- [ ] **4. Fetcher 처리 결정**
  - [ ] `SyncItemSaver` 시그니처 확인
  - [ ] Option 1: 미사용 시 제거
  - [ ] Option 2: 사용 시 전달

- [ ] **5. UA 캐싱 로직 이동** (선택)
  - [ ] `finally` 블록에서 제거
  - [ ] `WebDriverManager._cache_user_agent()` 메서드 추가
  - [ ] `WebDriverManager.start()`에서 호출
  - [ ] `WebDriverManagerPolicy.cache_user_agent` 필드 추가

---

### Phase 2: 테스트

- [ ] **Unit Test**
  - [ ] Adapter 생성 횟수 확인
  - [ ] SessionBridge cleanup 호출 확인
  - [ ] UA 캐싱 한 번만 실행 확인

- [ ] **Integration Test**
  - [ ] 실제 URL 크롤링 (test_crawl.py)
  - [ ] requests.Session 누수 확인
  - [ ] WebDriver 정상 종료 확인

- [ ] **Manual Test**
  - [ ] 여러 URL 연속 크롤링
  - [ ] 예외 발생 시 cleanup 확인
  - [ ] 로그 메시지 확인

---

### Phase 3: 검증

- [ ] **코드 품질**
  - [ ] Lint errors 확인
  - [ ] Type hints 검증
  - [ ] 중복 코드 제거 확인

- [ ] **성능**
  - [ ] 메모리 사용량 확인 (before/after)
  - [ ] Resource 누수 모니터링

- [ ] **문서**
  - [ ] Docstring 업데이트
  - [ ] CHANGELOG 작성
  - [ ] README 수정 (필요 시)

---

## 예상 효과

### 긍정적 효과

1. **코드 가독성 30% 향상**
   - 중복 제거
   - 조건문 단순화

2. **Resource 안전성 향상**
   - SessionBridge cleanup 보장
   - 명시적 종료 로직

3. **SRP 준수**
   - UA 캐싱 → WebDriverManager 책임
   - finally 블록 단순화

4. **유지보수성 향상**
   - "굳이" 로직 제거
   - 의도 명확화

### 부작용 없음

- ✅ 기존 기능 유지
- ✅ 성능 영향 없음
- ✅ Breaking changes 없음

---

## 구현 순서 (권장)

1. **1단계**: Adapter 이중 생성 제거 (10분)
   - 가장 간단
   - 즉시 효과

2. **2단계**: SessionBridge 조건문 단순화 (10분)
   - Adapter 수정과 연계
   - 테스트 용이

3. **3단계**: SessionBridge cleanup 추가 (20분)
   - finally 블록 수정
   - 테스트 필수

4. **4단계**: Fetcher 처리 결정 (30분)
   - ItemSaver 확인 필요
   - 선택적 작업

5. **5단계**: UA 캐싱 이동 (30-60분)
   - 선택적 작업
   - WebDriverManager 수정 필요

---

**추정 시간**: 1-2시간 (테스트 포함)
