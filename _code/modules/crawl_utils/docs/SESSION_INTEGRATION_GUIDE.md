# SessionManager와 YAML Config 통합 가이드

## 🎯 **문제 상황**

현재 Firefox YAML 설정 파일에 UA/AL이 하드코딩되어 있습니다:

```yaml
firefox:
  user_agent: "Mozilla/5.0 ... Firefox/120.0"
  accept_languages: "zh-CN,zh;q=0.9,ko;q=0.8,en;q=0.7"
  session_path: "{{data_dir}}/sessions/firefox_HK.json"
```

**문제점:**
- ❌ 각 YAML 파일마다 중복 설정
- ❌ UA/AL 변경 시 여러 파일 수정 필요
- ❌ browser_sessions.json과 분리 관리

---

## ✅ **해결 방안**

### **옵션 1: SessionManager 참조 (권장)**

YAML에서 SessionManager 프리셋 참조 → 동적 로드

### **옵션 2: 기존 방식 유지**

YAML에 직접 명시 → SessionManager는 별도 용도

---

## 📋 **옵션 1: SessionManager 참조 방식**

### **1-1. YAML 구조 개선**

#### **새로운 firefox_taobao.yaml**

```yaml
# -*- coding: utf-8 -*-
# Taobao 크롤링용 Firefox 설정

firefox:
  site: "taobao"
  provider: "firefox"
  headless: false
  window_size: [1440, 900]
  
  # -------------------------------------------------------------------------
  # Session 관리 - SessionManager 통합
  # -------------------------------------------------------------------------
  session_manager:
    enabled: true
    # 방법 1: 프리셋 사용 (간단)
    preset: "firefox_china"
    
    # 방법 2: 사이트 이름 사용 (자동 매핑)
    # site: "taobao"
    
    # 방법 3: 수동 조합
    # browser: "firefox"
    # region: "china"
  
  # 레거시 지원 (session_manager 없으면 이것 사용)
  # user_agent: "Mozilla/5.0 ..."
  # accept_languages: "zh-CN,zh;q=0.9,..."
  
  session_path: "{{data_dir}}/sessions/firefox_taobao_tmall_1688.json"
  save_session: true
  
  # -------------------------------------------------------------------------
  # 자동화 탐지 회피
  # -------------------------------------------------------------------------
  disable_automation: true
  dom_enabled: false
  resist_fingerprint_enabled: false
  
  # -------------------------------------------------------------------------
  # Firefox 경로 설정
  # -------------------------------------------------------------------------
  driver_path: "M:/WebDriver/geckodriver_win32.exe"
  binary_path: "C:/Program Files/Mozilla Firefox/firefox.exe"
  profile_path: "M:/Firefox_Profile/Taobao_Tmall_1688"
  
  # -------------------------------------------------------------------------
  # 추가 옵션
  # -------------------------------------------------------------------------
  use_webdriver_manager: true
  enable_cookies: true
  enable_cache: true
  load_images: true
  enable_javascript: true
```

---

#### **새로운 firefox_aliexpress.yaml**

```yaml
firefox:
  site: "aliexpress"
  provider: "firefox"
  headless: false
  window_size: [1440, 900]
  
  # SessionManager 프리셋 사용
  session_manager:
    enabled: true
    preset: "firefox_global"  # 영어+중국어
  
  session_path: "{{data_dir}}/sessions/firefox_aliexpress.json"
  save_session: true
  
  # ... 나머지 동일
```

---

### **1-2. Policy 클래스 확장**

#### **SessionManagerConfig 추가**

```python
# policy.py에 추가

class SessionManagerConfig(BaseModel):
    """SessionManager 통합 설정"""
    enabled: bool = Field(False, description="Enable SessionManager integration")
    
    # 방법 1: 프리셋
    preset: Optional[str] = Field(None, description="SessionManager preset name (firefox_china, firefox_global, etc.)")
    
    # 방법 2: 사이트
    site: Optional[str] = Field(None, description="Site name for auto session (taobao, aliexpress, etc.)")
    
    # 방법 3: 수동 조합
    browser: Optional[str] = Field(None, description="Browser type (firefox, chrome, edge)")
    region: Optional[str] = Field(None, description="Region (us, eu, latam, china, global)")
    
    @model_validator(mode="after")
    def validate_config(self):
        """설정 유효성 검증"""
        if not self.enabled:
            return self
        
        # 셋 중 하나는 반드시 있어야 함
        if not any([self.preset, self.site, (self.browser and self.region)]):
            raise ValueError(
                "SessionManager enabled but no configuration provided. "
                "Use one of: preset, site, or (browser+region)"
            )
        
        return self
```

