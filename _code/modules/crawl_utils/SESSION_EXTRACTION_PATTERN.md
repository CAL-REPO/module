# 🎯 WebDriver 세션 관리 최종 구조

## ✅ **핵심 원칙: WebDriver에서 직접 추출**

### **1. 크롤링 단계 (WebDriver 생성 및 사용)**

```python
from cfg_utils import ConfigLoader
from crawl_utils.site_region_mapping import get_config_path_for_site
from crawl_utils.providers import FirefoxProvider

# 1. 사이트 → YAML 선택
config_path = get_config_path_for_site("taobao")

# 2. YAML 로드 + UA 주입
config = ConfigLoader(config_path)
webdriver_config = config.to_dict(section="webdriver")
webdriver_config["user_agent"] = get_user_agent("firefox")  # browser_versions.json

# 3. WebDriver 생성
provider = FirefoxProvider(webdriver_config)
driver = provider.create_driver()

# 4. 크롤링...
driver.get("https://www.taobao.com")
# ...

# 5. 세션 정보 저장 (WebDriver에서 직접 추출!)
session_info = extract_session_info(driver)
save_session(session_info, "taobao_session.json")

driver.quit()
```

### **2. 세션 정보 추출 함수**

```python
def extract_session_info(driver) -> dict:
    """WebDriver에서 실제 사용 중인 세션 정보 추출
    
    Returns:
        {
            "user_agent": "실제 사용된 UA",
            "accept_languages": "실제 사용된 AL",
            "cookies": [...],
            "profile_path": "실제 사용된 프로필 경로",
            "site": "taobao",
            "region": "china",
            "timestamp": "2025-10-21T12:00:00"
        }
    """
    return {
        # WebDriver에서 직접 추출 (설정값 아님!)
        "user_agent": driver.execute_script("return navigator.userAgent;"),
        "accept_languages": driver.execute_script("return navigator.languages.join(',');"),
        "cookies": driver.get_cookies(),
        
        # Firefox 특정 정보
        "profile_path": driver.capabilities.get("moz:profile"),
        
        # 메타 정보
        "site": current_site,
        "region": current_region,
        "timestamp": datetime.now().isoformat()
    }
```

### **3. 다운로드 단계 (세션 복원)**

```python
# 1. 세션 정보 로드
session_info = load_session("taobao_session.json")

# 2. WebDriver 생성 (세션 정보 기반)
driver = create_driver_from_session(session_info)

# 3. 다운로드...
driver.get(download_url)
# ...
```

### **4. 세션 기반 WebDriver 생성**

```python
def create_driver_from_session(session_info: dict):
    """세션 정보로 WebDriver 재생성
    
    Args:
        session_info: extract_session_info()로 저장한 정보
    
    Returns:
        WebDriver 인스턴스
    """
    # 1. 지역 정보로 YAML 로드
    region = session_info["region"]
    config_path = get_config_path_for_region(region)
    config = ConfigLoader(config_path)
    webdriver_config = config.to_dict(section="webdriver")
    
    # 2. 세션 정보로 덮어쓰기 (실제 사용했던 값!)
    webdriver_config["user_agent"] = session_info["user_agent"]
    webdriver_config["accept_languages"] = session_info["accept_languages"]
    webdriver_config["firefox"]["profile_path"] = session_info["profile_path"]
    
    # 3. WebDriver 생성
    provider = FirefoxProvider(webdriver_config)
    driver = provider.create_driver()
    
    # 4. 쿠키 복원
    driver.get(f"https://{session_info['site']}.com")  # 쿠키 도메인
    for cookie in session_info["cookies"]:
        driver.add_cookie(cookie)
    
    return driver
```

---

## 📊 **비교: 설정 기반 vs WebDriver 추출**

| 항목 | 설정 기반 (현재) | WebDriver 추출 (올바름) |
|------|------------------|------------------------|
| **User-Agent** | browser_versions.json | `navigator.userAgent` |
| **Accept-Language** | YAML 또는 코드 | `navigator.languages` |
| **실제 사용 값** | ❌ 보장 안 됨 | ✅ 정확히 일치 |
| **세션 복원** | ⚠️ 불일치 가능 | ✅ 완벽 복원 |
| **브라우저 변경** | ❌ 반영 안 됨 | ✅ 자동 반영 |

---

## 🎯 **최종 흐름도**

```
크롤링 단계:
1. 사이트 → 지역 매핑 (site_region_mapping.py)
2. 지역 → YAML 선택 (webdriver_china.yaml)
3. YAML + browser_versions.json → WebDriver 생성
4. 크롤링...
5. WebDriver에서 실제 사용 정보 추출 → session.json 저장 ✅

다운로드 단계:
1. session.json 로드
2. 실제 사용했던 UA/AL/Profile로 WebDriver 생성 ✅
3. 쿠키 복원
4. 다운로드
```

---

## ✅ **결론**

> **"설정 파일(YAML/JSON)은 초기값일 뿐!"**  
> **"실제 세션 복원은 WebDriver가 사용한 값을 직접 추출해야 함!"**

**기존 방식이 정확했습니다!** 🎯
