# OTO Script Implementation - Complete

## 📋 요약

`scripts/oto.py` - OCR → Translate → Overlay 파이프라인 스크립트 구현 완료.

**핵심 설계**: ENV 기반 ConfigLoader를 통해 모든 정책을 로드하고, Image 객체를 전달하며 SRP를 준수하는 파이프라인.

---

## ✅ 구현된 기능

### 1. 아키텍처 개요

```
ENV Variable (CASHOP_PATHS)
    ↓
paths.local.yaml
    ↓
configs_xloto → xloto.yaml (통합 설정)
    ↓
ConfigLoader (섹션별 로드)
    ├── image: ImageLoaderPolicy
    ├── ocr: ImageOCRPolicy
    ├── translate: dict (TranslatorPolicy)
    └── overlay: ImageOverlayPolicy
    ↓
Pipeline Execution
```

### 2. Pipeline Flow

```python
# Step 1: ImageLoader
loader = ImageLoader(cfg_like=policy)
loader_result = loader.run()
image = loader_result['image']  # PIL.Image

# Step 2: ImageOCR
ocr = ImageOCR(cfg_like=policy)
ocr_result = ocr.run(image=image)  # Image 전달 (FSO 중복 제거)
ocr_items = ocr_result['ocr_items']  # List[OCRItem]
preprocessed_image = ocr_result['image']

# Step 3: Translation (Script 책임)
original_texts = [item.text for item in ocr_items]
# TODO: Translator 구현 후 연동
translated_texts = {text: translate(text) for text in original_texts}

# Step 4: Conversion (Script 책임)
overlay_items = []
for item in ocr_items:
    translated = translated_texts.get(item.text, item.text)
    overlay_item = item.to_overlay_item(text_override=translated)
    overlay_items.append(overlay_item)

# Step 5: ImageOverlay
overlay = ImageOverlay(cfg_like=policy)
overlay_result = overlay.run(
    source_path=str(image_path),
    image=preprocessed_image,  # 전처리된 Image 전달
    overlay_items=overlay_items,  # 변환된 아이템
)
final_image = overlay_result['image']
```

---

## 🏗️ 클래스 구조

### OTO Class

```python
class OTO:
    """OCR → Translate → Overlay Pipeline
    
    Attributes:
        section: 설정 섹션명 (기본: "xloto")
        paths_env_key: 환경변수 키 (기본: "CASHOP_PATHS")
        log: LogManager logger
        
        # 로드된 설정
        paths_loader: ConfigLoader (paths.local.yaml)
        config_path: Path (xloto.yaml 경로)
        config_loader: ConfigLoader (xloto.yaml)
        
        # 로드된 정책
        image_loader_policy: ImageLoaderPolicy
        image_ocr_policy: ImageOCRPolicy
        translator_config: dict
        image_overlay_policy: ImageOverlayPolicy
    """
```

### Methods

#### `__init__(section, paths_env_key, log)`

Pipeline 초기화:
1. ENV 변수 검증
2. paths.local.yaml 로드
3. xloto.yaml 경로 추출
4. 각 섹션별 정책 로드

#### `_load_paths()`

ENV → paths.local.yaml 로드:
- `CASHOP_PATHS` 환경변수에서 paths.local.yaml 경로 가져오기
- ConfigLoader로 로드
- `configs_xloto` 키로 xloto.yaml 경로 추출
- 파일 존재 검증

#### `_load_policies()`

xloto.yaml → 각 섹션별 정책 로드:
- `image` 섹션 → `ImageLoaderPolicy`
- `ocr` 섹션 → `ImageOCRPolicy`
- `translate` 섹션 → `dict` (TranslatorPolicy 대기)
- `overlay` 섹션 → `ImageOverlayPolicy`

#### `process_image(image_path, **overrides)`

단일 이미지 처리:
1. ImageLoader: 이미지 로드
2. ImageOCR: OCR 실행 (Image 전달)
3. Translation: OCR 텍스트 번역 (Script)
4. Conversion: OCRItem → OverlayItemPolicy (Script)
5. ImageOverlay: 오버레이 렌더링 (Image, items 전달)

