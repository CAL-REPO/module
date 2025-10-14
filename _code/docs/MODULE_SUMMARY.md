# 📚 CAShop Modules 전체 구조 분석 보고서

> **작성일**: 2025-10-14  
> **목적**: 전체 모듈 구조 파악 및 개선 방향 제시

---

## 📦 모듈 계층 구조

```
modules/
├── 🔧 Core Infrastructure (핵심 인프라)
│   ├── cfg_utils/          # 설정 로딩 및 병합 (ConfigLoader)
│   ├── log_utils/          # 로깅 관리 (LogManager)
│   ├── fso_utils/          # 파일시스템 작업 (FSOOps, FSOPathBuilder)
│   ├── path_utils/         # 경로 유틸리티 (OSPath)
│   └── structured_io/      # YAML/JSON 파싱 및 덤핑
│
├── 📊 Data Processing (데이터 처리)
│   ├── data_utils/         # 데이터 조작 (StringOps, DictOps, ListOps, GeometryOps)
│   ├── keypath_utils/      # 경로 기반 dict 조작 (KeyPathDict, KeyPathAccessor)
│   └── unify_utils/        # 정규화 및 해석 (Normalizer, Resolver)
│
├── 🖼️ Image Processing (이미지 처리)
│   ├── pillow_utils/       # 이미지 로딩/오버레이 (ImageLoader, ImageOverlay)
│   ├── ocr_utils/          # OCR 처리 (ImageOCR, PaddleOCR provider)
│   └── font_utils/         # 폰트 정책 (FontPolicy)
│
├── 🌐 Web & Crawling (웹 크롤링)
│   ├── crawl_refactor/     # 크롤링 파이프라인 (CrawlPipeline)
│   ├── firefox/            # Firefox WebDriver 관리
│   └── translate_utils/    # 번역 서비스 (Google Translate API)
│
└── 📈 Data I/O (데이터 입출력)
    └── xl_utils/           # Excel 작업 (openpyxl, xlwings)

```

---

## 🎯 주요 모듈 상세 분석

### 1️⃣ **cfg_utils** - 설정 로딩 시스템

**역할**: YAML/JSON 설정 파일을 Pydantic 모델로 변환

**핵심 클래스**:
- `ConfigLoader`: 설정 병합 및 모델 변환
- `ConfigNormalizer`: reference/blank 후처리
- `ConfigPolicy`: 병합/파싱 정책

**특징**:
- ✅ Section 자동 감지 (모델명 기반)
- ✅ Deep/Shallow 병합 지원
- ✅ Reference placeholder 해석 (`${key.path:default}`)
- ✅ 런타임 override 지원

**사용 예시**:
```python
from cfg_utils import ConfigLoader
from pillow_utils.policy import ImageLoaderPolicy

# Section 자동 감지 (unified.yaml에서 "pillow:" 추출)
loader = ConfigLoader("configs/unified.yaml")
policy = loader.as_model(ImageLoaderPolicy)

# 또는 명시적 section 지정
policy = loader.as_model(ImageLoaderPolicy, section="pillow")
```

---

### 2️⃣ **pillow_utils** - 이미지 처리 엔트리포인트

**3개 엔트리포인트**:
1. **ImageLoader**: 이미지 로딩/전처리/저장
2. **ImageOCR** (ocr_utils): OCR 실행
3. **ImageOverlay**: 텍스트 오버레이

**정책 구조**:
```python
# ImageLoaderPolicy (pillow.yaml)
pillow:
  source:        # ImageSourcePolicy (경로, 존재 확인)
  image:         # ImagePolicy (저장 옵션)
  meta:          # ImageMetaPolicy (메타데이터)
  processing:    # ImageProcessorPolicy (리사이즈, 블러)

# ImageOverlayPolicy (overlay.yaml)
overlay:
  source:        # ImageSourcePolicy
  output:        # 출력 설정
  texts:         # List[OverlayTextPolicy] (텍스트 오버레이)
  font:          # FontPolicy (폰트 설정)
```

**현재 사용 패턴**:
```python
# 통합 YAML 사용
loader = ImageLoader("configs/unified.yaml")
result = loader.run()
image = result["image"]
saved_path = result["saved_image_path"]

# 개별 YAML 사용
loader = ImageLoader("configs/pillow.yaml")
ocr = ImageOCR("configs/ocr.yaml")
overlay = ImageOverlay("configs/overlay.yaml")
```

---

### 3️⃣ **ocr_utils** - OCR 처리 파이프라인

