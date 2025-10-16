# Image Pipeline Refactoring - Complete

## 📋 요약

Image Utils 모듈의 파이프라인 구조를 SRP(Single Responsibility Principle) 기준에 맞게 리팩토링 완료.

**목표**: ImageLoader → ImageOCR → Translator → ImageOverlay 파이프라인에서 각 모듈이 단일 책임만 수행하도록 개선

---

## ✅ 완료된 작업

### 1. OverlayTextPolicy → OverlayItemPolicy 리팩토링

**파일**: `modules/image_utils/core/policy.py`

#### 변경사항:
- `OverlayTextPolicy` → `OverlayItemPolicy`로 클래스명 변경
- OCRItem 호환 필드 추가 (optional):
  - `conf`: OCR confidence score
  - `bbox`: OCR bounding box
  - `angle_deg`: OCR text angle
  - `lang`: OCR language code

- `ImageOverlayPolicy.texts` → `ImageOverlayPolicy.items`로 필드명 변경

#### 이유:
- 더 범용적인 네이밍 (텍스트만이 아닌 오버레이 아이템 전반)
- OCRItem과의 seamless integration을 위한 필드 호환성 확보
- Pipeline scripts에서의 변환 로직 단순화

#### Backward Compatibility:
```python
OverlayTextPolicy = OverlayItemPolicy  # Deprecated alias
```

---

### 2. OCRItem.to_overlay_item() 변환 메서드 추가

**파일**: `modules/image_utils/core/models.py`

#### 추가된 메서드:
```python
def to_overlay_item(
    self, 
    text_override: Optional[str] = None, 
    font_policy: Optional["FontPolicy"] = None
) -> "OverlayItemPolicy":
    """Convert OCRItem to OverlayItemPolicy for pipeline scripts.
    
    Args:
        text_override: Override text (e.g., translated text)
        font_policy: Override font policy
    
    Returns:
        OverlayItemPolicy instance
    """
    from .policy import OverlayItemPolicy
    
    # quad → polygon 변환
    polygon = [(p[0], p[1]) for p in self.quad]
    
    return OverlayItemPolicy(
        text=text_override or self.text,
        polygon=polygon,
        font=font_policy or FontPolicy(),
        conf=self.conf,
        bbox=self.bbox,
        angle_deg=self.angle_deg,
        lang=self.lang,
    )
```

#### 이유:
- OCRItem → OverlayItemPolicy 변환을 pipeline scripts에서 쉽게 수행
- SRP 준수: OCRItem은 변환 메서드만 제공, 번역 로직은 포함하지 않음
- `text_override` 파라미터로 번역된 텍스트를 주입 가능

---

### 3. ImageLoader.run() Image 객체 반환 추가

**파일**: `modules/image_utils/services/image_loader.py`

#### 변경사항:
```python
def run(self, source_override: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """이미지 로드, 처리 및 저장.
    
    Returns:
        {
            "success": bool,
            "image": PIL.Image.Image,  # ← 추가
            "original_path": Path,
            "saved_path": Optional[Path],
            ...
        }
    """
```

#### 이유:
- Pipeline에서 Image 객체를 다음 단계로 전달
- 불필요한 FSO 접근 제거 (ImageOCR가 파일을 다시 로드할 필요 없음)
- Memory efficiency 향상

---

### 4. ImageOCR.run() Image 객체 입력/출력 추가

**파일**: `modules/image_utils/services/image_ocr.py`

#### 변경사항:
```python
def run(
    self,
    source_override: Optional[Union[str, Path]] = None,
    image: Optional[Image.Image] = None,  # ← 추가
) -> Dict[str, Any]:
    """OCR 실행 및 결과 처리.
    
    Args:
        source_override: 소스 경로 오버라이드 (image가 None일 때만 사용)
        image: PIL Image 객체 (제공되면 파일 로딩 없이 바로 사용)
    
    Returns:
        {
            "success": bool,
            "image": PIL.Image.Image,  # ← 전처리된 이미지 반환
            "ocr_items": List[OCRItem],
            ...
        }
    """
```

#### 이유:
- ImageLoader에서 전달받은 Image 객체 활용
- OCR 전처리된 이미지를 다음 단계(Overlay)로 전달
- Pipeline chaining 지원

---

### 5. ImageOverlay.run() 인터페이스 개선 (SRP)

**파일**: `modules/image_utils/services/image_overlay.py`

#### 변경사항:

**Before** (SRP 위반):
```python
def run(
    self,
    source_override: Optional[Union[str, Path]] = None,
    texts_override: Optional[List[OverlayTextPolicy]] = None,
) -> Dict[str, Any]:
    # ImageOverlay가 OCRItem을 알고 있었음 (from_ocr_items factory)
```

