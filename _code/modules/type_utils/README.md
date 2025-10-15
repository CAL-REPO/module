# Type Utils

**파일 타입 추론 및 확장자 검출 유틸리티**

URL, 파일 경로, 바이너리 데이터에서 파일 타입을 자동으로 추론하고 확장자를 추출합니다.

---

## 🚀 빠른 시작

### 설치

이 모듈은 PYTHONPATH에 `modules/` 디렉토리가 포함되어 있어야 합니다:

```bash
export PYTHONPATH="M:\CALife\CAShop - 구매대행\_code\modules"
```

### 기본 사용

```python
from type_utils import infer_type, extract_extension

# 타입 추론
infer_type("https://example.com/photo.jpg")  # → 'image'
infer_type("document.pdf")                    # → 'document'
infer_type("Hello World")                     # → 'text'
infer_type(b"binary data")                    # → 'file'

# 확장자 추출
extract_extension("https://img.com/photo.jpg")  # → 'jpg'
extract_extension("archive.tar.gz")             # → 'gz'
```

---

## 📋 주요 기능

### 1. 타입 자동 추론

#### 지원 타입
- **image**: `.jpg`, `.png`, `.gif`, `.webp`, `.svg`, `.bmp` 등
- **video**: `.mp4`, `.avi`, `.mov`, `.webm`, `.mkv` 등
- **audio**: `.mp3`, `.wav`, `.flac`, `.aac`, `.ogg` 등
- **document**: `.pdf`, `.doc`, `.xls`, `.ppt`, `.txt` 등
- **archive**: `.zip`, `.rar`, `.7z`, `.tar`, `.gz` 등
- **text**: 일반 문자열
- **file**: 알 수 없는 바이너리

#### 추론 규칙

```python
from type_utils import TypeInferencer

inferencer = TypeInferencer()

# 1. URL 분석
inferencer.infer("https://img.com/photo.jpg")     # 'image'
inferencer.infer("https://cdn.com/video.mp4")     # 'video'

# 2. 파일 경로 분석
inferencer.infer("document.pdf")                  # 'document'
inferencer.infer("archive.tar.gz")                # 'archive'

# 3. bytes 타입
inferencer.infer(b"\x89PNG...")                   # 'file'

# 4. 일반 텍스트
inferencer.infer("Product Title")                 # 'text'
inferencer.infer("가격: 10,000원")                # 'text'

# 5. 명시적 힌트 (최우선)
inferencer.infer(b"data", hint="image")           # 'image'
```

---

### 2. 확장자 추출

```python
from type_utils import ExtensionDetector

detector = ExtensionDetector()

# 단일 확장자
detector.extract("photo.jpg")                     # 'jpg'
detector.extract("https://img.com/photo.png")     # 'png'

# 다중 확장자
detector.extract_all("archive.tar.gz")            # ['tar', 'gz']
detector.extract_all("backup.old.zip")            # ['old', 'zip']

# 확장자 정규화
detector.normalize("JPG")                         # 'jpg'
detector.normalize(".PNG", include_dot=True)      # '.png'

# 확장자 검증
detector.is_image_extension("jpg")                # True
detector.is_video_extension("mp4")                # True
detector.is_document_extension("pdf")             # True
```

---

### 3. 커스텀 정책

```python
from type_utils import TypeInferencer, InferencePolicy

# 커스텀 정책 생성
policy = InferencePolicy()
policy.add_custom_mapping(".myext", "image")

inferencer = TypeInferencer(policy)
inferencer.infer("file.myext")                    # 'image'
```

#### 정책 종류

```python
from type_utils.core.policy import DefaultInferencePolicy

# 1. 기본 정책
policy = DefaultInferencePolicy.get_default()

# 2. 엄격한 정책 (알 수 없는 타입 → unknown)
policy = DefaultInferencePolicy.get_strict()

# 3. 관대한 정책 (알 수 없는 타입 → file)
policy = DefaultInferencePolicy.get_permissive()
```

---

## 🎯 사용 사례

### 1. 크롤링: 자동 파일 분류

```python
from type_utils import infer_type

# JS 추출 결과
extracted_data = {
    "images": [
        "https://img.com/product1.jpg",
        "https://img.com/product2.png"
    ],
    "title": "나이키 신발",
    "price": "89,000원",
    "manual": "https://cdn.com/manual.pdf"
}

# 자동 타입 분류
for key, value in extracted_data.items():
    if isinstance(value, list):
        for item in value:
            file_type = infer_type(item)
            print(f"{item} → {file_type}")
    else:
        file_type = infer_type(value)
        print(f"{value} → {file_type}")

# 출력:
# https://img.com/product1.jpg → image
# https://img.com/product2.png → image
# 나이키 신발 → text
# 89,000원 → text
# https://cdn.com/manual.pdf → document
```

