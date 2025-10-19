# 🔥 CAShop 프로젝트 필수 환경변수 설정

## ⚠️ 절대 까먹지 말 것!

### 1. CASHOP_PATHS (최우선 필수)

```powershell
# PowerShell에서 임시 설정
$env:CASHOP_PATHS = "M:\CALife\CAShop - 구매대행\_code\configs\paths.local.yaml"
```

```cmd
# CMD에서 임시 설정
set CASHOP_PATHS=M:\CALife\CAShop - 구매대행\_code\configs\paths.local.yaml
```

#### 영구 설정 (권장)

**방법 1: 시스템 환경변수 (Windows)**
1. `Win + X` → "시스템"
2. "고급 시스템 설정" → "환경 변수"
3. "사용자 변수" 또는 "시스템 변수"에서 "새로 만들기"
4. 변수 이름: `CASHOP_PATHS`
5. 변수 값: `M:\CALife\CAShop - 구매대행\_code\configs\paths.local.yaml`

**방법 2: PowerShell 프로필 자동 설정**
```powershell
# PowerShell 프로필 편집
notepad $PROFILE

# 아래 내용 추가
$env:CASHOP_PATHS = "M:\CALife\CAShop - 구매대행\_code\configs\paths.local.yaml"
```

---

## 🎯 왜 필요한가?

### ConfigLoader 동작 원리:

```
1순위: 환경변수 CASHOP_PATHS 파싱
  ↓
  M:\CALife\CAShop - 구매대행\_code\configs\paths.local.yaml
  ↓
2순위: paths.local.yaml에서 참조 해석
  - {{configs_dir}} → M:/CALife/CAShop - 구매대행/_code/configs
  - {{configs_xl_dir}} → {{configs_dir}}/xl
  - {{configs_oto_dir}} → {{configs_dir}}/oto
  - ${public_dir} → {{root}}/_public
  - ${root} → M:/CALife/CAShop - 구매대행
  ↓
3순위: 개별 YAML 파일 로드
  - config_loader_xloto.yaml의 source 섹션
  - enable_env: true로 참조 해석 활성화
```

### 사용하는 모든 곳:

1. **cfg_utils (ConfigLoader)**
   - 모든 config_loader_*.yaml 파일 로드 시
   - 환경변수 기반 경로 resolving

2. **xloto.py**
   ```python
   config = ConfigLoader(config_loader_cfg_path=str(config_path))
   # CASHOP_PATHS → paths.local.yaml → {{configs_xl_dir}} 해석
   ```

3. **oto.py**
   ```python
   config = ConfigLoader(config_loader_cfg_path="config_loader_oto.yaml")
   # CASHOP_PATHS → paths.local.yaml → {{configs_oto_dir}} 해석
   ```

4. **모든 EntryPoint 스크립트**
   - xloto.py
   - xlcrawl.py
   - oto.py
   - etc.

---

## ⚠️ 설정 안 하면?

```
❌ FileNotFoundError: YAML file not found: {{configs_xl_dir}}\excel.yaml
❌ 참조 변수가 해석되지 않음
❌ 모든 ConfigLoader 기반 스크립트 실패
```

---

## ✅ 확인 방법

```powershell
# PowerShell
echo $env:CASHOP_PATHS

# CMD
echo %CASHOP_PATHS%

# Python
import os
print(os.environ.get("CASHOP_PATHS"))
```

**출력 예상 결과:**
```
M:\CALife\CAShop - 구매대행\_code\configs\paths.local.yaml
```

---

## 📝 paths.local.yaml 내용 (참고)

```yaml
# 환경변수 resolving의 기준이 되는 파일
root: "M:/CALife/CAShop - 구매대행"

# configs 관련 경로
configs_dir: "{{root}}/_code/configs"
configs_xl_dir: "{{configs_dir}}/xl"
configs_oto_dir: "{{configs_dir}}/oto"
configs_loader_dir: "{{configs_dir}}/loader"

# public 디렉토리
public_dir: "{{root}}/_public"
public_img_dir: "{{public_dir}}/01.IMAGE"

# data 디렉토리
data_dir: "{{root}}/_code/data"
db_dir: "{{data_dir}}/db"
fonts_dir: "{{data_dir}}/fonts"

# input/output
input_dir: "{{root}}/_code/input"
output_dir: "{{root}}/_code/output"

# logs
logs_dir: "{{root}}/_code/logs"
```

---

## 🔥 핵심 요약

> **ConfigLoader 사용 시 가장 먼저 CASHOP_PATHS 환경변수를 확인하고,**  
> **paths.local.yaml에서 모든 참조 변수를 해석합니다.**  
> **enable_env: true는 이 기능을 활성화하는 스위치입니다.**

**절대 까먹지 마세요!** 🚨