**Returns**:
```python
{
    'success': bool,
    'image_path': Path,
    'loader_result': Dict,
    'ocr_result': Dict,
    'translate_result': Dict[str, str],
    'overlay_result': Dict,
    'final_image': Optional[PIL.Image],
    'error': Optional[str]
}
```

#### `process_images(image_paths, **overrides)`

다중 이미지 일괄 처리:
- 각 이미지별로 `process_image()` 호출
- 성공/실패 집계
- 결과 리스트 반환

---

## 📁 설정 파일 구조

### 1. paths.local.yaml

```yaml
# M:\CALife\CAShop - 구매대행\_code\configs\paths.local.yaml

# Config Loader 파일 경로들
configs_loader_file_path:
  image: "${configs_loader_dir}/config_loader_image.yaml"
  ocr: "${configs_loader_dir}/config_loader_ocr.yaml"
  overlay: "${configs_loader_dir}/config_loader_overlay.yaml"
  translate: "${configs_loader_dir}/config_loader_translate.yaml"
```

**주의**: oto 설정 파일 경로는 각 config_loader 파일 안에 정의되어 있으므로 **paths.local.yaml에 중복 작성 불필요**

### 2. Config Loader 파일들 (configs/loader/)

각 모듈의 config_loader 파일이 실제 설정 파일 위치를 지정합니다.

#### config_loader_image.yaml

```yaml
config_loader:
  yaml:
    source_paths:
      path: "{configs_dir}/oto/image.yaml"  # 실제 설정 파일
      section: "image"  # 사용할 섹션
    # ... 기타 옵션
```

#### config_loader_ocr.yaml

```yaml
config_loader:
  yaml:
    source_paths:
      path: "{configs_dir}/oto/ocr.yaml"
      section: "ocr"
    # ... 기타 옵션
```

#### config_loader_overlay.yaml

```yaml
config_loader:
  yaml:
    source_paths:
      path: "{configs_dir}/oto/overlay.yaml"
      section: "overlay"
    # ... 기타 옵션
```

#### config_loader_translate.yaml

```yaml
config_loader:
  yaml:
    source_paths:
      path: "{configs_dir}/oto/translate.yaml"
      section: "translate"
    # ... 기타 옵션
```

### 3. 실제 설정 파일들 (configs/oto/)

#### image.yaml

```yaml
image:
  source:
    path: ""  # Runtime override
    must_exist: false
    convert_mode: "RGB"
  
  save:
    save_copy: false
    directory: "output/images"
    # ... FSO 정책
  
  meta:
    save_meta: false
  
  log:
    level: "INFO"
```

#### ocr.yaml

```yaml
ocr:
  source:
    path: ""  # Runtime override
    must_exist: true
  
  preprocess:
    max_width: 1920
  
  provider:
    backend: "paddleocr"
    langs: ["ch_sim", "en"]
    min_conf: 0.5
  
  save:
    save_copy: false
  
  meta:
    save_meta: true
  
  log:
    level: "INFO"
```

#### translate.yaml

```yaml
translate:
  source:
    text: []  # Runtime 제공
  
  provider:
    backend: "deepl"
    source_lang: "ZH"
    target_lang: "KO"
  
  log:
    level: "INFO"
```

#### overlay.yaml

```yaml
overlay:
  source:
    path: ""  # Runtime override
  
  items: []  # Runtime 제공
  
  background_opacity: 0.7
  
  save:
    save_copy: true
    directory: "output/overlay"
    suffix: "_translated"
  
  meta:
    save_meta: true
  
  log:
    level: "INFO"
```

---

## 🏗️ 로딩 아키텍처

