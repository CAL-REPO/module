# Adapter/EntryPoint 패턴 가이드 (image_utils)

## 개요

`image_utils`는 `translate_utils`의 **Adapter/EntryPoint 패턴**을 따라 재설계되었습니다.

### 핵심 원칙

1. **Adapter**: Standalone 실행 가능, Policy에 `source` 없음, `run(data)`에서 데이터 받음
2. **EntryPoint**: Policy에 `source` 포함, source 로딩 후 adapter에 전달, 결과 저장

---

## 1. Adapter 패턴 (translate_utils의 Translate.py)

### 특징
- **Policy에 source 없음**: 데이터 소스 정보를 Policy에서 제외
- **`__init__(cfg_like, log_manager, **overrides)`**: Policy와 로거만 받음
- **`run(data)`**: 실행 시점에 데이터를 파라미터로 받음
- **Standalone 사용 가능**: source 없이도 단독 실행 가능

### 예시: ImageLoad (adapter/load.py)

```python
from image_utils.adapter.load import ImageLoad
from image_utils.core.policy import ImageLoadPolicy

# Policy (source 없음)
policy = ImageLoadPolicy(
    save={"save_copy": False},
    meta={"save_meta": False},
    process={"resize_to": None}
)

# Adapter 생성
adapter = ImageLoad(cfg_like=policy)

# run()에서 이미지 받기
from PIL import Image
image = Image.open("test.jpg")
result = adapter.run(source=image)  # 또는 run(source="test.jpg")
```

### image_utils Adapters

| Adapter | Policy | run() 시그니처 |
|---------|--------|----------------|
| `ImageLoad` | `ImageLoadPolicy` | `run(source: Union[Image, Path, str])` |
| `ImageTextRecognize` | `ImageTextRecognizePolicy` | `run(image: Image)` |
| `ImageOverlay` | `ImageOverlayPolicy` | `run(image: Image, items: List[OverlayItemPolicy])` |

---

## 2. EntryPoint 패턴 (translate_utils의 Translator.py)

### 특징
- **Policy에 source 포함**: 데이터 소스를 Policy에 정의
- **source 로딩**: EntryPoint가 직접 source에서 데이터 로드
- **adapter.run(data) 호출**: 로드한 데이터를 adapter에 전달
- **결과 저장**: 결과를 파일로 저장하거나 반환

### 예시: ImageLoader (entry_point/loader.py)

```python
from image_utils.entry_point.loader import ImageLoader
from image_utils.core.policy import ImageLoaderPolicy

# Policy (source 포함)
policy = ImageLoaderPolicy(
    source={
        "path": "test.jpg",
        "glob_patterns": None,
        "must_exist": True,
    },
    image_load={
        "save": {"save_copy": True, "target_dir": "output"},
        "meta": {"save_meta": True},
        "process": {"resize_to": [800, 600]}
    }
)

# EntryPoint 생성 및 실행
loader = ImageLoader(cfg_like=policy)
result = loader.run()

# result["image"] → PIL Image 객체
# result["metadata"] → 이미지 메타데이터
```

### image_utils EntryPoints

| EntryPoint | Policy | 내부 Adapter | 역할 |
|-----------|--------|-------------|------|
| `ImageLoader` | `ImageLoaderPolicy` | `ImageLoad` | source 로드 → 이미지 처리 |
| `ImageTextRecognizer` | `ImageTextRecognizerPolicy` | `ImageTextRecognize` | source 로드 → OCR 실행 |
| `ImageOverlayer` | `ImageOverlayerPolicy` | `ImageOverlay` | source 로드 → 오버레이 렌더링 |

---

## 3. Policy 구조

### Adapter Policy (source 없음)

```python
class ImageLoadPolicy(BaseModel):
    name: str = "image_load"
    save: ImageSavePolicy
    meta: ImageMetaPolicy
    process: ImageProcessPolicy
    log: Optional[LogPolicy] = None
```

### EntryPoint Policy (source 포함)

```python
class ImageLoaderPolicy(BaseModel):
    name: str = "image_loader"
    source: ImageSourcePolicy  # ← source 추가
    image_load: ImageLoadPolicy  # ← Adapter Policy 포함
```

---

## 4. 사용 시나리오

### Scenario 1: Standalone Adapter 사용

**언제 사용**: 
- 이미 메모리에 이미지가 있을 때
- 파이프라인 중간 단계로 사용할 때
- source 로딩 없이 직접 데이터를 전달하고 싶을 때

```python
from image_utils.adapter.load import ImageLoad
from image_utils.adapter.text_recognize import ImageTextRecognize
from image_utils.adapter.overlay import ImageOverlay
from PIL import Image

# 1. 이미지 로드
image = Image.open("test.jpg")

# 2. ImageLoad adapter로 처리
load_adapter = ImageLoad(cfg_like={"save": {"save_copy": False}})
processed = load_adapter.run(source=image)

# 3. OCR adapter로 텍스트 인식
ocr_adapter = ImageTextRecognize(cfg_like={"provider": {"langs": ["ch", "en"]}})
ocr_items = ocr_adapter.run(image=processed["image"])

# 4. Overlay adapter로 오버레이
overlay_adapter = ImageOverlay(cfg_like={"items": [], "background_opacity": 0.7})
overlaid = overlay_adapter.run(image=processed["image"], items=ocr_items[:3])
```

