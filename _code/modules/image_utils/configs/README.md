# Image Utils Configuration Examples

이 디렉토리는 `image_utils` 모듈의 설정 파일 예제를 포함합니다.

## 📁 파일 구조

```
config/
├── README.md                      # 이 파일
├── image_loader_full.yaml        # ImageLoader 전체 옵션
├── image_loader_simple.yaml      # ImageLoader 간단 예제
├── image_ocr_full.yaml            # ImageOCR 전체 옵션
├── image_ocr_simple.yaml          # ImageOCR 간단 예제
├── image_overlay_full.yaml        # ImageOverlay 전체 옵션
└── image_overlay_simple.yaml      # ImageOverlay 간단 예제
```

## 🎯 사용 방법

### 1. Simple 버전 (권장)
실제 프로젝트에서 자주 사용하는 옵션만 포함한 간단한 예제입니다.

```python
from image_utils import ImageLoader

# YAML 파일로 초기화
loader = ImageLoader("modules/image_utils/config/image_loader_simple.yaml")
result = loader.run()
```

### 2. Full 버전
모든 가능한 옵션을 확인하고 싶을 때 참고하세요.

```python
from image_utils import ImageLoader

# 전체 옵션 YAML 파일
loader = ImageLoader("modules/image_utils/config/image_loader_full.yaml")
result = loader.run()
```

### 3. Runtime Override
YAML 설정을 기본으로 하고 특정 값만 런타임에 변경:

```python
from image_utils import ImageLoader

loader = ImageLoader(
    "config/image_loader_simple.yaml",
    save={"name": {"suffix": "_custom"}},  # suffix만 변경
    process={"resize_to": [1024, 768]}      # 리사이즈 크기 변경
)
result = loader.run()
```

## 📋 주요 정책 설명

### ImageLoader
- **source**: 소스 이미지 경로 및 로드 옵션
- **save**: 이미지 저장 설정 (FSO 기반)
- **meta**: 메타데이터 저장 설정
- **process**: 리사이즈, 블러 등 이미지 처리
- **log**: 로그 설정

### ImageOCR
- **source**: 소스 이미지 경로 및 로드 옵션
- **provider**: OCR 제공자 (PaddleOCR 등) 설정
- **preprocess**: OCR 전처리 (리사이즈 등)
- **postprocess**: OCR 후처리 (텍스트 정제, 중복 제거)
- **save**: 이미지 저장 설정 (선택)
- **meta**: OCR 결과 JSON 저장
- **log**: 로그 설정

### ImageOverlay
- **source**: 소스 이미지 경로 및 로드 옵션
- **texts**: 텍스트 오버레이 목록 (좌표, 폰트 등)
- **background_opacity**: 배경 투명도
- **save**: 오버레이된 이미지 저장
- **meta**: 오버레이 정보 저장
- **log**: 로그 설정

## 🔧 FSO 통합

`save`와 `meta` 정책은 `fso_utils`와 통합되어 있습니다:

### FSONamePolicy (파일명 정책)
- **suffix**: 파일명 접미사 (예: `_processed`)
- **tail_mode**: 자동 tail 생성 (`counter`, `date`, `datetime` 등)
- **ensure_unique**: 중복 파일명 방지
- **sanitize**: 특수문자 제거
- 기타: prefix, delimiter, case 등

### FSOOpsPolicy (파일 작업 정책)
- **exist.create_if_missing**: 디렉토리 자동 생성
- **exist.overwrite**: 덮어쓰기 허용
- **ext.default_ext**: 기본 확장자
- **ext.allowed_exts**: 허용 확장자 목록

## 💡 팁

### 1. 최소 설정
필수 항목만 설정하고 나머지는 기본값 사용:

```yaml
image:
  source:
    path: "input/image.jpg"
  # 나머지는 모두 기본값
```

### 2. 섹션별 override
특정 섹션만 변경:

```yaml
image:
  source:
    path: "input/image.jpg"
  
  save:
    name:
      suffix: "_custom"  # 이것만 변경
  
  # process, meta, log는 기본값
```

### 3. FSO 고급 기능 활용
파일명에 날짜/시간 추가:

```yaml
save:
  name:
    suffix: "_processed"
    tail_mode: "datetime"        # 20251015_143022 형식 추가
    date_format: "%Y%m%d_%H%M%S"
```

카운터와 날짜 함께 사용:

```yaml
save:
  name:
    suffix: "_processed"
    tail_mode: "datetime_counter"  # 20251015_001, 20251015_002
```

## 📚 참고

- FSO 정책 상세: `modules/fso_utils/core/policy.py`
- Log 정책 상세: `modules/logs_utils/core/policy.py`
- Font 정책 상세: `modules/font_utils/core/policy.py`