**After** (SRP 준수):
```python
def run(
    self,
    source_path: Union[str, Path],
    image: Optional[Image.Image] = None,
    overlay_items: Optional[List[OverlayItemPolicy]] = None,
) -> Dict[str, Any]:
    """텍스트 오버레이 실행.
    
    SRP: ImageOverlay는 주어진 overlay_items를 이미지에 렌더링하는 것만 담당.
    OCR → Translation → OverlayItem 변환은 pipeline scripts에서 처리.
    
    Args:
        source_path: 소스 경로 (메타데이터 저장용)
        image: PIL Image 객체 (None이면 source_path에서 로드)
        overlay_items: OverlayItemPolicy 리스트 (None이면 policy.items 사용)
    
    Returns:
        {
            "success": bool,
            "source_path": Path,
            "saved_path": Optional[Path],
            "overlaid_items": int,
            "image": Optional[Image.Image],  # ← 오버레이된 이미지
            ...
        }
    """
```

#### 주요 변경:
1. **OCRItem 인식 제거**: ImageOverlay는 OCRItem을 모름
2. **OverlayItemPolicy만 처리**: 깔끔한 인터페이스
3. **Image 객체 입출력**: Pipeline chaining 지원
4. **from_ocr_items() 제거**: SRP 위반이므로 삭제

#### 이유:
- **SRP 준수**: ImageOverlay는 "주어진 아이템을 렌더링"하는 것만 책임
- **OCR → Translation → Conversion 로직**: Pipeline scripts에서 처리
- **모듈 간 의존성 제거**: ImageOverlay가 OCRItem을 몰라도 됨

---

### 6. Pipeline 테스트 스크립트 작성

**파일**: `tests/test_image_pipeline.py`

#### 구조:
```python
def test_pipeline(image_path: Path):
    # Step 1: ImageLoader
    loader = ImageLoader()
    loader_result = loader.run(source_override=str(image_path))
    image = loader_result["image"]
    
    # Step 2: ImageOCR
    ocr = ImageOCR()
    ocr_result = ocr.run(source_override=str(image_path), image=image)
    ocr_items = ocr_result["ocr_items"]
    preprocessed_image = ocr_result["image"]
    
    # Step 3: Translation (script responsibility)
    translated_texts = {}
    for item in ocr_items:
        translated_texts[item.text] = translate(item.text)  # Your logic
    
    # Step 4: Conversion (script responsibility)
    overlay_items = []
    for item in ocr_items:
        translated = translated_texts.get(item.text, item.text)
        overlay_item = item.to_overlay_item(text_override=translated)
        overlay_items.append(overlay_item)
    
    # Step 5: ImageOverlay
    overlay = ImageOverlay()
    overlay_result = overlay.run(
        source_path=str(image_path),
        image=preprocessed_image,
        overlay_items=overlay_items,
    )
    final_image = overlay_result["image"]
```

#### 검증 항목:
- ✅ Image 객체가 단계 간 전달되는지
- ✅ OCRItem → OverlayItemPolicy 변환이 작동하는지
- ✅ 각 모듈이 단일 책임만 수행하는지
- ✅ Pipeline이 end-to-end로 동작하는지

---

## 🎯 달성된 목표

### SRP (Single Responsibility Principle) 준수

| 모듈 | 책임 | OCR 인식 | Translation 인식 |
|------|------|----------|------------------|
| **ImageLoader** | 이미지 로드 및 전처리 | ❌ | ❌ |
| **ImageOCR** | OCR 실행 및 결과 생성 | ✅ (자기 자신) | ❌ |
| **ImageOverlay** | 주어진 아이템 렌더링 | ❌ | ❌ |
| **Pipeline Script** | OCR → Translation → Conversion 조정 | ✅ | ✅ |

### Pipeline Chaining

```
ImageLoader.run()
    ↓ Image object
ImageOCR.run(image=...)
    ↓ OCRItem[], preprocessed Image
[Script: Translation]
    ↓ translated_texts{}
[Script: Conversion via to_overlay_item()]
    ↓ OverlayItemPolicy[]
ImageOverlay.run(image=..., overlay_items=...)
    ↓ Final Image
```

### 제거된 중복

- ❌ ImageOverlay에서 OCRItem 처리 로직 제거
- ❌ `from_ocr_items()` factory method 제거 (SRP 위반)
- ❌ 각 모듈에서 파일을 반복적으로 로드하는 로직 제거

---

## 📦 영향 받는 파일

### Core Models & Policies
- `modules/image_utils/core/models.py` - OCRItem.to_overlay_item() 추가
- `modules/image_utils/core/policy.py` - OverlayItemPolicy 리팩토링