### Scenario 2: EntryPoint 사용 (파일에서 로드)

**언제 사용**:
- 파일/URL에서 이미지를 로드해야 할 때
- 설정 파일(YAML)로 전체 파이프라인을 관리할 때
- source 로딩 + 처리를 한 번에 수행하고 싶을 때

```python
from image_utils.entry_point.loader import ImageLoader
from image_utils.entry_point.text_recognizer import ImageTextRecognizer
from image_utils.entry_point.overlayer import ImageOverlayer

# 1. ImageLoader로 파일 로드 + 처리
loader = ImageLoader(cfg_like={
    "source": {"path": "test.jpg"},
    "image_load": {"save": {"save_copy": True}}
})
loaded = loader.run()

# 2. ImageTextRecognizer로 파일 로드 + OCR
recognizer = ImageTextRecognizer(cfg_like={
    "source": {"path": "test.jpg"},
    "text_recognize": {"provider": {"langs": ["ch", "en"]}}
})
ocr_result = recognizer.run()

# 3. ImageOverlayer로 파일 로드 + 오버레이
overlayer = ImageOverlayer(cfg_like={
    "source": {"path": "test.jpg"},
    "overlay": {"items": ocr_result["items"][:5]}
})
overlay_result = overlayer.run()
```

### Scenario 3: YAML 설정 파일 사용

**config.yaml**:
```yaml
image_loader:
  source:
    path: "input/test.jpg"
  image_load:
    save:
      save_copy: true
      target_dir: "output"
    process:
      resize_to: [800, 600]

text_recognizer:
  source:
    path: "input/test.jpg"
  text_recognize:
    provider:
      langs: ["ch", "en"]
      min_conf: 0.6
```

**Python 코드**:
```python
from cfg_utils import ConfigLoader
from image_utils.entry_point.loader import ImageLoader
from image_utils.entry_point.text_recognizer import ImageTextRecognizer

# YAML 로드
config = ConfigLoader("config.yaml")

# EntryPoint 실행
loader = ImageLoader(cfg_like=config["image_loader"])
loader.run()

recognizer = ImageTextRecognizer(cfg_like=config["text_recognizer"])
recognizer.run()
```

---

## 5. translate_utils vs image_utils 비교

| 항목 | translate_utils | image_utils |
|------|----------------|-------------|
| **Adapter** | `Translate` | `ImageLoad`, `ImageTextRecognize`, `ImageOverlay` |
| **Adapter Policy** | `TranslatePolicy` (source 없음) | `ImageLoadPolicy`, `ImageTextRecognizePolicy`, `ImageOverlayPolicy` |
| **EntryPoint** | `Translator` | `ImageLoader`, `ImageTextRecognizer`, `ImageOverlayer` |
| **EntryPoint Policy** | `TranslatorPolicy` (source 포함) | `ImageLoaderPolicy`, `ImageTextRecognizerPolicy`, `ImageOverlayerPolicy` |
| **run() 시그니처** | `run(data: str)` | `run(source)`, `run(image)`, `run(image, items)` |

---

## 6. 마이그레이션 가이드

### Deprecated Aliases (제거됨 ⚠️)

다음 alias들은 제거되었습니다. 정식 이름을 사용하세요:

| Deprecated | 사용할 이름 |
|-----------|-----------|
| `ImageOCRPolicy` | `ImageTextRecognizerPolicy` |
| `ImageProcessorPolicy` | `ImageProcessPolicy` |
| `OverlayTextPolicy` | `OverlayItemPolicy` |

### 기존 코드 수정 예시

**Before** (deprecated):
```python
from image_utils import ImageOCRPolicy

policy = ImageOCRPolicy(
    source={"path": "test.jpg"},
    provider={"langs": ["ch", "en"]}
)
```

**After** (정식):
```python
from image_utils import ImageTextRecognizerPolicy

policy = ImageTextRecognizerPolicy(
    source={"path": "test.jpg"},
    text_recognize={
        "provider": {"langs": ["ch", "en"]}
    }
)
```

---

## 7. 테스트

### 개별 테스트
```bash
python test_imageload_adapter.py
python test_imageloader_entrypoint.py
python test_text_recognize_adapter.py
python test_text_recognizer_entrypoint.py
python test_overlay_adapter.py
python test_overlayer_entrypoint.py
```

### 통합 테스트
```bash
python test_integration.py
```

---

## 8. 참고 자료

- **translate_utils**: `modules/translate_utils/adapter/translate.py`, `modules/translate_utils/entry_point/translator.py`
- **image_utils 구현**: `modules/image_utils/adapter/`, `modules/image_utils/entry_point/`
- **Policy 정의**: `modules/image_utils/core/policy.py`

---

## 작성일
2025-10-19

## 작성자
GitHub Copilot (CAShop - 구매대행 프로젝트)
