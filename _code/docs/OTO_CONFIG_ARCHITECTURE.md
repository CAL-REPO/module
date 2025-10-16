# OTO Script - Config Loading Architecture Update

## 📋 변경 사항

기존 xloto.yaml 통합 파일 방식에서 **config_loader 파일을 통한 모듈별 로딩 방식**으로 변경.

---

## ✅ 현재 구조

### 1. 파일 구조

```
configs/
├── paths.local.yaml              # ENV 변수가 가리키는 파일
├── loader/                       # ConfigLoader 정책 파일들
│   ├── config_loader_image.yaml
│   ├── config_loader_ocr.yaml
│   ├── config_loader_overlay.yaml
│   └── config_loader_translate.yaml
└── oto/                          # 실제 모듈 설정 파일들
    ├── image.yaml
    ├── ocr.yaml
    ├── overlay.yaml
    └── translate.yaml
```

### 2. 로딩 플로우

```
ENV: CASHOP_PATHS
    ↓
paths.local.yaml
    configs_loader_file_path:
        image: "configs/loader/config_loader_image.yaml"
        ocr: "configs/loader/config_loader_ocr.yaml"
        overlay: "configs/loader/config_loader_overlay.yaml"
        translate: "configs/loader/config_loader_translate.yaml"
    ↓
config_loader_image.yaml
    source_paths:
        path: "{configs_dir}/oto/image.yaml"
        section: "image"
    ↓
oto/image.yaml
    image:
        source: {...}
        save: {...}
        meta: {...}
        log: {...}
    ↓
ImageLoaderPolicy
```

### 3. OTO.py 로직

```python
# 1. ENV → paths.local.yaml
paths_yaml = os.getenv("CASHOP_PATHS")
paths_dict = ConfigLoader.load(paths_yaml)

# 2. config_loader 경로 추출
loader_paths = paths_dict["configs_loader_file_path"]
config_loader_image = loader_paths["image"]  # config_loader_image.yaml

# 3. config_loader를 통해 정책 로드
# config_loader_image.yaml 내부에 oto/image.yaml 경로가 정의됨
image_loader_policy = ConfigLoader.load(
    config_loader_image,
    model=ImageLoaderPolicy
)
# → ConfigLoader가 내부적으로 oto/image.yaml을 읽어서 ImageLoaderPolicy 생성
```

---

## 🎯 중요 포인트

### ❌ 중복 불필요

**paths.local.yaml에 oto 파일 경로를 직접 작성할 필요 없음:**

```yaml
# ❌ 불필요 - 작성하지 말 것
configs_oto_file_path:
  image: "configs/oto/image.yaml"
  ocr: "configs/oto/ocr.yaml"
  # ...
```

**이유:**
- `config_loader_image.yaml` 내부에 이미 경로가 정의되어 있음:
  ```yaml
  config_loader:
    yaml:
      source_paths:
        path: "{configs_dir}/oto/image.yaml"  # ← 여기에 이미 정의됨
  ```

### ✅ paths.local.yaml에 필요한 것

**config_loader 파일 경로만:**

```yaml
configs_loader_file_path:
  image: "${configs_loader_dir}/config_loader_image.yaml"
  ocr: "${configs_loader_dir}/config_loader_ocr.yaml"
  overlay: "${configs_loader_dir}/config_loader_overlay.yaml"
  translate: "${configs_loader_dir}/config_loader_translate.yaml"
```

---

## 🔧 수정된 파일

### 1. paths.local.yaml

```yaml
# configs_loader_file_path만 유지 (oto 경로 제거)
configs_loader_file_path:
  image: "${configs_loader_dir}/config_loader_image.yaml"
  ocr: "${configs_loader_dir}/config_loader_ocr.yaml"
  overlay: "${configs_loader_dir}/config_loader_overlay.yaml"
  translate: "${configs_loader_dir}/config_loader_translate.yaml"
```