---

#### **WebDriverPolicy 수정**

```python
class WebDriverPolicy(BaseModel):
    """모든 WebDriver 공통 정책"""
    name: str = Field("webdriver", description="Config section name")
    site: str = Field(default="", description="Site identifier")
    provider: ProviderType = Field("firefox", description="WebDriver provider type")
    
    # 기본 설정
    headless: bool = Field(False, description="Run browser in headless mode")
    window_size: Optional[Tuple[int, int]] = Field((1440, 900), description="Browser window size")
    
    # SessionManager 통합 (새로 추가)
    session_manager: Optional[SessionManagerConfig] = Field(None, description="SessionManager integration config")
    
    # Session 관리
    session_path: Optional[Path] = Field(None, description="Path to save/load session data")
    save_session: bool = Field(False, description="Enable session save/restore")
    
    # 레거시 필드 (session_manager 우선, 없으면 이것 사용)
    user_agent: Optional[str] = Field(None, description="Custom User-Agent (fallback)")
    accept_languages: Optional[str] = Field("en-US,en;q=0.9", description="Accept-Language (fallback)")
    
    # ... 나머지 필드 동일
    
    @model_validator(mode="after")
    def load_session_config(self):
        """SessionManager에서 UA/AL 로드"""
        # SessionManager 활성화 시
        if self.session_manager and self.session_manager.enabled:
            try:
                from crawl_utils.session_manager import (
                    get_session_for_site,
                    get_session_by_preset,
                    get_session
                )
                
                # 프리셋 사용
                if self.session_manager.preset:
                    session = get_session_by_preset(self.session_manager.preset)
                
                # 사이트 사용
                elif self.session_manager.site:
                    session = get_session_for_site(self.session_manager.site)
                
                # 수동 조합
                elif self.session_manager.browser and self.session_manager.region:
                    session = get_session(
                        browser=self.session_manager.browser,
                        region=self.session_manager.region
                    )
                
                # UA/AL 덮어쓰기 (레거시 필드가 없는 경우만)
                if not self.user_agent:
                    self.user_agent = session.user_agent
                if not self.accept_languages:
                    self.accept_languages = session.accept_language
                
            except Exception as e:
                # SessionManager 로드 실패 시 레거시 필드 사용
                print(f"Warning: SessionManager load failed: {e}")
                pass
        
        return self
```

---

### **1-3. 사용 예시**

```python
from cfg_utils import ConfigLoader
from crawl_utils.provider import FirefoxProvider

# Config 로드
config = ConfigLoader(config_loader_cfg_path="config_loader_xloto.yaml")
firefox_config = config.to_dict(section="firefox")

# Provider 생성 (자동으로 SessionManager에서 UA/AL 로드)
provider = FirefoxProvider(firefox_config)

# UA/AL 확인
print(provider.config.user_agent)        # SessionManager에서 로드된 값
print(provider.config.accept_languages)  # SessionManager에서 로드된 값
```

---

## 📋 **옵션 2: 기존 방식 유지 (간단)**

### **2-1. YAML은 그대로 유지**

```yaml
firefox:
  site: "taobao"
  user_agent: "Mozilla/5.0 ... Firefox/144.0"
  accept_languages: "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7"
  session_path: "{{data_dir}}/sessions/firefox_taobao.json"
```

---

### **2-2. SessionManager는 별도 용도**

```python
# 크롤링 스크립트에서 필요 시 직접 사용
from crawl_utils.session_manager import get_session_for_site

# requests 라이브러리로 다운로드 시
session = get_session_for_site("taobao")
response = requests.get(url, headers=session.get_headers())
```

---

### **2-3. 장단점**

