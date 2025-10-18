# structured_io 개선 구현 요약

**작성일**: 2025-10-19  
**작업자**: GitHub Copilot

---

## ✅ 완료된 작업

### 1. Base 접두사 통일 (네이밍 일관성)

#### ✅ `core/interface.py`
- `Parser` → `BaseParser`
- `Dumper` → `BaseDumper`
- 하위 호환성을 위한 alias 추가:
  ```python
  Parser = BaseParser
  Dumper = BaseDumper
  ```

#### ✅ `core/__init__.py`
- Export 순서 변경: `BaseParser`, `BaseDumper`가 primary
- `Parser`, `Dumper`는 backward compatibility용으로 표시

---

### 2. Import 경로 수정

#### ✅ `formats/yaml_io.py`
```python
# ❌ Before
from structured_io.fileio import BaseParserPolicy
from structured_io.core.interface import BaseDumper

# ✅ After
from structured_io.core.policy import BaseParserPolicy
from structured_io.core.interface import BaseParser, BaseDumper
```

#### ✅ `formats/json_io.py`
```python
# ❌ Before
from structured_io.core.interface import BaseParser
from structured_io.core.interface import BaseDumper

# ✅ After
from structured_io.core.interface import BaseParser, BaseDumper
```

---

### 3. VarsResolver 캡슐화 개선 (Private 메서드 호출 제거)

#### ✅ `formats/yaml_io.py`
```python
# ❌ Before
resolver = VarsResolver(data={}, policy=vars_policy)
text = resolver._apply_single(text)  # private 메서드

# ✅ After
resolver = VarsResolver(data={}, policy=vars_policy)
text = resolver.apply(text)  # public API
```

**추가 개선**:
- `recursive=True` → `recursive=False` (문자열만 처리하므로 불필요)
- 주석 개선: "VarsResolver의 public API 사용"

#### ✅ `formats/json_io.py`
- 동일한 패턴으로 수정

---

## 📊 발견된 문제와 해결 방안

### 문제 1: SourcePathPolicy의 역할 혼란 ❌

**현재 상태**:
- `structured_io/core/policy.py`에 `SourcePathPolicy` 정의
- `BaseParserPolicy.source_paths` 필드 존재
- 하지만 `structured_io` 내에서 사용하지 않음

**사용처 분석**:
```python
# cfg_utils/services/config_loader.py에서만 사용
from structured_io.core.base_policy import SourcePathPolicy  # ❌ 잘못된 경로

class SourcePathPolicy(BaseModel):
    path: Union[str, Path]
    section: Optional[str]
```

**역할 분석**:
- `SourcePathPolicy`: ConfigLoader가 여러 YAML 파일을 로드할 때 사용
- `source_paths` 필드: ConfigLoader 전용 필드 (Parser와 무관)

**해결 방안**:

#### 옵션 A: SourcePathPolicy를 cfg_utils로 이동 (권장)

1. `cfg_utils/core/policy.py`에 `SourcePathPolicy` 정의
2. `structured_io/core/policy.py`에서 제거
3. `BaseParserPolicy.source_paths` 필드 제거

```python
# cfg_utils/core/policy.py
class SourcePathPolicy(BaseModel):
    """ConfigLoader용 소스 경로 정책"""
    path: Union[str, Path] = Field(..., description="파일 경로")
    section: Optional[str] = Field(None, description="추출할 섹션")

class ConfigPolicy(BaseModel):
    yaml: Optional[BaseParserPolicy] = Field(...)
    source_paths: Optional[Union[SourcePathPolicy, List[SourcePathPolicy]]] = Field(...)
    # ...
```

**장점**:
- 책임 명확화: Parser는 파싱만, ConfigLoader는 소스 관리
- `structured_io`의 순수성 유지
- cfg_utils와 structured_io 간 의존성 감소

**단점**:
- cfg_utils 코드 수정 필요 (import 경로 변경)
- 기존 코드 영향

#### 옵션 B: 현재 구조 유지 + 문서화

- `SourcePathPolicy`를 `structured_io`에 유지
- "ConfigLoader 전용" 명시
- `BaseParserPolicy.source_paths` deprecated 표시

**권장**: **옵션 A** (책임 분리 원칙)

---

### 문제 2: cfg_utils의 잘못된 import 경로 ⚠️

**현재**:
```python
# cfg_utils/core/policy.py
from structured_io.core.base_policy import BaseParserPolicy  # ❌

# cfg_utils/services/config_loader.py
from structured_io.core.base_policy import SourcePathPolicy  # ❌
```

**수정 필요**:
```python
# ✅ 올바른 경로
from structured_io.core.policy import BaseParserPolicy, SourcePathPolicy
```

**파일 목록**:
1. `cfg_utils/core/policy.py` (line 20)
2. `cfg_utils/services/config_loader.py` (line 424, 478, 519)

---

### 문제 3: FSOOps 연계 필요성 🟢

**현재 구조**:
```python
# structured_io/fileio/structured_fileio.py
from modules.fso_utils import FSOOps, FSOOpsPolicy

class StructuredFileIO:
    def __init__(self, path: str | Path, parser, dumper, fso_policy: FSOOpsPolicy | None = None):
        self.path = FSOOps(path, fso_policy or FSOOpsPolicy(as_type="file"))
```

