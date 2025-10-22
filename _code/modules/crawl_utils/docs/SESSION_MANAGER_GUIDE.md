# Session Manager 사용 가이드

## 📋 개요

`SessionManager`는 브라우저 세션 설정(User-Agent, Accept-Language)을 통합 관리하는 유틸리티입니다.

### 🎯 **주요 기능**
- ✅ User-Agent와 Accept-Language를 한 파일에서 통합 관리
- ✅ 브라우저별, 지역별, 사이트별 프리셋 제공
- ✅ 동적 조합으로 유연한 세션 생성
- ✅ 싱글톤 패턴으로 메모리 효율적

---

## 📂 파일 구조

```
_code/
├── data/
│   └── sessions/
│       ├── browser_sessions.json  # 통합 설정 파일 (새로 생성)
│       ├── AL_US.json              # (구버전 - 삭제 가능)
│       ├── AL_CN.json              # (구버전 - 삭제 가능)
│       └── UA_firefox.json         # (구버전 - 삭제 가능)
└── modules/
    └── crawl_utils/
        └── session_manager.py      # SessionManager 클래스
```

---

## 🚀 사용 방법

### **1. 기본 Import**

```python
from crawl_utils.session_manager import SessionManager, get_session_for_site, get_session_by_preset
```

---

### **2. 사이트별 기본 설정 사용 (가장 간단)**

```python
# Taobao 크롤링
session = get_session_for_site("taobao")

headers = session.get_headers()
# {
#   "User-Agent": "Mozilla/5.0 ... Firefox/144.0",
#   "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7"
# }

print(f"Browser: {session.browser}")  # firefox
print(f"Region: {session.region}")    # china
print(f"Profile: {session.profile_path}")  # M:/Firefox_Profile/Taobao_Tmall_1688
```

**지원 사이트:**
- `taobao`, `tmall`, `1688` → 중국어 우선
- `aliexpress`, `alibaba` → 영어 우선 (글로벌)
- `jd`, `vvic` → 중국어 우선

---

### **3. 프리셋 사용**

```python
# 중국 사이트 크롤링용
session = get_session_by_preset("firefox_china")

# 글로벌 사이트 크롤링용
session = get_session_by_preset("firefox_global")

# 미국 사이트 크롤링용
session = get_session_by_preset("firefox_us")

# 유럽 사이트 크롤링용
session = get_session_by_preset("firefox_eu")
```

**지원 프리셋:**
- `firefox_china` → Firefox + 중국어
- `firefox_global` → Firefox + 영어+중국어
- `firefox_us` → Firefox + 미국 영어
- `firefox_eu` → Firefox + 유럽 다국어
- `chrome_global` → Chrome + 영어+중국어

---

### **4. 수동 조합 (고급)**

```python
from crawl_utils.session_manager import get_session

# Firefox + 중국어
session = get_session(browser="firefox", region="china")

# Chrome + 미국 영어
session = get_session(browser="chrome", region="us")

# Edge + 유럽 다국어
session = get_session(browser="edge", region="eu")
```

---

### **5. Selenium에서 사용**

```python
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from crawl_utils.session_manager import get_session_for_site

# 세션 설정 로드
session = get_session_for_site("taobao")

# Firefox Options 설정
options = Options()
options.set_preference("general.useragent.override", session.user_agent)
options.set_preference("intl.accept_languages", session.accept_language)

# 프로필 경로 설정 (선택사항)
if session.profile_path:
    options.add_argument(f"-profile {session.profile_path}")

# WebDriver 시작
driver = webdriver.Firefox(options=options)
driver.get("https://www.taobao.com")
```

---

### **6. requests에서 사용**

```python
import requests
from crawl_utils.session_manager import get_session_for_site

session_config = get_session_for_site("aliexpress")

response = requests.get(
    "https://www.aliexpress.com",
    headers=session_config.get_headers()
)
```

---

## 📖 API 레퍼런스

### **SessionConfig 클래스**

세션 설정을 담는 데이터 클래스입니다.

#### **속성**
- `user_agent: str` - User-Agent 문자열
- `accept_language: str` - Accept-Language 문자열
- `browser: str` - 브라우저 종류 ('firefox', 'chrome', 'edge')
- `region: str` - 지역 ('us', 'eu', 'latam', 'china', 'global')
- `profile_path: Optional[str]` - Firefox 프로필 경로
- `metadata: Dict[str, Any]` - 추가 메타데이터

#### **메서드**
- `get_headers() -> Dict[str, str]` - HTTP 헤더 딕셔너리 반환
- `to_dict() -> Dict[str, Any]` - 전체 설정을 딕셔너리로 반환

---

### **SessionManager 클래스**

#### **주요 메서드**

##### **get_session_for_site(site: str) -> SessionConfig**
사이트별 기본 세션 설정 반환

```python
session = SessionManager.get_session_for_site("taobao")
```

---

##### **get_session_by_preset(preset_name: str) -> SessionConfig**
프리셋 이름으로 세션 설정 반환

```python
session = SessionManager.get_session_by_preset("firefox_china")
```

---

##### **get_session(browser: str, region: str) -> SessionConfig**
브라우저와 지역을 조합하여 세션 설정 생성

```python
session = SessionManager.get_session(browser="firefox", region="china")
```