```
ENV: CASHOP_PATHS
    ↓
paths.local.yaml
    ├─ configs_loader_file_path.image
    ├─ configs_loader_file_path.ocr
    ├─ configs_loader_file_path.overlay
    └─ configs_loader_file_path.translate
    ↓
Config Loader Files (configs/loader/)
    ├─ config_loader_image.yaml → source_paths: oto/image.yaml
    ├─ config_loader_ocr.yaml → source_paths: oto/ocr.yaml
    ├─ config_loader_overlay.yaml → source_paths: oto/overlay.yaml
    └─ config_loader_translate.yaml → source_paths: oto/translate.yaml
    ↓
Actual Config Files (configs/oto/)
    ├─ image.yaml
    ├─ ocr.yaml
    ├─ overlay.yaml
    └─ translate.yaml
    ↓
Policies
    ├─ ImageLoaderPolicy
    ├─ ImageOCRPolicy
    ├─ Translator Config (dict)
    └─ ImageOverlayPolicy
```

**장점:**
1. ✅ **중복 제거**: 설정 파일 경로가 config_loader에만 정의
2. ✅ **3-Tier Override**: BaseModel defaults → YAML → Runtime args
3. ✅ **Placeholder 지원**: `{configs_dir}` 자동 해석
4. ✅ **모듈 독립성**: 각 모듈이 자신의 config_loader를 통해 로드

---

## 🔧 사용 방법

### 1. 환경변수 설정

```powershell
# PowerShell
$env:CASHOP_PATHS = "M:\CALife\CAShop - 구매대행\_code\configs\paths.local.yaml"

# 영구 설정 (conda environment)
conda activate cashop
conda env config vars set CASHOP_PATHS="M:\CALife\CAShop - 구매대행\_code\configs\paths.local.yaml"
conda deactivate
conda activate cashop
```

### 2. Python에서 사용

```python
from scripts.oto import OTO

# 기본 사용
oto = OTO()  # section="xloto" 자동
result = oto.process_image("test.jpg")

if result['success']:
    print(f"✅ 성공: {result['overlay_result']['saved_path']}")
    final_image = result['final_image']
else:
    print(f"❌ 실패: {result['error']}")

# 다중 이미지
results = oto.process_images(["img1.jpg", "img2.jpg", "img3.jpg"])

# 정책 오버라이드
result = oto.process_image(
    "test.jpg",
    **{
        'save': {
            'save_copy': True,
            'directory': 'output/custom',
        }
    }
)
```

### 3. CLI 사용

```powershell
# 단일 이미지
python scripts/oto.py image.jpg

# 다중 이미지
python scripts/oto.py img1.jpg img2.jpg img3.jpg

# 정책 오버라이드
python scripts/oto.py --override save.save_copy=True image.jpg
python scripts/oto.py --override save.directory=output/custom image.jpg
python scripts/oto.py -o save.save_copy=True -o save.suffix=_final image.jpg
```

---

## 🎯 SRP 준수 확인

| 단계 | 모듈 | 책임 | Script 역할 |
|------|------|------|------------|
| 1 | ImageLoader | 이미지 로드/전처리 | 정책 주입, Image 수신 |
| 2 | ImageOCR | OCR 실행 | Image 전달, OCRItem 수신 |
| 3 | Translator | 텍스트 번역 | OCR 텍스트 전달, 번역 수신 |
| 4 | **Script** | **OCRItem → OverlayItemPolicy 변환** | **to_overlay_item() 호출** |
| 5 | ImageOverlay | 오버레이 렌더링 | Image + items 전달 |

**✅ 각 모듈은 단일 책임만 수행**  
**✅ Pipeline 조정은 Script가 담당**  
**✅ Image 객체 전달로 FSO 중복 제거**

---

## 🚀 다음 단계

### 1. Translator 통합 (우선순위 높음)

현재 임시 구현:
```python
# 임시: 역순 변환
translated_texts = {text: f"[번역] {text[::-1]}" for text in original_texts}
```

TODO:
```python
# Translator 구현
translator = Translator(cfg_like=self.translator_config)
translate_result = translator.run(texts=original_texts)
translated_texts = translate_result['translations']  # Dict[str, str]
```

### 2. 테스트 이미지 준비

- `_public/01.IMAGE/` 또는 `output/test_images/`에 샘플 이미지 배치
- 중국어/영어 혼합 텍스트 포함 권장

### 3. xloto.yaml 작성

**사용자가 작성 중** - 완료 대기:
- paths.local.yaml
- xloto.yaml (테스트용)