**분석**:

#### FSOOps의 역할:
1. 파일 존재 검증
2. 디렉토리 자동 생성
3. 권한 검사
4. 경로 정규화
5. 백업 관리

#### StructuredFileIO의 요구사항:
1. ✅ 파일 읽기/쓰기 (필수)
2. ✅ 디렉토리 자동 생성 (필수)
3. ⚠️ 권한 검사 (선택)
4. ⚠️ 백업 관리 (선택)

#### 결론:
**✅ FSOOps 연계는 적절함**

**이유**:
1. `cfg_utils`, `xl_utils` 등 다른 모듈도 FSOOps 사용
2. 파일 I/O의 고급 기능 (검증, 백업) 제공
3. 프로젝트 일관성 유지

**대안 (단순화)**:
```python
# fso_policy 없이 기본 Path 사용 가능
class StructuredFileIO:
    def __init__(self, path: str | Path, parser, dumper):
        self.path = Path(path)
        
    def read(self) -> Any:
        if not self.path.exists():
            raise FileNotFoundError(f"File not found: {self.path}")
        # ...
    
    def write(self, data: Any) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)  # 디렉토리 생성
        # ...
```

**권장**: **현재 구조 유지** (FSOOps의 고급 기능 활용)

---

## 🎯 개선 효과

### Before vs After

| 항목 | Before | After | 개선 |
|------|--------|-------|------|
| **네이밍 일관성** | `Parser` / `BaseParser` 혼용 | `BaseParser` 통일 | ✅ 명확 |
| **Import 경로** | `structured_io.fileio` (❌) | `structured_io.core.policy` (✅) | ✅ 정확 |
| **캡슐화** | `resolver._apply_single()` (private) | `resolver.apply()` (public) | ✅ 개선 |
| **의존성** | `recursive=True` (불필요) | `recursive=False` | ✅ 최적화 |
| **문서화** | 주석 부족 | 상세한 주석 추가 | ✅ 가독성 |

---

## 🚀 향후 작업 (Phase 2)

### 1. cfg_utils Import 경로 수정 (Critical)
```python
# cfg_utils/core/policy.py
- from structured_io.core.base_policy import BaseParserPolicy
+ from structured_io.core.policy import BaseParserPolicy

# cfg_utils/services/config_loader.py (3곳)
- from structured_io.core.base_policy import SourcePathPolicy
+ from structured_io.core.policy import SourcePathPolicy
```

### 2. SourcePathPolicy 이동 검토 (High)
- `structured_io` → `cfg_utils` 이동
- `BaseParserPolicy.source_paths` 필드 제거
- cfg_utils import 업데이트

### 3. 테스트 추가 (High)
```python
# tests/test_yaml_parser.py
def test_vars_resolver_public_api():
    """VarsResolver public API 사용 테스트"""
    parser = yaml_parser(enable_env=True, enable_placeholder=True)
    parser.context = {"HOST": "localhost"}
    
    text = "url: http://{{HOST}}:${PORT:8000}"
    data = parser.parse(text)
    
    assert data["url"] == "http://localhost:8000"
```

### 4. 문서화 개선 (Medium)
- README.md 업데이트
- API 레퍼런스 추가
- 사용 예시 확장

---

## 📝 변경 파일 목록

### ✅ 수정 완료
1. `structured_io/core/interface.py` - Base 접두사 통일
2. `structured_io/core/__init__.py` - Export 순서 변경
3. `structured_io/formats/yaml_io.py` - Import 경로 + VarsResolver public API
4. `structured_io/formats/json_io.py` - Import 경로 + VarsResolver public API

### ⏳ 수정 필요 (Phase 2)
5. `cfg_utils/core/policy.py` - Import 경로 수정
6. `cfg_utils/services/config_loader.py` - Import 경로 수정 (3곳)

### 🔍 검토 필요
7. `structured_io/core/policy.py` - `SourcePathPolicy` 이동 검토
8. `cfg_utils/core/policy.py` - `SourcePathPolicy` 재정의 검토

---

## ✅ 최종 체크리스트

- [x] Base 접두사 통일 (BaseParser, BaseDumper)
- [x] Import 경로 수정 (yaml_io.py, json_io.py)
- [x] VarsResolver private 메서드 호출 제거
- [x] recursive 플래그 최적화 (True → False)
- [x] 코드 주석 개선
- [ ] cfg_utils import 경로 수정 (Phase 2)
- [ ] SourcePathPolicy 이동 검토 (Phase 2)
- [ ] 테스트 추가 (Phase 2)

---

## 📌 결론

1. **Base 접두사 통일**: 네이밍 일관성 확보 ✅
2. **VarsResolver 캡슐화 개선**: Private 메서드 호출 제거 ✅
3. **SourcePathPolicy**: cfg_utils 전용 필드 → 이동 검토 필요 ⏳
4. **FSOOps 연계**: 현재 구조 적절함 ✅

**전체 개선 효과**: 
- 코드 품질 향상
- 캡슐화 개선
- 의존성 최적화
- 책임 분리 명확화

**다음 단계**: Phase 2 작업 (cfg_utils import 수정)