---

##### **list_browsers() -> list**
사용 가능한 브라우저 목록

```python
browsers = SessionManager.list_browsers()
# ['firefox', 'chrome', 'edge']
```

---

##### **list_regions() -> list**
사용 가능한 지역 목록

```python
regions = SessionManager.list_regions()
# ['us', 'eu', 'latam', 'china', 'global']
```

---

##### **list_sites() -> list**
사용 가능한 사이트 목록

```python
sites = SessionManager.list_sites()
# ['taobao', 'tmall', '1688', 'aliexpress', 'alibaba', 'jd', 'vvic']
```

---

##### **list_presets() -> list**
사용 가능한 프리셋 목록

```python
presets = SessionManager.list_presets()
# ['firefox_china', 'firefox_global', 'firefox_us', 'firefox_eu', 'chrome_global']
```

---

## 🎯 실전 사용 예시

### **예시 1: Taobao 크롤링**

```python
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from crawl_utils.session_manager import get_session_for_site

# 1. Taobao 세션 설정 로드
session = get_session_for_site("taobao")

# 2. Firefox 옵션 구성
options = Options()
options.set_preference("general.useragent.override", session.user_agent)
options.set_preference("intl.accept_languages", session.accept_language)
options.add_argument(f"-profile {session.profile_path}")

# 3. 크롤링 시작
driver = webdriver.Firefox(options=options)
driver.get("https://s.taobao.com/search?q=nike")

# 크롤링 로직...
```

---

### **예시 2: 여러 지역에서 AliExpress 가격 비교**

```python
from crawl_utils.session_manager import get_session

regions = ["us", "eu", "latam"]
product_url = "https://www.aliexpress.com/item/1234567890.html"

for region in regions:
    # 지역별 세션 생성
    session = get_session(browser="firefox", region=region)
    
    # 각 지역 가격 수집
    driver = setup_driver(session)  # 가상 함수
    driver.get(product_url)
    
    price = extract_price(driver)  # 가상 함수
    print(f"Region: {region}, Price: {price}")
```

---

### **예시 3: 사이트 자동 전환**

```python
from crawl_utils.session_manager import get_session_for_site, SessionManager

# 크롤링할 사이트 목록
sites = SessionManager.list_sites()

for site in sites:
    session = get_session_for_site(site)
    
    print(f"\n크롤링 시작: {site}")
    print(f"  Browser: {session.browser}")
    print(f"  Region: {session.region}")
    print(f"  AL: {session.accept_language}")
    
    # 각 사이트 크롤링...
```

---

## 🔧 설정 파일 구조 (`browser_sessions.json`)

### **User-Agents 섹션**

```json
{
  "user_agents": {
    "firefox": {
      "value": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0",
      "browser": "firefox",
      "version": "144.0",
      "platform": "Windows NT 10.0; Win64; x64"
    }
  }
}
```

---

### **Accept-Languages 섹션**

```json
{
  "accept_languages": {
    "china": {
      "value": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
      "region": "China",
      "primary_lang": "zh-CN",
      "currencies": ["CNY"]
    }
  }
}
```

---

### **Site Profiles 섹션**

```json
{
  "site_profiles": {
    "taobao": {
      "default_browser": "firefox",
      "default_region": "china",
      "description": "Taobao - China domestic e-commerce",
      "profile_path": "M:/Firefox_Profile/Taobao_Tmall_1688"
    }
  }
}
```

---

### **Presets 섹션**

```json
{
  "presets": {
    "firefox_china": {
      "user_agent": "firefox",
      "accept_language": "china",
      "use_case": "Chinese domestic sites (Taobao, Tmall, 1688, JD, VVIC)"
    }
  }
}
```

---

## ✅ 마이그레이션 가이드

### **기존 코드 (개별 파일)**

```python
# 기존 방식
import json

with open("data/sessions/UA_firefox.json") as f:
    ua_data = json.load(f)

with open("data/sessions/AL_CN.json") as f:
    al_data = json.load(f)

user_agent = ua_data["headers"]["User-Agent"]
accept_language = al_data["headers"]["Accept-Language"]
```

---

### **새 코드 (SessionManager)**

```python
# 새 방식
from crawl_utils.session_manager import get_session

session = get_session(browser="firefox", region="china")
user_agent = session.user_agent
accept_language = session.accept_language

# 또는 한 번에
headers = session.get_headers()
```

---

## 🎉 장점 요약

1. ✅ **통합 관리** - UA와 AL을 한 파일에서 관리
2. ✅ **유연성** - 브라우저와 지역을 자유롭게 조합
3. ✅ **간편성** - 사이트별 프리셋으로 즉시 사용
4. ✅ **확장성** - 새 브라우저/지역 추가 용이
5. ✅ **유지보수** - 설정 변경 시 한 곳만 수정
6. ✅ **타입 안전** - 데이터 클래스로 타입 체크

---

## 📝 테스트 실행

```bash
cd M:\CALife\CAShop - 구매대행\_code\modules\crawl_utils
python session_manager.py
```

**출력 예시:**
```
================================================================================
Session Manager Examples
================================================================================

1. 사이트별 기본 설정:

TAOBAO:
  Browser: firefox
  Region: china
  User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv...
  Accept-Language: zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7

...
```