### 2. scripts/oto.py

#### Before (xloto.yaml 방식)
```python
# 통합 파일 경로 추출
config_key = f"configs_{self.section}"  # configs_xloto
config_path = paths_dict.get(config_key)

# 섹션별 로드
ImageLoaderPolicy = ConfigLoader.load(
    config_path,
    model=ImageLoaderPolicy,
    section="image"  # xloto.yaml의 image 섹션
)
```

#### After (config_loader 방식)
```python
# config_loader 경로 추출
loader_paths = paths_dict["configs_loader_file_path"]
image_loader_path = loader_paths["image"]  # config_loader_image.yaml

# config_loader를 통해 로드
ImageLoaderPolicy = ConfigLoader.load(
    image_loader_path,
    model=ImageLoaderPolicy
)
# → ConfigLoader가 내부적으로 oto/image.yaml 읽음
```

### 3. CLI 변경

#### Before
```powershell
python oto.py --section xloto image.jpg  # section 인자 필요
```

#### After
```powershell
python oto.py image.jpg  # section 인자 제거 (자동으로 config_loader 사용)
```

---

## 🎉 장점

### 1. 중복 제거
- oto 파일 경로가 `config_loader` 파일에만 정의
- `paths.local.yaml`에서 중복 관리 불필요

### 2. 3-Tier Override 유지
```
Pydantic BaseModel defaults
    ↓
YAML (oto/image.yaml)
    ↓
Runtime arguments (oto.py의 **overrides)
```

### 3. Placeholder 자동 해석
```yaml
# config_loader_image.yaml
source_paths:
  path: "{configs_dir}/oto/image.yaml"
  # {configs_dir}는 ConfigLoader가 자동 해석
```

### 4. 모듈 독립성
- 각 모듈이 자신의 `config_loader` 파일을 가짐
- 다른 모듈에 영향 없이 개별 수정 가능

### 5. 설정 파일 분리
- 각 모듈별 설정이 독립적인 파일로 관리됨 (`oto/image.yaml`, `oto/ocr.yaml`, etc.)
- 가독성 및 유지보수성 향상

---

## 🚀 테스트 방법

```powershell
# 1. 환경변수 설정
$env:CASHOP_PATHS = "M:\CALife\CAShop - 구매대행\_code\configs\paths.local.yaml"

# 2. 테스트 실행
python scripts/oto.py test_image.jpg

# 예상 출력:
# 🔧 OTO Pipeline 초기화 중...
# paths.local.yaml 로드: M:\...\paths.local.yaml
# Config Loader 경로 로드 완료
#   ✅ image: M:\...\config_loader_image.yaml
#   ✅ ocr: M:\...\config_loader_ocr.yaml
#   ✅ overlay: M:\...\config_loader_overlay.yaml
#   ✅ translate: M:\...\config_loader_translate.yaml
# Config 정책 로드 중...
#   ✅ ImageLoader 정책 로드 완료
#   ✅ ImageOCR 정책 로드 완료
#   ⚠️  Translator 정책 로드 실패: ...
#   ✅ ImageOverlay 정책 로드 완료
# OTO Pipeline 초기화 완료
```

---

## 📝 현재 상태

### ✅ 완료
- [x] paths.local.yaml 구조 확인
- [x] config_loader 파일들 존재 확인 (configs/loader/)
- [x] 실제 설정 파일들 존재 확인 (configs/oto/)
- [x] oto.py 로딩 로직 수정
- [x] 중복 경로 제거
- [x] CLI 인자 단순화 (--section 제거)

### ⏳ 다음 단계
1. 테스트 이미지 준비
2. 환경변수 설정 확인
3. End-to-End 테스트 실행
4. Translator 통합 (현재 임시 구현)

---

**작성일**: 2025-10-16  
**작성자**: GitHub Copilot  
**버전**: 2.0 (Config Loader 아키텍처)
