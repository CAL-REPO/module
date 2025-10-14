# Entrypoint Configuration Files Summary

## ✅ 3개의 엔트리포인트 YAML 설정 파일 완료

모든 설정 파일은 `_code/configs/` 디렉토리에 위치하며, 각 엔트리포인트가 YAML 설정만으로도 완전히 작동할 수 있도록 모든 정책을 포함합니다.

---

## 1. 📄 pillow.yaml (ImageLoader - 1st Entrypoint)

**파일 위치**: `_code/configs/pillow.yaml`

**목적**: 이미지 로딩, 처리, 저장 및 메타데이터 생성

### 포함된 정책 (ImageLoaderPolicy):

#### source (ImageSourcePolicy)
- `path`: 소스 이미지 경로 (필수)
- `must_exist`: 파일 존재 여부 검증
- `convert_mode`: PIL 모드 변환 (예: "RGB", "RGBA", "L")

#### image (ImagePolicy)
- `save_copy`: 이미지 복사본 저장 여부
- `directory`: 저장 디렉토리
- `filename`: 파일명 (null = 자동 생성)
- `suffix`: 파일명 접미사 (기본값: "_processed")
- `format`: 출력 포맷 (null = 원본 유지)
- `quality`: JPEG/WebP 품질 (1-100)
- `ensure_unique`: 중복 방지 카운터 추가

#### meta (ImageMetaPolicy)
- `save_meta`: 메타데이터 JSON 저장 여부
- `directory`: 메타데이터 디렉토리
- `filename`: 메타데이터 파일명

#### processing (ImageProcessorPolicy)
- `resize_to`: 리사이즈 크기 [width, height]
- `blur_radius`: 가우시안 블러 반경
- `convert_mode`: 처리 후 모드 변환

### 사용 예시:
```python
from pillow_utils import ImageLoader

# YAML에서 로드
loader = ImageLoader("configs/pillow.yaml")
result = loader.run()

# 런타임 오버라이드
loader = ImageLoader("configs/pillow.yaml", 
                     save_copy=False, 
                     resize_to=[800, 600])
result = loader.run()

# 반환값: {"image": PIL.Image, "metadata": dict, 
#          "saved_image_path": Path, "saved_meta_path": Path}
```

---

## 2. 📄 ocr.yaml (ImageOCR - 2nd Entrypoint)

**파일 위치**: `_code/configs/ocr.yaml`

**목적**: 이미지 OCR 수행, 결과 저장 및 메타데이터 생성

### 포함된 정책 (OcrPolicy):

#### file (OcrFilePolicy)
- `file_path`: 소스 이미지 경로
- `save_img`: 처리된 이미지 저장 여부
- `save_dir`: 이미지 저장 디렉토리
- `save_suffix`: 파일명 접미사
- `save_ocr_meta`: OCR 메타데이터 저장 여부
- `ocr_meta_dir`: 메타데이터 디렉토리
- `ocr_meta_name`: 메타데이터 파일명

#### provider (OcrProviderPolicy)
- `provider`: OCR 제공자 ("paddle")
- `langs`: 언어 코드 리스트 (["ch_sim", "en"])
- `min_conf`: 최소 신뢰도 임계값 (0.0-1.0)
- `paddle_device`: 디바이스 ("gpu" or "cpu")
- `paddle_use_angle_cls`: 텍스트 각도 분류 활성화
- `paddle_instance`: 내부 캐시된 인스턴스

#### preprocess (OcrPreprocessPolicy)
- `resized`: 리사이즈 수행 여부
- `max_width`: 최대 너비 (null = 리사이즈 안 함)

#### 기타
- `debug`: 디버그 모드 활성화
- `source`: ImageSourcePolicy 통합
- `target`: ImagePolicy 통합
- `meta`: ImageMetaPolicy 통합
- `log`: LogPolicy 통합 (상세 로깅 설정)

### 사용 예시:
```python
from ocr_utils import ImageOCR

# YAML에서 로드
ocr = ImageOCR("configs/ocr.yaml")
items, metadata, saved_path = ocr.run()

# 런타임 오버라이드
ocr = ImageOCR("configs/ocr.yaml", 
               langs=["en"], 
               min_conf=0.7)
items, metadata, saved_path = ocr.run()
```

---

## 3. 📄 overlay.yaml (ImageOverlay - 3rd Entrypoint)

**파일 위치**: `_code/configs/overlay.yaml`

**목적**: 이미지에 텍스트 오버레이 렌더링

### 포함된 정책 (ImageOverlayPolicy):

#### source (ImageSourcePolicy)
- `path`: 소스 이미지 경로
- `must_exist`: 파일 존재 여부 검증
- `convert_mode`: PIL 모드 변환

#### output (ImagePolicy)
- `save_copy`: 오버레이된 이미지 저장 여부
- `directory`: 저장 디렉토리
- `filename`: 파일명 (null = 자동 생성)
- `suffix`: 파일명 접미사 (기본값: "_overlay")
- `format`: 출력 포맷
- `quality`: JPEG/WebP 품질
- `ensure_unique`: 중복 방지 카운터 추가

