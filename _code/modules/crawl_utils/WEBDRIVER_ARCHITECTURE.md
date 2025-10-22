# 🎯 WebDriver 설정 최종 구조

## ✅ **핵심 원칙**

### **1. Firefox Profile = 모든 세션 관리**
- **쿠키**: `cookies.sqlite` (Firefox 자동 관리)
- **localStorage**: `webappsstore.sqlite` (Firefox 자동 관리)
- **세션**: `sessionstore.jsonlz4` (Firefox 자동 관리)
- **설정**: `prefs.js` (Firefox 자동 관리)

**→ SessionManager 불필요!**

### **2. YAML = 지역별 고정 설정**
- **Accept-Language**: 지역별 고정값 (거의 변경 없음)
- **Profile Path**: 지역별 고정 경로
- **정책**: headless, window_size, disable_automation

**→ 지역별로 YAML 분리하므로 중복 없음!**

### **3. JSON = 자주 변경되는 동적 값**
- **User-Agent**: 브라우저 업데이트마다 변경
- **Browser Versions**: Firefox/Chrome/Edge 버전

**→ browser_versions.json으로 분리!**

---

## 📁 **파일 구조**

```
crawl_utils/
├── site_region_mapping.py     # UA/AL/경로 중앙 관리
├── browser_version_manager.py # UA 자동 감지 (선택적 도구)
├── policy.py                  # WebDriverPolicy 클래스
├── providers/
│   ├── firefox_provider.py    # Firefox WebDriver 생성
│   └── chrome_provider.py     # Chrome WebDriver 생성 (향후)
└── configs/
    ├── webdriver_china.yaml   # 중국 지역 정책
    └── webdriver_global.yaml  # 글로벌 지역 정책

M:/Firefox_Profile/
├── CRAWL_CHINA/               # 중국 사이트용 프로필
│   ├── cookies.sqlite         # 쿠키 (Firefox 자동)
│   ├── webappsstore.sqlite    # localStorage (Firefox 자동)
│   └── prefs.js               # 설정 (Firefox 자동)
└── CRAWL_GLOBAL/              # 글로벌 사이트용 프로필
    ├── cookies.sqlite
    ├── webappsstore.sqlite
    └── prefs.js
```

---

## 🚀 **사용 패턴 (최종)**

### **Step 1: ConfigLoader로 YAML 로드**

```python
from cfg_utils import ConfigLoader
from crawl_utils.site_region_mapping import (
    get_config_path_for_site,
    get_region_for_site,
    get_user_agent
)

# 1. 사이트 → 지역
site = "taobao"
region = get_region_for_site(site)  # "china"

# 2. YAML 로드 (AL, profile_path 포함!)
config_path = get_config_path_for_site(site)
config = ConfigLoader(config_path)
webdriver_config = config.to_dict(section="webdriver")

# ✅ 이미 포함됨:
# - accept_languages: "zh-CN,zh;q=0.9,..."
# - firefox.profile_path: "M:/Firefox_Profile/CRAWL_CHINA"

# 3. UA만 런타임 주입 (browser_versions.json에서)
webdriver_config["user_agent"] = get_user_agent("firefox", region)

# 4. Provider 생성
provider = FirefoxProvider(webdriver_config)
driver = provider.create_driver()
```

---

## 🔥 **핵심 개선 사항**

### **Before (❌ 복잡 + 중복)**

```
1. YAML 파일 (4개): UA/AL 하드코딩
2. JSON 파일 (4개): UA/AL + 쿠키 저장
3. SessionManager: 쿠키 저장/복원
4. Firefox Profile: 쿠키 저장 (중복!)
```

**문제:**
- UA 업데이트: 4개 YAML + 4개 JSON = 8곳 수정
- 쿠키 중복 관리: SessionManager + Profile
- 동기화 문제: JSON 파일 오래된 UA

### **After (✅ 단순 + 명확)**

```
1. site_region_mapping.py: UA/AL 중앙 관리
2. webdriver_*.yaml (4개): 정책만
3. Firefox Profile: 모든 세션 관리
```

**장점:**
- UA 업데이트: 1줄만 수정!
- 쿠키 관리: Profile 하나만
- 동기화 문제 없음: 코드에서 항상 최신

---

## 📋 **UA 업데이트 방법**

### **수동 업데이트 (권장)**

```python
# site_region_mapping.py
BROWSER_VERSIONS = {
    "firefox": "145.0",  # ← 여기만 변경!
}
```

```bash
git add site_region_mapping.py
git commit -m "chore: update Firefox version to 145.0"
git push
```

### **자동 감지 (선택적)**

```python
# browser_version_manager.py 사용
from crawl_utils.browser_version_manager import get_firefox_version

version = get_firefox_version()  # "145.0" (설치된 Firefox 감지)
print(f"Current Firefox version: {version}")

# 수동으로 site_region_mapping.py 업데이트 권장
```

---

## 🎯 **최종 정리**

| 항목 | 관리 위치 | 업데이트 방법 | 이유 |
|------|----------|--------------|------|
| **User-Agent** | `browser_versions.json` | 프로그래밍 | 자주 변경 (브라우저 업데이트) |
| **Accept-Language** | `webdriver_*.yaml` | 수동 편집 | 지역별 고정값 (거의 변경 없음) |
| **Profile Path** | `webdriver_*.yaml` | 수동 편집 | 지역별 고정 경로 |
| **쿠키** | Firefox Profile | 자동 (Firefox) | 세션 데이터 |
| **localStorage** | Firefox Profile | 자동 (Firefox) | 세션 데이터 |
| **정책** | `webdriver_*.yaml` | 수동 편집 | 동작 제어 |

---

## ✅ **제거된 것들**

1. ❌ `session_manager.py` - Profile이 이미 모든 세션 관리
2. ❌ `webdriver_*.json` - 세션 파일 불필요 (Profile 사용)
3. ❌ `browser_sessions.json` - 통합 JSON 파일 불필요
4. ❌ `site_region_mapping.py`의 AL 관리 - YAML로 이동 (지역별 고정값)
5. ❌ `site_region_mapping.py`의 profile_path 생성 - YAML에 직접 명시

---

## 🚀 **결론**

**"프로필 = 모든 세션 관리"** 원칙을 따르면:

1. ✅ **SessionManager 불필요** (Profile이 이미 관리)
2. ✅ **JSON 파일 불필요** (UA/AL은 코드, 쿠키는 Profile)
3. ✅ **UA 업데이트 간단** (1줄만 수정)
4. ✅ **중복 제거** (단일 진실 공급원)

**완벽한 단순화 완성!** 🎉
