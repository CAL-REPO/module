# 🦊 Firefox 프로필 관리 가이드

**작성일:** 2025-10-21  
**대상:** CAShop 구매대행 크롤링 시스템  
**목적:** Firefox 프로필 분리 전략 및 설정 가이드

---

## 📋 목차

1. [프로필 개요](#1-프로필-개요)
2. [사이트별 프로필 전략](#2-사이트별-프로필-전략)
3. [프로필 생성 및 관리](#3-프로필-생성-및-관리)
4. [프로필별 설정 가이드](#4-프로필별-설정-가이드)
5. [세션 관리 전략](#5-세션-관리-전략)
6. [문제 해결](#6-문제-해결)
7. [베스트 프랙티스](#7-베스트-프랙티스)

---

## 1. 프로필 개요

### 1.1 Firefox 프로필이란?

Firefox 프로필은 사용자별 설정, 쿠키, 히스토리, 북마크 등을 저장하는 **독립적인 저장소**입니다.

```
Firefox 프로필 = 가상의 "사용자 계정"

프로필 A                  프로필 B
├─ cookies.sqlite        ├─ cookies.sqlite
├─ sessionstore.jsonlz4  ├─ sessionstore.jsonlz4
├─ prefs.js             ├─ prefs.js
├─ places.sqlite        ├─ places.sqlite
└─ ...                  └─ ...

→ 서로 완전히 독립적!
```

### 1.2 프로필 분리의 장점

| 장점 | 설명 |
|------|------|
| **세션 격리** | 사이트별 로그인 상태 독립 관리 |
| **설정 독립** | 언어, 쿠키, 캐시 설정 별도 적용 |
| **보안 강화** | 계정 간 간섭 방지 |
| **디버깅 용이** | 문제 발생 시 프로필 단위 격리 |
| **테스트 편의** | 프로덕션/테스트 환경 분리 |

### 1.3 프로필 분리의 단점

| 단점 | 설명 |
|------|------|
| **디스크 사용량 증가** | 프로필당 50-500MB |
| **관리 복잡도** | 여러 프로필 동시 관리 필요 |
| **초기 설정 시간** | 프로필별 수동 설정 필요 |
| **메모리 사용 증가** | 동시 실행 시 메모리 부담 |

---

## 2. 사이트별 프로필 전략

### 2.1 알리바바 그룹 플랫폼 분석

```
알리바바 그룹 (Alibaba Group)
│
├─ 🏢 Alibaba.com (B2B)
│  ├─ 서버: 독립 서버
│  ├─ 계정: 독립 계정 시스템
│  └─ 프로필 전략: ✅ 독립 프로필
│
├─ 🛒 AliExpress (B2C 글로벌)
│  ├─ 서버: 독립 서버
│  ├─ 계정: 독립 계정 시스템
│  └─ 프로필 전략: ✅ 독립 프로필
│
├─ 🛍️ Taobao (C2C 중국)
│  ├─ 서버: 독립 서버 (Tmall과 일부 공유)
│  ├─ 계정: Tmall과 공유 (SSO)
│  └─ 프로필 전략: 🚫 Tmall과 통합 필수
│
└─ 🏬 Tmall (B2C 중국)
   ├─ 서버: Taobao와 일부 공유
   ├─ 계정: Taobao와 공유 (SSO)
   └─ 프로필 전략: 🚫 Taobao와 통합 필수
```

### 2.2 프로필 분리 가능 여부

| 사이트 A | 사이트 B | 서버 독립성 | 계정 독립성 | 프로필 분리 | 동시 크롤링 |
|----------|----------|-------------|-------------|-------------|-------------|
| **Alibaba.com** | **AliExpress** | ✅ 완전 독립 | ✅ 완전 독립 | ✅ 가능 | ✅ 안전 |
| **Alibaba.com** | **Taobao** | ✅ 완전 독립 | ✅ 완전 독립 | ✅ 가능 | ✅ 안전 |
| **AliExpress** | **Taobao** | ✅ 완전 독립 | ✅ 완전 독립 | ✅ 가능 | ✅ 안전 |
| **Taobao** | **Tmall** | ❌ 일부 공유 | ❌ SSO 공유 | 🚫 **통합 필수** | ⚠️ 위험 |

### 2.3 권장 프로필 구조

```
M:/Firefox_Profile/
│
├─ AliExpress/              # ✅ AliExpress 전용
│  ├─ cookies.sqlite
│  ├─ sessionstore.jsonlz4
│  └─ prefs.js
│     └─ accept_languages: "en-US,en;q=0.9,ko;q=0.8"
│
├─ Alibaba_B2B/             # ✅ Alibaba.com 전용
│  ├─ cookies.sqlite
│  ├─ sessionstore.jsonlz4
│  └─ prefs.js
│     └─ accept_languages: "en-US,en;q=0.9,zh-CN;q=0.8"
│
├─ Taobao_Tmall_Unified/    # ✅ Taobao & Tmall 통합
│  ├─ cookies.sqlite        # (Taobao + Tmall 쿠키 공유)
│  ├─ sessionstore.jsonlz4  # (SSO 세션 공유)
│  └─ prefs.js
│     └─ accept_languages: "zh-CN,zh;q=0.9,ko;q=0.8"
│
└─ Test/                     # ✅ 테스트용 프로필
   └─ ...
```

---

## 3. 프로필 생성 및 관리

### 3.1 현재 프로필 확인 방법

#### 방법 A: about:profiles (가장 쉬움)

1. Firefox 주소창에 입력:
   ```
   about:profiles
   ```

2. 현재 사용 중인 프로필 확인:
   ```
   현재 사용 중인 프로필 (This is the profile in use)
   
   프로필 이름: default-release
   루트 디렉토리: C:\Users\사용자명\AppData\Roaming\Mozilla\Firefox\Profiles\xxxxx.default-release
   ```

3. [폴더 열기] 버튼 클릭

#### 방법 B: about:support

1. Firefox 주소창에 입력:
   ```
   about:support
   ```

2. "프로필 폴더" 항목에서 [폴더 열기] 클릭

#### 방법 C: Windows 탐색기

```
%APPDATA%\Mozilla\Firefox\Profiles
```

### 3.2 커스텀 프로필 생성

#### 방법 A: Firefox Profile Manager

1. **Firefox 완전 종료**

2. **Windows + R 키 → 실행:**
   ```
   firefox.exe -P
   ```

3. **프로필 관리자에서:**
   - [프로필 만들기] 클릭
   - 프로필 이름 입력: `AliExpress`
   - [폴더 선택...] → `M:\Firefox_Profile\AliExpress` 선택
   - [완료]

#### 방법 B: 명령줄로 프로필 생성

```powershell
# PowerShell에서 실행

# 프로필 폴더 생성
New-Item -ItemType Directory -Path "M:\Firefox_Profile\AliExpress" -Force

# Firefox 실행 (프로필 자동 생성)
& "C:\Program Files\Mozilla Firefox\firefox.exe" -profile "M:\Firefox_Profile\AliExpress" -no-remote
```

### 3.3 프로필 실행 명령어

```powershell
# 단일 프로필 실행
& "C:\Program Files\Mozilla Firefox\firefox.exe" -profile "M:\Firefox_Profile\AliExpress" -no-remote

# 여러 프로필 동시 실행
& "C:\Program Files\Mozilla Firefox\firefox.exe" -profile "M:\Firefox_Profile\AliExpress" -no-remote
& "C:\Program Files\Mozilla Firefox\firefox.exe" -profile "M:\Firefox_Profile\Taobao_Tmall" -no-remote
```

**중요:** `-no-remote` 옵션은 여러 프로필을 동시에 실행할 수 있게 합니다.

---

## 4. 프로필별 설정 가이드

### 4.1 AliExpress 프로필 설정

#### Step 1: 프로필 실행
```powershell
& "C:\Program Files\Mozilla Firefox\firefox.exe" -profile "M:\Firefox_Profile\AliExpress" -no-remote
```

#### Step 2: 언어 설정
1. `about:preferences#general` 접속
2. "언어" 섹션 → [언어 설정...]
3. 추가 언어:
   - `English (United States)` (최우선)
   - `한국어` (보조)
4. 순서: English > 한국어

#### Step 3: 로그인
1. `https://www.aliexpress.com` 접속
2. 계정 로그인
3. "Keep me signed in" 체크
4. 브라우저 종료 후 재실행하여 로그인 유지 확인

#### Step 4: 설정 파일 확인
```powershell
# 쿠키 파일 존재 확인
Test-Path "M:\Firefox_Profile\AliExpress\cookies.sqlite"
# True가 나와야 함
```

### 4.2 Taobao & Tmall 통합 프로필 설정

#### Step 1: 프로필 실행
```powershell
& "C:\Program Files\Mozilla Firefox\firefox.exe" -profile "M:\Firefox_Profile\Taobao_Tmall" -no-remote
```

#### Step 2: 언어 설정
1. `about:preferences#general` 접속
2. "语言" 섹션 → [选择语言...]
3. 추가 언어:
   - `中文 (简体)` (최우선)
   - `한국어` (보조)
4. 순서: 中文 (简体) > 한국어

#### Step 3: Taobao 로그인
1. `https://www.taobao.com` 접속
2. 계정 로그인 (중국 휴대폰 필요)
3. "记住我" (로그인 상태 유지) 체크

#### Step 4: Tmall 자동 로그인 확인
1. `https://www.tmall.com` 접속
2. **자동으로 로그인되는지 확인** (SSO)
3. 로그인되지 않으면 Step 3 재시도

#### Step 5: 세션 공유 확인
```
Taobao 로그인 → Tmall 자동 로그인 ✅
Tmall 로그인 → Taobao 자동 로그인 ✅

→ SSO 세션 공유 정상 작동
```

### 4.3 Alibaba.com (B2B) 프로필 설정

#### Step 1: 프로필 실행
```powershell
& "C:\Program Files\Mozilla Firefox\firefox.exe" -profile "M:\Firefox_Profile\Alibaba_B2B" -no-remote
```

#### Step 2: 언어 설정
1. `about:preferences#general` 접속
2. "Language" 섹션 → [Set Alternatives...]
3. 추가 언어:
   - `English (United States)` (최우선)
   - `中文 (简体)` (보조)
   - `한국어` (보조)

#### Step 3: 기업 계정 로그인
1. `https://www.alibaba.com` 접속
2. 기업 계정 로그인
3. "Remember me" 체크

---

## 5. 세션 관리 전략

### 5.1 세션 파일 구조

```yaml
# 현재 프로젝트 설정 (문제 있음)
# configs/firefox_aliexpress.yaml
session_path: "{{data_dir}}/sessions/firefox_HK.json"  # ⚠️ 공통 세션

# configs/firefox_taobao.yaml
session_path: "{{data_dir}}/sessions/firefox_HK.json"  # ⚠️ 공통 세션
```

**문제점:**
- 모든 사이트가 같은 세션 파일 사용
- 동시 크롤링 시 세션 충돌 가능

### 5.2 권장 세션 파일 구조

```yaml
# configs/firefox_aliexpress.yaml
firefox:
  site: "aliexpress"
  session_path: "{{data_dir}}/sessions/aliexpress_session.json"  # ✅ 독립 세션
  profile_path: "M:/Firefox_Profile/AliExpress"                  # ✅ 독립 프로필

# configs/firefox_alibaba_b2b.yaml
firefox:
  site: "alibaba"
  session_path: "{{data_dir}}/sessions/alibaba_b2b_session.json"  # ✅ 독립 세션
  profile_path: "M:/Firefox_Profile/Alibaba_B2B"                  # ✅ 독립 프로필

# configs/firefox_taobao_tmall.yaml
firefox:
  site: "taobao_tmall"
  session_path: "{{data_dir}}/sessions/taobao_tmall_unified.json"  # ✅ 통합 세션
  profile_path: "M:/Firefox_Profile/Taobao_Tmall_Unified"          # ✅ 통합 프로필
```

### 5.3 세션 파일 디렉토리 구조

```
M:/CALife/CAShop - 구매대행/_code/data/sessions/
│
├─ aliexpress_session.json          # AliExpress 세션
├─ alibaba_b2b_session.json         # Alibaba.com 세션
├─ taobao_tmall_unified.json        # Taobao & Tmall 통합 세션
└─ test_session.json                # 테스트용 세션
```

---

## 6. 문제 해결

### 6.1 Taobao & Tmall 분리 프로필 사용 시 문제

#### 🔴 문제 #1: 동시 세션 감지
```
증상:
- Taobao 프로필로 로그인
- Tmall 프로필로 동일 계정 로그인 시도
- "您的账号在其他设备登录" (다른 기기에서 로그인됨) 메시지

원인:
- 알리바바 SSO 서버가 중복 세션 감지

해결책:
→ 통합 프로필 사용 (Taobao_Tmall_Unified)
```

#### 🔴 문제 #2: IP 기반 이상 행위 감지
```
증상:
- 같은 IP에서 Taobao 프로필로 50개 상품 조회
- 같은 IP에서 Tmall 프로필로 30개 상품 조회
- 캡차(CAPTCHA) 발생

원인:
- 같은 IP에서 다른 세션으로 빈번한 접근

해결책:
1. 통합 프로필 사용
2. 시간차 크롤링 (5분 간격)
3. 프록시 분리 (비로그인 크롤링 시)
```

#### 🔴 문제 #3: 디바이스 핑거프린팅 충돌
```
증상:
- 다른 프로필인데 디바이스 정보가 동일
- 봇 의심으로 보안 검증 요구

원인:
- User-Agent, 화면 해상도, Canvas fingerprint 동일

해결책:
1. 통합 프로필 사용 (권장)
2. User-Agent 랜덤화 + Canvas 랜덤화
```

### 6.2 프로필 손상 복구

#### 증상:
- Firefox 실행 시 "프로필이 손상되었습니다" 메시지
- 로그인 정보 손실

#### 복구 방법:

```powershell
# 1. 프로필 백업
Copy-Item "M:\Firefox_Profile\AliExpress" "M:\Firefox_Profile\AliExpress_backup" -Recurse

# 2. 손상된 파일 삭제
Remove-Item "M:\Firefox_Profile\AliExpress\sessionstore.jsonlz4"
Remove-Item "M:\Firefox_Profile\AliExpress\sessionstore-backups" -Recurse

# 3. Firefox 재시작
& "C:\Program Files\Mozilla Firefox\firefox.exe" -profile "M:\Firefox_Profile\AliExpress" -no-remote

# 4. 로그인 재설정
```

### 6.3 프로필 동기화 실패

#### 증상:
- Selenium으로 프로필 로드 시 로그인 정보 없음
- 수동 설정한 언어가 적용되지 않음

#### 해결 방법:

```python
# 프로필 경로가 정확한지 확인
import os

profile_path = "M:/Firefox_Profile/AliExpress"
if not os.path.exists(profile_path):
    print(f"❌ 프로필 폴더 없음: {profile_path}")
else:
    print(f"✅ 프로필 폴더 존재: {profile_path}")
    
    # 쿠키 파일 확인
    cookies_file = os.path.join(profile_path, "cookies.sqlite")
    if os.path.exists(cookies_file):
        print(f"✅ 쿠키 파일 존재")
    else:
        print(f"❌ 쿠키 파일 없음 → 로그인 필요")
```

---

## 7. 베스트 프랙티스

### 7.1 프로필 명명 규칙

```
✅ 좋은 예:
- AliExpress
- Taobao_Tmall_Unified
- Alibaba_B2B
- Test_AliExpress

❌ 나쁜 예:
- Profile1
- THKIM (사용자 이름)
- firefox_profile (목적 불명확)
```

### 7.2 프로필 백업 전략

```powershell
# 프로필 백업 스크립트
# backup_profiles.ps1

$ProfileBase = "M:\Firefox_Profile"
$BackupBase = "M:\Firefox_Profile_Backup"
$Date = Get-Date -Format "yyyyMMdd_HHmmss"

$Profiles = @("AliExpress", "Taobao_Tmall_Unified", "Alibaba_B2B")

foreach ($Profile in $Profiles) {
    $Source = Join-Path $ProfileBase $Profile
    $Dest = Join-Path $BackupBase "$Profile`_$Date"
    
    if (Test-Path $Source) {
        Copy-Item $Source $Dest -Recurse
        Write-Host "✅ 백업 완료: $Profile"
    }
}
```

**백업 주기:** 주 1회 또는 중요 설정 변경 전

### 7.3 프로필 정리 주기

```
정기 정리 항목:
[ ] 쿠키 만료 확인 (3개월마다)
[ ] 캐시 정리 (1개월마다)
[ ] 히스토리 삭제 (6개월마다)
[ ] 사용하지 않는 프로필 삭제
```

### 7.4 보안 강화 설정

#### about:config 권장 설정

```
# WebRTC IP 유출 방지
media.peerconnection.enabled = false

# 자동화 탐지 회피
dom.webdriver.enabled = false

# 위치 정보 차단
geo.enabled = false

# WebGL 비활성화 (핑거프린팅 방지)
webgl.disabled = true

# 리퍼러 정책 강화
network.http.referer.XOriginPolicy = 2
```

### 7.5 성능 최적화

```yaml
# Firefox 옵션 최적화
firefox:
  # 이미지 로딩 (필요 시에만)
  load_images: false  # 속도 2배 향상
  
  # JavaScript (필수 아니면 비활성화)
  enable_javascript: true
  
  # 캐시 (개발 시 비활성화)
  enable_cache: false
  
  # Headless 모드 (안정성 높음)
  headless: true
```

---

## 8. 프로필 관리 스크립트

### 8.1 프로필 자동 설정 스크립트

```powershell
# setup_firefox_profiles.ps1

$FirefoxPath = "C:\Program Files\Mozilla Firefox\firefox.exe"
$ProfileBase = "M:\Firefox_Profile"

function New-FirefoxProfile {
    param(
        [string]$ProfileName,
        [string]$URL = "",
        [string]$Language = "en-US"
    )
    
    $ProfilePath = Join-Path $ProfileBase $ProfileName
    
    # 프로필 폴더 생성
    if (-not (Test-Path $ProfilePath)) {
        New-Item -ItemType Directory -Path $ProfilePath -Force
        Write-Host "✅ 프로필 생성: $ProfileName"
    }
    
    # Firefox 실행
    $Args = @("-profile", $ProfilePath, "-no-remote")
    if ($URL) {
        $Args += $URL
    }
    
    Start-Process $FirefoxPath -ArgumentList $Args
    Write-Host "🦊 Firefox 프로필 실행: $ProfileName"
}

# 메뉴
Write-Host @"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Firefox 프로필 설정 도구
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. AliExpress 프로필 생성
2. Taobao & Tmall 통합 프로필 생성
3. Alibaba B2B 프로필 생성
4. 모든 프로필 생성
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"@

$choice = Read-Host "선택 (1-4)"

switch ($choice) {
    "1" { 
        New-FirefoxProfile -ProfileName "AliExpress" -URL "https://www.aliexpress.com" -Language "en-US"
    }
    "2" { 
        New-FirefoxProfile -ProfileName "Taobao_Tmall_Unified" -URL "https://www.taobao.com" -Language "zh-CN"
    }
    "3" { 
        New-FirefoxProfile -ProfileName "Alibaba_B2B" -URL "https://www.alibaba.com" -Language "en-US"
    }
    "4" {
        New-FirefoxProfile -ProfileName "AliExpress" -URL "https://www.aliexpress.com" -Language "en-US"
        Start-Sleep -Seconds 2
        New-FirefoxProfile -ProfileName "Taobao_Tmall_Unified" -URL "https://www.taobao.com" -Language "zh-CN"
        Start-Sleep -Seconds 2
        New-FirefoxProfile -ProfileName "Alibaba_B2B" -URL "https://www.alibaba.com" -Language "en-US"
    }
    default { Write-Host "❌ 잘못된 선택" }
}
```

### 8.2 프로필 검증 스크립트

```powershell
# verify_profiles.ps1

$ProfileBase = "M:\Firefox_Profile"
$Profiles = @("AliExpress", "Taobao_Tmall_Unified", "Alibaba_B2B")

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host "   Firefox 프로필 검증"
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

foreach ($Profile in $Profiles) {
    $ProfilePath = Join-Path $ProfileBase $Profile
    Write-Host "`n📁 프로필: $Profile"
    
    # 프로필 폴더 확인
    if (Test-Path $ProfilePath) {
        Write-Host "  ✅ 폴더 존재: $ProfilePath"
        
        # 쿠키 파일 확인
        $CookiesFile = Join-Path $ProfilePath "cookies.sqlite"
        if (Test-Path $CookiesFile) {
            $FileSize = (Get-Item $CookiesFile).Length / 1KB
            Write-Host "  ✅ 쿠키 파일: $([math]::Round($FileSize, 2)) KB"
        } else {
            Write-Host "  ⚠️  쿠키 파일 없음 (로그인 필요)"
        }
        
        # 세션 파일 확인
        $SessionFile = Join-Path $ProfilePath "sessionstore.jsonlz4"
        if (Test-Path $SessionFile) {
            Write-Host "  ✅ 세션 파일 존재"
        } else {
            Write-Host "  ⚠️  세션 파일 없음"
        }
        
        # 설정 파일 확인
        $PrefsFile = Join-Path $ProfilePath "prefs.js"
        if (Test-Path $PrefsFile) {
            Write-Host "  ✅ 설정 파일 존재"
        } else {
            Write-Host "  ⚠️  설정 파일 없음"
        }
        
    } else {
        Write-Host "  ❌ 프로필 폴더 없음: $ProfilePath"
    }
}

Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

---

## 9. 체크리스트

### 9.1 프로필 생성 체크리스트

```
[ ] 프로필 이름 결정 (사이트명_용도)
[ ] 프로필 폴더 생성 (M:\Firefox_Profile\{name})
[ ] Firefox로 프로필 실행 확인
[ ] 언어 설정 완료
[ ] 로그인 완료 및 쿠키 저장 확인
[ ] 브라우저 재시작 후 로그인 유지 확인
[ ] YAML 설정 파일 업데이트
[ ] Selenium 테스트 실행 성공
```

### 9.2 Taobao & Tmall 통합 체크리스트

```
[ ] 통합 프로필 생성 (Taobao_Tmall_Unified)
[ ] Taobao 로그인 완료
[ ] Tmall 자동 로그인 확인 (SSO)
[ ] 쿠키 도메인 확인 (.taobao.com, .tmall.com)
[ ] 세션 공유 테스트 (Taobao ↔ Tmall)
[ ] YAML에서 session_path 통합
[ ] YAML에서 profile_path 통합
[ ] 동시 크롤링 테스트 (금지)
```

### 9.3 보안 체크리스트

```
[ ] WebRTC IP 유출 확인 (ipleak.net)
[ ] DNS 유출 확인 (dnsleaktest.com)
[ ] VPN 연결 확인 (whoer.net)
[ ] 디바이스 핑거프린팅 확인 (browserleaks.com)
[ ] 자동화 탐지 우회 확인 (dom.webdriver.enabled = false)
[ ] 쿠키 만료 기간 확인 (3개월 이내)
```

---

## 10. 참고 자료

### 10.1 Firefox 공식 문서
- [Profile Manager](https://support.mozilla.org/en-US/kb/profile-manager-create-remove-switch-firefox-profiles)
- [about:profiles](https://support.mozilla.org/en-US/kb/dedicated-profiles-firefox-installation)
- [Command Line Options](https://developer.mozilla.org/en-US/docs/Mozilla/Command_Line_Options)

### 10.2 관련 문서
- [CRAWL_UTILS_COMPREHENSIVE_REVIEW.md](./CRAWL_UTILS_COMPREHENSIVE_REVIEW.md)
- [REFACTORING_COMPLETE_REPORT.md](./REFACTORING_COMPLETE_REPORT.md)

### 10.3 외부 도구
- [IP 확인](https://api.ipify.org)
- [VPN 테스트](https://ipleak.net)
- [브라우저 테스트](https://browserleaks.com)

---

## 11. 결론

### ✅ 핵심 요약

1. **Alibaba.com ↔ AliExpress**: 독립 프로필 가능 ✅
2. **AliExpress ↔ Taobao**: 독립 프로필 가능 ✅
3. **Taobao ↔ Tmall**: **통합 프로필 필수** 🚫

### 🎯 권장 프로필 구조

```
M:/Firefox_Profile/
├─ AliExpress/              # ✅ 독립
├─ Alibaba_B2B/             # ✅ 독립
├─ Taobao_Tmall_Unified/    # ✅ 통합 (SSO)
└─ Test/                     # ✅ 테스트
```

### 📌 핵심 원칙

```
┌─────────────────────────────────────────────────────┐
│  프로필 분리 원칙                                     │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ✅ 서버 독립 → 프로필 분리 가능                      │
│  ✅ 계정 독립 → 프로필 분리 가능                      │
│  🚫 SSO 연동 → 프로필 통합 필수                      │
│                                                      │
│  예외: Taobao ↔ Tmall (SSO 공유)                    │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

**문서 작성일:** 2025-10-21  
**버전:** 1.0  
**작성자:** GitHub Copilot