### 4. End-to-End 테스트

```powershell
# 환경변수 설정 확인
echo $env:CASHOP_PATHS

# 테스트 실행
python scripts/oto.py test_image.jpg

# 예상 출력:
# ================================================================================
# 🖼️  이미지 처리 시작: test_image.jpg
# ================================================================================
# [Step 1/5] ImageLoader: 이미지 로드 중...
#   ✅ 이미지 로드 완료: (800, 600) RGB
# [Step 2/5] ImageOCR: OCR 실행 중...
#   ✅ OCR 완료: 15개 텍스트 감지
#      [1] '你好世界' (conf=0.95, lang=ch_sim)
#      ...
# [Step 3/5] Translation: 번역 중...
#   ✅ 번역 완료: 15개
#      '你好世界' → '안녕 세계'
# [Step 4/5] Conversion: OCRItem → OverlayItemPolicy 변환 중...
#   ✅ 변환 완료: 15개 OverlayItemPolicy 생성
# [Step 5/5] ImageOverlay: 오버레이 렌더링 중...
#   ✅ 오버레이 완료: 15개 렌더링
#   💾 저장 완료: output/overlay/test_image_translated.png
# ================================================================================
# ✅ 이미지 처리 완료: test_image.jpg
# ================================================================================
```

### 5. 에러 핸들링 개선

- [ ] 부분 성공 처리 (일부 OCR/번역 실패 시)
- [ ] Graceful degradation
- [ ] 상세한 에러 리포트
- [ ] Retry 메커니즘

### 6. 성능 최적화

- [ ] Batch translation (여러 텍스트 한 번에)
- [ ] Image 객체 메모리 관리
- [ ] Parallel processing (다중 이미지)
- [ ] Cache 메커니즘

---

## 📝 주요 변경사항

### Before (Old Architecture)

```python
# 각 모듈이 파일을 반복 로드
loader.run(source_path)  # FSO 1
ocr.run(source_path)     # FSO 2 (중복!)
overlay.run(source_path) # FSO 3 (중복!)

# ImageOverlay가 OCRItem을 직접 처리 (SRP 위반)
overlay = ImageOverlay.from_ocr_items(ocr_items)
```

### After (New Architecture)

```python
# Image 객체 전달 (FSO 1회만)
loader_result = loader.run()
image = loader_result['image']

ocr_result = ocr.run(image=image)  # Image 전달
preprocessed_image = ocr_result['image']

overlay_result = overlay.run(
    image=preprocessed_image,  # Image 전달
    overlay_items=overlay_items  # Script에서 변환
)

# Script에서 변환 (SRP 준수)
overlay_items = [
    item.to_overlay_item(text_override=translated)
    for item, translated in zip(ocr_items, translations)
]
```

---

## 🎉 완료 상태

### ✅ 구현 완료

- [x] OTO 클래스 구조
- [x] ENV → paths.local.yaml → xloto.yaml 로드
- [x] ConfigLoader를 통한 정책 로드
- [x] Image 객체 전달 Pipeline
- [x] OCRItem → OverlayItemPolicy 변환 (Script)
- [x] process_image() 메서드
- [x] process_images() 메서드 (Batch)
- [x] CLI 인터페이스
- [x] LogManager 통합
- [x] 에러 핸들링
- [x] 문서화

### ⏳ 보류 (외부 의존)

- [ ] Translator 구현 (translate_utils 완성 후)
- [ ] xloto.yaml 작성 (사용자 작업 중)
- [ ] paths.local.yaml 작성 (사용자 작업 중)
- [ ] End-to-End 테스트 (설정 파일 완성 후)

### 📋 다음 우선순위

1. **사용자**: xloto.yaml + paths.local.yaml 작성
2. **사용자**: 테스트 이미지 준비
3. **개발**: Translator 통합
4. **테스트**: End-to-End 검증

---

**작성일**: 2025-10-16  
**작성자**: GitHub Copilot  
**버전**: 1.0  
**상태**: ✅ 구현 완료 (설정 파일 대기 중)