### 2. 파일 업로드: 타입 검증

```python
from type_utils import TypeInferencer

def validate_upload(filename: str, allowed_types: set):
    inferencer = TypeInferencer()
    file_type = inferencer.infer(filename)
    
    if file_type not in allowed_types:
        raise ValueError(f"Invalid file type: {file_type}")
    
    return file_type

# 이미지만 허용
validate_upload("photo.jpg", {"image"})        # OK
validate_upload("document.pdf", {"image"})     # ValueError
```

### 3. 파일 다운로드: 확장자 자동 결정

```python
from type_utils import infer_extension

async def download_file(url: str, save_dir: str):
    # 확장자 자동 추론
    ext = infer_extension(url) or "bin"
    
    # 파일명 생성
    import hashlib
    hash_name = hashlib.md5(url.encode()).hexdigest()
    filename = f"{hash_name}.{ext}"
    
    # 다운로드
    save_path = Path(save_dir) / filename
    # ... download logic
```

### 4. crawl_utils 통합

```python
from type_utils import TypeInferencer
from crawl_utils.core.models import NormalizedItem, ItemKind

class SmartNormalizer:
    def __init__(self):
        self.inferencer = TypeInferencer()
    
    def normalize(self, extracted: dict) -> list[NormalizedItem]:
        items = []
        
        for key, value in extracted.items():
            # 타입 자동 추론
            file_type = self.inferencer.infer(value)
            
            # crawl_utils ItemKind로 변환
            kind: ItemKind = self._to_item_kind(file_type)
            
            # NormalizedItem 생성
            items.append(NormalizedItem(
                kind=kind,
                value=value,
                name_hint=key,
                extension=self.inferencer.infer_extension(value)
            ))
        
        return items
    
    def _to_item_kind(self, file_type: str) -> ItemKind:
        """FileType → ItemKind 매핑"""
        mapping = {
            "image": "image",
            "text": "text",
            "file": "file",
            "video": "file",
            "audio": "file",
            "document": "file",
            "archive": "file",
        }
        return mapping.get(file_type, "text")
```

---

## 📚 API 문서

### TypeInferencer

#### `infer(value, *, hint=None, fallback="file") -> FileType`

값의 타입 자동 추론.

**Args:**
- `value`: 추론할 값 (str, bytes, Path)
- `hint`: 명시적 타입 힌트 (선택)
- `fallback`: 추론 실패 시 기본값

**Returns:**
- `FileType`: `"image"`, `"video"`, `"audio"`, `"document"`, `"archive"`, `"text"`, `"file"`, `"unknown"` 중 하나

#### `infer_extension(value, kind=None) -> Optional[str]`

값에서 파일 확장자 추론.

**Args:**
- `value`: 추론할 값
- `kind`: 파일 타입 (알려진 경우)

**Returns:**
- `str`: 확장자 (점 없이) 또는 `None`

#### 타입 판별 메서드

- `is_url(value) -> bool`: URL 여부
- `is_image(value) -> bool`: 이미지 타입
- `is_video(value) -> bool`: 비디오 타입
- `is_audio(value) -> bool`: 오디오 타입
- `is_document(value) -> bool`: 문서 타입
- `is_archive(value) -> bool`: 압축 파일 타입
- `is_text(value) -> bool`: 텍스트 타입

---

### ExtensionDetector

#### `extract(value, *, normalize=True, include_dot=False) -> Optional[str]`

(마지막) 확장자 추출.

**Args:**
- `value`: URL, 파일 경로, 파일명
- `normalize`: 소문자 변환 여부
- `include_dot`: 점(.) 포함 여부

**Returns:**
- `str`: 확장자 또는 `None`

#### `extract_all(value, *, normalize=True) -> List[str]`

모든 확장자 추출 (다중 확장자 지원).

**Args:**
- `value`: URL, 파일 경로, 파일명
- `normalize`: 소문자 변환 여부

**Returns:**
- `List[str]`: 확장자 리스트

#### `normalize(extension, *, include_dot=False) -> str`

확장자 정규화 (소문자 변환, 점 처리).

#### 확장자 검증 메서드

- `is_image_extension(ext) -> bool`
- `is_video_extension(ext) -> bool`
- `is_audio_extension(ext) -> bool`
- `is_document_extension(ext) -> bool`
- `is_archive_extension(ext) -> bool`

#### `get_file_type(extension) -> Optional[FileType]`

확장자에서 파일 타입 추론.

---

### InferencePolicy

추론 규칙을 커스터마이징하는 정책 클래스.

#### 주요 속성