**핵심 클래스**:
- `ImageOCR`: OCR 실행 엔트리포인트
- `OcrPolicy`: 설정 통합 (file, provider, preprocess)
- `OCRItem`: 단일 OCR 결과 모델

**Provider 구조**:
```python
ocr_utils/providers/
  ├── __init__.py
  ├── paddle.py       # PaddleOCR 래퍼
  └── (future) tesseract.py
```

**PaddleOCR 버전**:
- ✅ **Current**: PaddleOCR 3.2.0 (최신 안정 버전)
- ✅ API: `ocr.predict(input="image_path")`
- ✅ 다국어 지원: `["ch_sim", "en"]`

**결과 구조**:
```python
{
    "image": PIL.Image,
    "resize_ratio": (0.8, 0.8),
    "ocr_results": [
        {
            "text": "감지된 텍스트",
            "bbox": {"x": 10, "y": 20, "w": 100, "h": 30},
            "polygon": [(x1,y1), (x2,y2), ...],
            "conf": 0.95,
            "lang": "ch_sim"
        }
    ],
    "metadata": {...}
}
```

---

### 4️⃣ **log_utils** - 로깅 관리

**핵심 클래스**:
- `LogManager`: Loguru 기반 로거 설정
- `LogPolicy`: 로그 정책 (회전, 보존, 압축)
- `LogFSOBuilder`: 로그 파일 경로 자동 생성

**특징**:
- ✅ 파일 자동 회전 (rotation: "1 day")
- ✅ 보존 기간 설정 (retention: "7 days")
- ✅ 압축 지원 (compression: "zip")
- ✅ FSO_utils 통합 (안전한 경로 생성)

**사용 예시**:
```python
from log_utils import LogManager, LogPolicy

policy = LogPolicy(
    enabled=True,
    level="INFO",
    rotation="1 day",
    retention="7 days"
)
logger = LogManager(name="MyLogger", policy=policy).setup()
logger.info("로그 메시지")
```

---

### 5️⃣ **fso_utils** - 파일시스템 작업

**핵심 클래스**:
- `FSOOps`: 파일/디렉터리 존재 확인 및 생성
- `FSOPathBuilder`: 안전한 경로 생성 (충돌 방지)
- `FSONamePolicy`: 파일명 생성 정책
- `FSOOpsPolicy`: 작업 정책

**특징**:
- ✅ 자동 충돌 회피 (counter, datetime)
- ✅ 안전한 파일명 생성 (특수문자 제거)
- ✅ 정책 기반 동작 (create_if_missing)

**사용 예시**:
```python
from fso_utils import FSOPathBuilder, FSONamePolicy, FSOOpsPolicy, ExistencePolicy

name_policy = FSONamePolicy(
    as_type="file",
    name="output",
    extension=".jpg",
    tail_mode="counter",
    ensure_unique=True
)
ops_policy = FSOOpsPolicy(
    as_type="file",
    exist=ExistencePolicy(create_if_missing=True)
)
builder = FSOPathBuilder(base_dir="output/", name_policy=name_policy, ops_policy=ops_policy)
path = builder()  # output/output_001.jpg
```

---

### 6️⃣ **data_utils** - 데이터 조작 유틸리티

**모듈 구성**:
```python
data_utils/
  ├── string_ops.py      # 문자열 조작
  ├── dict_ops.py        # 딕셔너리 병합
  ├── list_ops.py        # 리스트 조작
  ├── geometry_ops.py    # 기하학 연산 (bbox IoU)
  ├── db_ops.py          # SQLite KV 저장소
  └── df_ops/            # DataFrame 조작
```

**주요 기능**:
- `StringOps.strip_special_chars()`: 특수문자 제거
- `StringOps.is_alphanumeric_only()`: 문자 포함 여부 확인
- `GeometryOps.bbox_intersection_over_union()`: bbox 중복 감지
- `DictOps.deep_merge()`: 딕셔너리 병합
- `SQLiteKVStore`: 캐시용 KV 저장소

---

### 7️⃣ **keypath_utils** - 경로 기반 dict 조작

**핵심 클래스**:
- `KeyPathDict`: 경로 기반 dict 컨테이너
- `KeyPathAccessor`: 안전한 경로 접근
- `KeyPathState`: 상태 관리 모델

**특징**:
- ✅ 경로 기반 접근 (`"user.info.name"`)
- ✅ Deep/Shallow 병합
- ✅ 안전한 기본값 처리

**사용 예시**:
```python
from keypath_utils import KeyPathDict

data = KeyPathDict()
data.override("user.info.name", "Alice")
data.merge({"user": {"age": 30}}, deep=True)
print(data.get("user.info.name"))  # "Alice"
```