#### meta (ImageMetaPolicy)
- `save_meta`: 메타데이터 저장 여부
- `directory`: 메타데이터 디렉토리
- `filename`: 메타데이터 파일명

#### font (FontPolicy)
- `family`: 폰트 경로 또는 이름
- `size`: 폰트 크기 (픽셀)
- `fill`: 텍스트 색상 (hex: "#FF0000")
- `stroke_fill`: 테두리 색상
- `stroke_width`: 테두리 두께

#### 오버레이 설정
- `background_opacity`: 배경 투명도 (0.0-1.0)

#### texts (List[OverlayTextPolicy])
각 텍스트 오버레이 항목:
- `text`: 오버레이할 텍스트
- `polygon`: 텍스트 배치 영역 좌표 [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
- `font`: 개별 폰트 설정 (FontPolicy 오버라이드)
- `anchor`: PIL 앵커 포인트 ("mm", "lt", etc.)
- `offset`: 위치 오프셋 [dx, dy]
- `max_width_ratio`: 최대 텍스트 너비 비율 (0.0-1.0)

### 사용 예시:
```python
from pillow_utils import ImageOverlay

# YAML에서 로드 (2개의 샘플 텍스트 포함)
overlay = ImageOverlay("configs/overlay.yaml")
result_path = overlay.run()

# 런타임 오버라이드
from pillow_utils.policy import ImageOverlayPolicy, OverlayTextPolicy

texts = [
    OverlayTextPolicy(
        text="새 텍스트",
        polygon=[[50, 50], [300, 50], [300, 100], [50, 100]]
    )
]
overlay = ImageOverlay("configs/overlay.yaml", texts=texts)
result_path = overlay.run()

# 반환값: Path (오버레이된 이미지 경로)
```

---

## 공통 특징

### 1. **YAML 기반 설정**
- 모든 엔트리포인트는 YAML 파일만으로 완전히 설정 가능
- 코드 수정 없이 설정 변경 가능

### 2. **런타임 오버라이드**
- 모든 필드는 `**kwargs`를 통한 런타임 오버라이드 지원
- 우선순위: BaseModel 기본값 → YAML → **kwargs

### 3. **Pydantic 검증**
- 모든 설정은 Pydantic BaseModel로 검증
- 타입 안전성 및 기본값 제공

### 4. **FSO_utils 통합**
- 파일 경로 및 이름 생성에 FSO_utils 활용
- 안전한 파일명 생성 및 중복 방지

### 5. **경로 유틸리티**
- `path_utils.downloads()` 기본 디렉토리 제공
- null 값 사용 시 자동으로 적절한 기본 경로 설정

---

## 설정 파일 검증

✅ **모든 YAML 파일 lint 통과 (0 errors)**
- pillow.yaml: ✅ No errors
- ocr.yaml: ✅ No errors  
- overlay.yaml: ✅ No errors

---

## 워크플로우 예시

### 전체 파이프라인 (3개 엔트리포인트 연결)

```python
from pillow_utils import ImageLoader, ImageOverlay
from ocr_utils import ImageOCR

# 1단계: 이미지 로딩 및 전처리
loader = ImageLoader("configs/pillow.yaml", resize_to=[1200, 900])
result = loader.run()
processed_image = result["image"]
processed_path = result["saved_image_path"]

# 2단계: OCR 수행
ocr = ImageOCR("configs/ocr.yaml", file_path=processed_path)
ocr_items, ocr_meta, _ = ocr.run()

# 3단계: 오버레이 렌더링 (translate 모듈 통합 대기)
# 현재는 수동 좌표 지정, 추후 translate 모듈에서 자동 변환
overlay = ImageOverlay("configs/overlay.yaml", 
                       source={"path": processed_path})
final_path = overlay.run()

print(f"최종 결과: {final_path}")
```

---

## 추가 개선 사항 (향후)

1. **translate 모듈 통합**
   - OCR 결과 → 번역 → 좌표 변환 → 오버레이 자동화
   - 새로운 엔트리포인트: `TranslateOverlay`

2. **로깅 정책 통합**
   - 현재 LogPolicy는 ImageLoaderPolicy에 미포함
   - 향후 통합 시 pillow.yaml에 log 섹션 추가 필요

3. **더 많은 예제 추가**
   - 각 YAML 파일에 다양한 사용 사례 주석 추가
   - 템플릿 파일 세트 제공

---

## 파일 요약

| 파일 | 엔트리포인트 | 주요 기능 | 반환값 |
|------|-------------|----------|--------|
| `pillow.yaml` | ImageLoader | 이미지 로딩/처리/저장 | dict (image, metadata, paths) |
| `ocr.yaml` | ImageOCR | OCR 수행 | tuple (items, metadata, path) |
| `overlay.yaml` | ImageOverlay | 텍스트 오버레이 | Path (오버레이 이미지) |

---

**작성일**: 2025-10-14  
**상태**: ✅ 완료 및 검증 완료