```python
policy = InferencePolicy(
    # 확장자 집합 (커스터마이징 가능)
    image_extensions={".jpg", ".png", ...},
    video_extensions={".mp4", ".avi", ...},
    audio_extensions={".mp3", ".wav", ...},
    document_extensions={".pdf", ".doc", ...},
    archive_extensions={".zip", ".rar", ...},
    
    # URL 판별 규칙
    url_schemes={"http", "https", "ftp"},
    
    # 기본 타입
    bytes_default_type="file",
    unknown_extension_type="file",
    text_default_type="text",
    url_without_extension_type="file",
    
    # 대소문자 구분
    case_sensitive=False,
    
    # 커스텀 매핑
    custom_mappings={".custom": "image"},
)
```

#### 메서드

- `get_file_type(extension) -> Optional[FileType]`: 확장자 → 타입
- `is_url(value) -> bool`: URL 판별
- `add_custom_mapping(extension, file_type)`: 커스텀 매핑 추가

---

## 🔧 고급 사용법

### 1. 싱글톤 인스턴스 사용

```python
from type_utils import get_default_inferencer, get_default_detector

# 싱글톤 인스턴스 (재사용)
inferencer = get_default_inferencer()
detector = get_default_detector()

# 여러 번 호출해도 동일 인스턴스
assert get_default_inferencer() is inferencer
```

### 2. 편의 함수 사용

```python
from type_utils import (
    infer_type,
    infer_extension,
    extract_extension,
    extract_all_extensions,
    normalize_extension,
    is_url,
)

# 클래스 인스턴스 없이 직접 사용
infer_type("photo.jpg")                    # 'image'
extract_extension("archive.tar.gz")        # 'gz'
normalize_extension("JPG")                 # 'jpg'
is_url("https://example.com")              # True
```

### 3. 커스텀 확장자 추가

```python
from type_utils import TypeInferencer, InferencePolicy

# 1. 정책 생성
policy = InferencePolicy()

# 2. 커스텀 확장자 추가
policy.add_custom_mapping(".sketch", "image")
policy.add_custom_mapping(".blend", "file")

# 3. Inferencer 생성
inferencer = TypeInferencer(policy)

# 4. 사용
inferencer.infer("design.sketch")  # 'image'
inferencer.infer("model.blend")    # 'file'
```

---

## 🧪 테스트

```bash
# PYTHONPATH 설정
export PYTHONPATH="M:\CALife\CAShop - 구매대행\_code\modules"

# 테스트 실행
pytest modules/type_utils/tests/ -v
```

---

## 📦 디렉토리 구조

```
type_utils/
├── __init__.py              # 최상위 exports
├── core/
│   ├── __init__.py
│   ├── types.py            # FileType, 확장자 집합 정의
│   └── policy.py           # InferencePolicy
├── services/
│   ├── __init__.py
│   ├── inferencer.py       # TypeInferencer
│   └── extension.py        # ExtensionDetector
└── tests/
    └── test_inferencer.py  # 단위 테스트
```

---

## 🎯 설계 원칙

### 1. 최소 의존성
- 표준 라이브러리만 사용 (`pathlib`, `urllib.parse`, `typing`)
- 외부 패키지 의존성 없음 (Pydantic 제외)

### 2. 범용성
- 크롤링뿐 아니라 파일 처리, 업로드, 다운로드 등 다양한 용도로 사용 가능

### 3. 확장 가능성
- `InferencePolicy`로 규칙 커스터마이징
- 새로운 파일 타입 추가 용이
- 향후 MIME type, magic number 분석 추가 가능

### 4. 테스트 용이성
- 순수 함수로 설계
- Mock 없이 단위 테스트 가능

---

## 🔄 crawl_utils와의 통합

`type_utils`는 독립 모듈이지만 `crawl_utils`에서 다음과 같이 사용됩니다:

```python
# crawl_utils/services/smart_normalizer.py
from type_utils import TypeInferencer

class SmartNormalizer:
    def __init__(self):
        self.inferencer = TypeInferencer()
    
    def normalize(self, extracted: dict) -> list:
        # type_utils로 타입 자동 추론
        # crawl_utils ItemKind로 변환
        # NormalizedItem 생성
        pass
```

---

## 📝 버전

**v1.0.0** - 2025-10-15

- ✅ TypeInferencer 구현
- ✅ ExtensionDetector 구현
- ✅ InferencePolicy 구현
- ✅ 편의 함수 제공
- ✅ 단위 테스트 작성

---

## 🤝 기여

이 모듈은 CAShop 프로젝트의 일부입니다.

**작성자**: GitHub Copilot  
**프로젝트**: CAShop - 구매대행  
**날짜**: 2025-10-15