---

### 8️⃣ **unify_utils** - 정규화 및 해석

**핵심 클래스**:
- `ReferenceResolver`: `${key.path:default}` 해석
- `PlaceholderResolver`: `{var}` 치환
- `ValueNormalizer`: 값 타입 정규화
- `RuleBasedNormalizer`: 규칙 기반 정규화

**특징**:
- ✅ Reference 재귀 해석
- ✅ 환경변수 치환
- ✅ 타입 변환 (date, bool, number)

**사용 예시**:
```python
from unify_utils import ReferenceResolver

data = {
    "base_url": "https://example.com",
    "api_url": "${base_url}/api"
}
resolver = ReferenceResolver(data)
result = resolver.apply(data)
# result["api_url"] == "https://example.com/api"
```

---

### 9️⃣ **structured_io** - YAML/JSON 파싱

**핵심 클래스**:
- `YamlParser`: YAML 파싱 (env/include 지원)
- `YamlDumper`: YAML 덤핑
- `JsonParser`: JSON 파싱
- `StructuredFileIO`: 파일 I/O 통합

**특징**:
- ✅ `!include` 지시자 지원
- ✅ 환경변수 치환 (`${ENV_VAR}`)
- ✅ Placeholder 해석

---

### 🔟 **crawl_refactor** - 크롤링 파이프라인

**핵심 클래스**:
- `CrawlPipeline`: 전체 파이프라인 조율
- `HTTPFetcher`: HTTP 리소스 다운로드
- `ExtractorFactory`: 데이터 추출기 생성
- `DataNormalizer`: 데이터 정규화
- `StorageDispatcher`: 저장 전략 실행

**파이프라인 흐름**:
```
Navigator.load(url)
  ↓
Navigator.paginate(page)
  ↓
Navigator.scroll()
  ↓
Extractor.extract() → raw_data
  ↓
DataNormalizer.normalize() → NormalizedItem[]
  ↓
StorageDispatcher.save_many() → SaveSummary
```

---

## 🔗 모듈 간 의존 관계

```
[상위 계층] - 비즈니스 로직
  pillow_utils → ocr_utils → translate_utils
  crawl_refactor → firefox

[중간 계층] - 데이터 처리
  cfg_utils → structured_io → unify_utils
  keypath_utils → data_utils

[하위 계층] - 인프라
  log_utils → fso_utils → path_utils
```

**의존성 규칙**:
- ❌ 하위 → 상위 의존 금지
- ✅ 동일 계층 간 최소 의존
- ✅ 정책 객체를 통한 간접 의존

---

## 📋 정책(Policy) 기반 설계 패턴

**모든 주요 모듈이 Pydantic Policy 사용**:

| 모듈 | Policy 클래스 | 역할 |
|------|--------------|------|
| cfg_utils | ConfigPolicy | 병합/파싱 정책 |
| log_utils | LogPolicy | 로그 회전/보존 정책 |
| pillow_utils | ImageLoaderPolicy | 이미지 로딩 정책 |
| ocr_utils | OcrPolicy | OCR 실행 정책 |
| crawl_refactor | CrawlPolicy | 크롤링 파이프라인 정책 |
| fso_utils | FSOOpsPolicy | 파일 작업 정책 |

**Policy 설계 원칙**:
1. ✅ **Validation**: Pydantic으로 타입/값 검증
2. ✅ **Defaults**: 합리적인 기본값 제공
3. ✅ **Composition**: 작은 Policy 조합
4. ✅ **Override**: YAML → Runtime override 지원

---

## 🎨 현재 설정 파일 구조

```yaml
# configs/unified.yaml - 통합 설정 (권장)
pillow:
  source: {...}
  image: {...}
  meta: {...}
  processing: {...}

ocr:
  file: {...}
  provider: {...}
  preprocess: {...}

overlay:
  source: {...}
  output: {...}
  texts: [...]
```

**개별 설정 파일**:
- `configs/pillow.yaml` - ImageLoader 전용
- `configs/ocr.yaml` - ImageOCR 전용
- `configs/overlay.yaml` - ImageOverlay 전용

---

## 🚀 실행 스크립트 현황

### ✅ 정상 작동 스크립트

**scripts/tmp_run_service.py** (통합 파이프라인):
```python
# 1. ImageLoader → 이미지 전처리
loader = ImageLoader(cfg_path)
loader_result = loader.run()
image = loader_result["image"]

# 2. ImageOCR → OCR 실행
ocr = ImageOCR(cfg_path)
ocr_result = ocr.run(image=image)
items = ocr_result["ocr_results"]

# 3. ImageOverlay → 오버레이
overlay = ImageOverlay(cfg_path)
output_path = overlay.run()
```

