# Section-Based Configuration Guide

## 📚 섹션 기반 설정 구조

모든 YAML 설정 파일은 **섹션 기반 구조**를 사용합니다. 이를 통해:
1. 개별 파일로 사용 가능
2. 통합 파일(unified.yaml)에서 여러 엔트리포인트 설정 통합 가능
3. ConfigLoader가 자동으로 적절한 섹션 감지

---

## 🎯 설정 파일 구조

### 1. 개별 섹션 파일

각 엔트리포인트는 자신의 섹션 이름을 가집니다:

#### **pillow.yaml** (ImageLoader)
```yaml
pillow:  # ← 섹션 이름
  source:
    path: "..."
  image:
    save_copy: true
  meta:
    save_meta: true
  processing:
    resize_to: null
```

#### **overlay.yaml** (ImageOverlay)
```yaml
overlay:  # ← 섹션 이름
  source:
    path: "..."
  output:
    save_copy: true
  font:
    family: "..."
  texts:
    - text: "..."
```

#### **ocr.yaml** (ImageOCR)
```yaml
ocr:  # ← 섹션 이름
  file:
    file_path: "..."
  provider:
    provider: "paddle"
  preprocess:
    max_width: 1200
```

---

### 2. 통합 설정 파일 (unified.yaml)

모든 섹션을 하나의 파일에 포함:

```yaml
# 통합 설정 파일
pillow:
  source:
    path: "..."
  # ... pillow 설정

ocr:
  file:
    file_path: "..."
  # ... ocr 설정

overlay:
  source:
    path: "..."
  # ... overlay 설정
```

---

## 🔧 사용 방법

### 방법 1: 개별 파일 사용 (권장)

각 엔트리포인트는 자동으로 자신의 섹션을 감지합니다:

```python
from pillow_utils import ImageLoader, ImageOverlay
from ocr_utils import ImageOCR

# ConfigLoader가 자동으로 'pillow' 섹션 감지
loader = ImageLoader("configs/pillow.yaml")

# ConfigLoader가 자동으로 'ocr' 섹션 감지
ocr = ImageOCR("configs/ocr.yaml")

# ConfigLoader가 자동으로 'overlay' 섹션 감지
overlay = ImageOverlay("configs/overlay.yaml")
```

### 방법 2: 통합 파일 사용

하나의 파일에서 모든 설정 로드:

```python
from pillow_utils import ImageLoader, ImageOverlay
from ocr_utils import ImageOCR

# 동일한 파일이지만 각 엔트리포인트는 자신의 섹션만 로드
loader = ImageLoader("configs/unified.yaml")   # 'pillow' 섹션
ocr = ImageOCR("configs/unified.yaml")         # 'ocr' 섹션
overlay = ImageOverlay("configs/unified.yaml") # 'overlay' 섹션
```

### 방법 3: 명시적 섹션 지정

ConfigLoader를 직접 사용하여 명시적으로 섹션 지정:

```python
from modules.cfg_utils import ConfigLoader
from pillow_utils.policy import ImageLoaderPolicy, ImageOverlayPolicy

# 명시적 섹션 지정
config = ConfigLoader("configs/unified.yaml")
pillow_policy = config.as_model(ImageLoaderPolicy, section="pillow")
overlay_policy = config.as_model(ImageOverlayPolicy, section="overlay")

# 섹션을 dict로 추출
pillow_dict = config.get_section("pillow")
overlay_dict = config.get_section("overlay")
```

---

## 🔍 ConfigLoader 섹션 자동 감지

ConfigLoader는 다음 규칙으로 섹션을 자동 감지합니다:

### 감지 규칙

1. **모델 이름 기반 자동 감지**
   ```python
   ImageLoaderPolicy  → 'imageloaderpolicy', 'imageloader', 'loader'
   ImageOverlayPolicy → 'imageoverlaypolicy', 'imageoverlay', 'overlay'
   OcrPolicy          → 'ocrpolicy', 'ocr'
   ```