### Services
- `modules/image_utils/services/image_loader.py` - Image 반환 추가
- `modules/image_utils/services/image_ocr.py` - Image 입출력 추가
- `modules/image_utils/services/image_overlay.py` - 인터페이스 개선 (SRP)

### Tests
- `tests/test_image_pipeline.py` - 새 아키텍처 검증 스크립트

---

## 🔄 Migration Guide

### 기존 코드 (Before)

```python
# Old: ImageOverlay가 OCRItem을 직접 처리
overlay = ImageOverlay.from_ocr_items(
    source_path="image.jpg",
    ocr_items=ocr_items,
    background_opacity=0.7,
)
result = overlay.run()
```

### 새 코드 (After)

```python
# New: Pipeline script에서 변환 처리
# Step 1: OCR
ocr = ImageOCR()
ocr_result = ocr.run(source_override="image.jpg")
ocr_items = ocr_result["ocr_items"]

# Step 2: Translation (your logic)
translated_texts = translate_batch([item.text for item in ocr_items])

# Step 3: Conversion
overlay_items = []
for item, translated in zip(ocr_items, translated_texts):
    overlay_item = item.to_overlay_item(text_override=translated)
    overlay_items.append(overlay_item)

# Step 4: Overlay
overlay = ImageOverlay()
result = overlay.run(
    source_path="image.jpg",
    image=ocr_result["image"],
    overlay_items=overlay_items,
)
```

---

## 🧪 테스트 방법

```powershell
# 환경 설정
cd "M:\CALife\CAShop - 구매대행\_code"

# Python 환경 활성화
conda activate cashop  # 또는 적절한 환경

# 테스트 실행
python tests/test_image_pipeline.py
```

### 예상 출력:
```
================================================================================
Image Processing Pipeline Test - New Architecture
================================================================================
Test image: M:\...\sample.jpg

[Step 1/5] ImageLoader: Load and preprocess image
--------------------------------------------------------------------------------
✅ Image loaded: (800, 600) RGB
   Source: M:\...\sample.jpg

[Step 2/5] ImageOCR: Detect text in image
--------------------------------------------------------------------------------
✅ OCR completed: 15 text items detected
   [1] 'Hello World' (conf=0.95, lang=en)
   ...

[Step 3/5] Translation: Translate OCR results (script responsibility)
--------------------------------------------------------------------------------
✅ Translation completed: 15 texts translated
   'Hello World' → '[TR] dlroW olleH'
   ...

[Step 4/5] Conversion: OCRItem → OverlayItemPolicy (script responsibility)
--------------------------------------------------------------------------------
✅ Conversion completed: 15 overlay items created
   [1] '[TR] dlroW olleH' polygon=[(10, 20), (100, 20)]...

[Step 5/5] ImageOverlay: Render overlay items on image
--------------------------------------------------------------------------------
✅ Overlay completed: 15 items rendered
   Image size: (800, 600)

================================================================================
Pipeline Test Summary
================================================================================
✅ All steps completed successfully!
   1. Loaded image: (800, 600) RGB
   2. Detected texts: 15
   3. Translated texts: 15
   4. Converted items: 15
   5. Overlaid items: 15
   → Final image: (800, 600) RGB
================================================================================

✨ Pipeline architecture validated:
   - SRP compliance: Each module does one thing
   - Image objects passed (no redundant FSO)
   - Conversion logic in script (not in modules)
================================================================================
```

---

## 📝 향후 작업

### 1. Translation 모듈 통합
- `translate_utils` 연동
- Batch translation 지원
- Cache 메커니즘

### 2. from_config 패턴 적용
- 모든 entrypoint에 `from_config()` classmethod 추가
- ConfigLoader 기능 보존 (source_paths, deep merge, etc.)

### 3. 성능 최적화
- Image 객체 메모리 관리
- Parallel processing for batch operations
- GPU acceleration for OCR (optional)

### 4. Error Handling 강화
- Graceful degradation
- Partial success 처리
- Detailed error reporting

---

## 🎉 결론

### 달성 사항:
✅ SRP 준수 - 각 모듈이 단일 책임만 수행  
✅ Pipeline Chaining - Image 객체 전달로 효율성 증대  
✅ 모듈 간 결합도 감소 - 깔끔한 인터페이스  
✅ 확장성 향상 - 새로운 처리 단계 추가 용이  
✅ 테스트 가능성 증대 - 각 단계 독립적으로 테스트 가능  

### 설계 원칙:
- **Single Responsibility**: 각 모듈은 한 가지만 잘한다
- **Dependency Inversion**: 상위 수준(scripts)이 하위 수준(modules) 조정
- **Open/Closed**: 확장에는 열려있고 수정에는 닫혀있음
- **Interface Segregation**: 필요한 인터페이스만 노출

---

**작성일**: 2025-10-16  
**작성자**: GitHub Copilot  
**버전**: 1.0