**장점:**
- ✅ 기존 코드 수정 불필요
- ✅ YAML 명시적 (무엇을 사용하는지 명확)
- ✅ SessionManager는 독립적 용도

**단점:**
- ❌ 중복 관리 (browser_sessions.json + YAML)
- ❌ 변경 시 여러 파일 수정
- ❌ 일관성 유지 어려움

---

## 🎯 **권장 방안: 옵션 1 (SessionManager 참조)**

### **마이그레이션 단계**

#### **Step 1: Policy 클래스 확장**

`policy.py`에 `SessionManagerConfig` 추가 및 `WebDriverPolicy` 수정

---

#### **Step 2: YAML 파일 업데이트**

```yaml
# firefox_taobao.yaml
firefox:
  session_manager:
    enabled: true
    preset: "firefox_china"  # 또는 site: "taobao"
  
  # 레거시 필드 제거 (선택사항)
  # user_agent: "..."
  # accept_languages: "..."
```

---

#### **Step 3: 테스트**

```python
# 기존 코드 그대로 동작
from cfg_utils import ConfigLoader

config = ConfigLoader(config_loader_cfg_path="...")
firefox_config = config.to_dict(section="firefox")

# UA/AL이 자동으로 SessionManager에서 로드됨
print(firefox_config["user_agent"])
print(firefox_config["accept_languages"])
```

---

#### **Step 4: 점진적 마이그레이션**

1. ✅ `firefox_taobao.yaml` 먼저 변경
2. ✅ 테스트 후 `firefox_aliexpress.yaml` 변경
3. ✅ 나머지 파일 순차적 변경

---

## 📊 **비교 요약**

| 항목 | 옵션 1 (SessionManager 참조) | 옵션 2 (기존 유지) |
|------|----------------------------|-------------------|
| **관리 일원화** | ✅ browser_sessions.json 하나로 | ❌ YAML 각각 관리 |
| **변경 용이성** | ✅ 한 곳만 수정 | ❌ 여러 파일 수정 |
| **코드 수정** | ⚠️ Policy 클래스 수정 필요 | ✅ 수정 불필요 |
| **명시성** | ⚠️ YAML만 보면 UA/AL 알기 어려움 | ✅ YAML에 명시 |
| **유연성** | ✅ 프리셋/사이트/조합 선택 | ❌ 고정값 |
| **유지보수** | ✅ 간편 | ❌ 번거로움 |

---

## 💡 **최종 권장**

### **단계적 접근 (Hybrid)**

```yaml
firefox:
  site: "taobao"
  
  # SessionManager 통합 (우선 사용)
  session_manager:
    enabled: true
    preset: "firefox_china"
  
  # 레거시 fallback (SessionManager 실패 시 사용)
  user_agent: "Mozilla/5.0 ... Firefox/144.0"
  accept_languages: "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7"
```

**동작 순서:**
1. `session_manager.enabled=true` → SessionManager에서 로드
2. SessionManager 실패 → 레거시 필드 사용
3. 둘 다 없음 → Policy 기본값 사용

**장점:**
- ✅ 하위 호환성 유지
- ✅ 점진적 마이그레이션 가능
- ✅ 안정적 fallback

---

## 🔥 **즉시 적용 가능한 코드**

### **Policy 클래스 추가 (policy.py)**

```python
# SessionManagerConfig 추가
class SessionManagerConfig(BaseModel):
    enabled: bool = Field(False)
    preset: Optional[str] = None
    site: Optional[str] = None
    browser: Optional[str] = None
    region: Optional[str] = None

# WebDriverPolicy에 추가
class WebDriverPolicy(BaseModel):
    # 기존 필드...
    
    session_manager: Optional[SessionManagerConfig] = None
    
    @model_validator(mode="after")
    def load_session_config(self):
        if self.session_manager and self.session_manager.enabled:
            # SessionManager에서 로드
            pass
        return self
```

---

### **YAML 예시 (firefox_taobao.yaml)**

```yaml
firefox:
  session_manager:
    enabled: true
    preset: "firefox_china"
  
  # Fallback
  user_agent: "Mozilla/5.0 ... Firefox/144.0"
  accept_languages: "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7"
```

**이 방식이 가장 안전하고 유연합니다!** 🎯