2. **Policy/Config 접미사 제거**
   ```python
   ImageLoaderPolicy  → 'imageloader'
   MyConfig           → 'my'
   ```

3. **Image 접두사 제거**
   ```python
   ImageLoader → 'loader'
   ImageOverlay → 'overlay'
   ```

### 실제 동작

```yaml
# unified.yaml
pillow:         # ← ImageLoaderPolicy가 자동 감지
  source: ...

overlay:        # ← ImageOverlayPolicy가 자동 감지
  source: ...

ocr:            # ← OcrPolicy가 자동 감지
  file: ...
```

```python
# 모두 자동으로 올바른 섹션 로드
loader = ImageLoader("unified.yaml")    # 'pillow' 섹션
overlay = ImageOverlay("unified.yaml")  # 'overlay' 섹션
ocr = ImageOCR("unified.yaml")          # 'ocr' 섹션
```

---

## 📁 파일 조직

### 현재 구조

```
configs/
├── pillow.yaml      # 개별: ImageLoader 설정
├── ocr.yaml         # 개별: ImageOCR 설정
├── overlay.yaml     # 개별: ImageOverlay 설정
└── unified.yaml     # 통합: 모든 엔트리포인트 설정
```

### 권장 사용 패턴

1. **개발/테스트**: 개별 파일 사용
   - 각 엔트리포인트 독립적으로 테스트
   - 설정 변경이 명확하게 분리됨

2. **프로덕션**: 통합 파일 사용
   - 한 곳에서 모든 설정 관리
   - 일관된 경로 및 설정 유지
   - 전체 파이프라인 설정 한눈에 파악

---

## 🎨 고급 사용법

### 런타임 오버라이드 (섹션 기반)

```python
from pillow_utils import ImageLoader

# YAML 섹션 로드 + 런타임 오버라이드
loader = ImageLoader(
    "configs/unified.yaml",  # 'pillow' 섹션 자동 감지
    save_copy=False,         # 런타임 오버라이드
    resize_to=[800, 600]
)
```

### 다중 설정 병합

```python
from modules.cfg_utils import ConfigLoader

# 여러 파일 병합 (나중 파일이 우선)
config = ConfigLoader([
    "configs/base.yaml",      # 기본 설정
    "configs/production.yaml" # 프로덕션 오버라이드
])

policy = config.as_model(ImageLoaderPolicy, section="pillow")
```

### 조건부 섹션 선택

```python
from modules.cfg_utils import ConfigLoader
import os

env = os.getenv("ENV", "dev")
config_file = f"configs/{env}.yaml"

# 환경별 다른 설정 파일 사용
loader = ImageLoader(config_file)
```

---

## ✅ 장점

### 1. **유연성**
- 개별 파일 또는 통합 파일 선택 가능
- 상황에 맞는 조직 구조 선택

### 2. **자동 감지**
- 섹션 이름을 명시하지 않아도 자동 감지
- 모델 이름 기반의 직관적인 매핑

### 3. **확장성**
- 새로운 엔트리포인트 추가 시 섹션만 추가
- 기존 설정에 영향 없음

### 4. **재사용성**
- 공통 설정을 통합 파일에서 관리
- 여러 엔트리포인트가 동일한 경로/디렉토리 공유 가능

---

## 📝 예제

### 전체 파이프라인 (통합 파일 사용)

```python
# configs/unified.yaml 하나로 전체 파이프라인 실행

from pillow_utils import ImageLoader, ImageOverlay
from ocr_utils import ImageOCR

config_file = "configs/unified.yaml"

# 1. 이미지 로드 및 전처리
loader = ImageLoader(config_file)  # 'pillow' 섹션
result = loader.run()

# 2. OCR 수행
ocr = ImageOCR(config_file)  # 'ocr' 섹션
items, metadata, _ = ocr.run()

# 3. 오버레이 렌더링
overlay = ImageOverlay(config_file)  # 'overlay' 섹션
final_path = overlay.run()

print(f"최종 결과: {final_path}")
```

---

**작성일**: 2025-10-14  
**상태**: ✅ 완료 및 검증 완료