**실행 결과** (2025-10-14 검증):
- ✅ 이미지 로딩: 1500x2322 RGB
- ✅ OCR 감지: 29개 → 14개 (정제/중복제거)
- ✅ 오버레이 생성: output/images/01_overlay_008.jpg
- ✅ 소요 시간: ~57초 (PaddleOCR 모델 로딩 포함)

---

## ⚠️ 개선 필요 사항

### 1️⃣ **엔트리포인트 복잡도**

**현재 문제**:
```python
# __init__이 복잡함
def __init__(self, policy_or_path: Union[Policy, str, Path], **kwargs):
    if isinstance(policy_or_path, (str, Path)):
        cfg = ConfigLoader(policy_or_path).as_model(Policy)
        if kwargs:
            # 병합 로직...
            pass
    # ...
```

**제안 개선**:
```python
# from_config 패턴
@classmethod
def from_config(cls, config_path: str, **overrides):
    policy = ConfigLoader(config_path).as_model(Policy)
    # override 처리
    return cls(policy)

def __init__(self, policy: Policy):
    self.policy = policy
```

### 2️⃣ **결과 객체 구조**

**현재**: Dict 반환 (타입 안전성 낮음)
```python
result = loader.run()
image = result["image"]  # 오타 위험
```

**제안**: Dataclass 결과 객체
```python
@dataclass
class ImageLoaderResult:
    image: Image.Image
    output_path: Optional[Path]
    metadata: Dict[str, Any]

result = loader.run()
image = result.image  # 타입 안전
```

### 3️⃣ **모듈 문서화**

**현황**:
- ✅ cfg_utils: 상세 docstring
- ✅ log_utils: policy.py 완전 문서화
- ⚠️ pillow_utils: 부분 문서화
- ⚠️ ocr_utils: 최소 문서화

**필요**:
- 각 모듈 README.md 작성
- 사용 예시 추가
- 의존 관계 명시

---

## 📊 테스트 커버리지 현황

| 모듈 | 테스트 파일 | 상태 |
|------|------------|------|
| cfg_utils | ❌ 없음 | 미작성 |
| log_utils | ❌ 없음 | 미작성 |
| pillow_utils | ❌ 없음 | 미작성 |
| ocr_utils | ⚠️ test_refactor.py | 부분 |
| crawl_refactor | ❌ 없음 | 미작성 |

**권장 사항**:
- pytest 기반 단위 테스트 추가
- 통합 테스트 스크립트 작성
- CI/CD 파이프라인 구축

---

## 🎯 권장 개선 순서

### Phase 1: 엔트리포인트 개선 (1주)
1. ✅ ImageLoader에 `from_config()` 추가
2. ✅ ImageOCR에 `from_config()` 추가
3. ✅ ImageOverlay에 `from_config()` 추가
4. ✅ 결과 객체 dataclass 변환
5. ✅ 테스트 스크립트 업데이트

### Phase 2: 문서화 (1주)
1. 각 모듈 README.md 작성
2. 사용 예시 추가
3. API 레퍼런스 생성
4. 의존 관계 다이어그램

### Phase 3: 테스트 (2주)
1. pytest 환경 구축
2. 단위 테스트 작성
3. 통합 테스트 작성
4. 커버리지 측정

### Phase 4: 리팩토링 (지속)
1. 중복 코드 제거
2. 성능 최적화
3. 타입 힌팅 강화
4. Linting 적용

---

## 📝 최종 요약

### ✅ 잘 설계된 부분
1. **Policy 기반 설계**: 모든 모듈이 일관된 정책 패턴 사용
2. **계층 구조**: 명확한 의존 관계 (상위 → 하위)
3. **ConfigLoader**: 강력한 설정 병합 및 section 자동 감지
4. **FSO_utils**: 안전한 파일시스템 작업

### ⚠️ 개선 필요 부분
1. **엔트리포인트 복잡도**: `__init__` 단순화 필요
2. **결과 타입**: Dict → Dataclass 변환
3. **문서화**: 각 모듈 사용법 명확화
4. **테스트**: 체계적인 테스트 코드 부재

### 🎯 핵심 개선 방향
> **"정책 로딩은 from_config()로, 실행은 run()으로, 결과는 dataclass로"**

---

**작성자**: GitHub Copilot  
**검토 필요**: 사용자 확인 및 피드백
