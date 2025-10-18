# cfg_utils vs cfg_utils_v2 비교 분석

## 📋 목차
1. [개요](#개요)
2. [핵심 차이점](#핵심-차이점)
3. [아키텍처 비교](#아키텍처-비교)
4. [Policy 구조 비교](#policy-구조-비교)
5. [ConfigLoader 비교](#configloader-비교)
6. [사용법 비교](#사용법-비교)
7. [마이그레이션 가이드](#마이그레이션-가이드)
8. [언제 무엇을 사용할까](#언제-무엇을-사용할까)

---

## 개요

### cfg_utils (v1)
- **목적**: YAML 설정 파일 로드 및 정규화
- **접근법**: YAML 중심, Pydantic 모델 지원
- **특징**: BaseServiceLoader 패턴 (각 모듈별 Loader 구현)

### cfg_utils_v2
- **목적**: 통합 Configuration 관리 시스템
- **접근법**: 단일 진입점, 타입 자동 판단
- **특징**: KeyPath State 기반, Source 추상화

---

## 핵심 차이점

| 항목 | cfg_utils (v1) | cfg_utils_v2 |
|------|----------------|--------------|
| **진입점** | `ConfigLoader.load()` | `ConfigLoader` (인스턴스) |
| **주 사용 형태** | 정적 메서드 (Static) | 인스턴스 메서드 |
| **데이터 구조** | KeyPathDict | KeyPathState |
| **소스 타입** | YAML Path, BaseModel, Dict | BaseModel, Dict, YAML Path (자동 판단) |
| **정책 구조** | ConfigPolicy (단일) | ConfigLoaderPolicy → SourcePolicy (계층) |
| **병합 방식** | Merge Helper 함수들 | KeyPathState.merge() |
| **Override** | load() 호출 시 kwargs | override() 메서드 |
| **환경 변수** | ConfigPolicy.auto_load_paths | env, env_os 인자 |
| **Section 관리** | load_with_section() | base_sources/override_sources (튜플) |
| **상태 관리** | Stateless (함수형) | Stateful (인스턴스) |

---

## 아키텍처 비교

### cfg_utils (v1) - Function-Oriented

```
Application
    ↓
ConfigLoader.load(cfg_like, model, policy, **overrides)
    ↓
    ├─> load_source() → dict
    ├─> merge_sequence() → KeyPathDict
    ├─> ConfigNormalizer → Normalize
    └─> model.model_validate() → Model
```

**특징**:
- 함수 중심 (Helper functions)
- 한 번 호출로 완료
- 상태 유지 없음

### cfg_utils_v2 - Object-Oriented

```
Application
    ↓
ConfigLoader(base_sources, override_sources, env, env_os)
    ↓
    ├─> UnifiedSource → KeyPathDict
    ├─> KeyPathState.merge() → Merge
    ├─> EnvProcessor → env section
    └─> StateConverter → Dict/Model
```

**특징**:
- 객체 중심 (Class instances)
- 인스턴스 생성 후 여러 작업 가능
- 상태 유지 (KeyPathState)

---

## Policy 구조 비교

### cfg_utils (v1) - Flat Structure

```python
class ConfigPolicy(BaseModel):
    """단일 정책 모델"""
    
    # YAML 파싱
    yaml: Optional[BaseParserPolicy]
    
    # Normalizer
    drop_blanks: bool = True
    resolve_reference: bool = True
    
    # Merge
    merge_order: Literal["base→yaml→arg"] = "base→yaml→arg"
    merge_mode: Literal["deep", "shallow"] = "deep"
    
    # KeyPath
    keypath: KeyPathNormalizePolicy
    
    # Reference
    reference_context: dict[str, Any]
    auto_load_paths: bool = False
```

**특징**:
- 모든 옵션이 한 곳에
- 간단하고 직관적
- YAML 중심 설계

### cfg_utils_v2 - Hierarchical Structure

```python
# 1. 기본 정책
class MergePolicy(BaseModel):
    deep: bool = False
    overwrite: bool = True

class NormalizePolicy(BaseModel):
    normalize_keys: bool = False
    drop_blanks: bool = False
    resolve_vars: bool = True

# 2. 소스 정책 (타입별)
class SourcePolicy(BaseModel):
    """통합 소스 정책"""
    src: Optional[Any]  # 단일 진입점
    
    # BaseModel 정책
    base_model_normalizer: Optional[NormalizePolicy]
    base_model_merge: Optional[MergePolicy]
    
    # Dict 정책
    dict_normalizer: Optional[NormalizePolicy]
    dict_merge: Optional[MergePolicy]
    
    # YAML 정책
    yaml_parser: Optional[BaseParserPolicy]
    yaml_normalizer: Optional[NormalizePolicy]
    yaml_merge: Optional[MergePolicy]

# 3. ConfigLoader 전역 정책
class ConfigLoaderPolicy(BaseModel):
    source: SourcePolicy
    keypath: Optional[KeyPathStatePolicy]
    log: Optional[Any]
```

**특징**:
- 계층 구조 (3단계)
- 타입별 정책 분리
- 유연하고 확장 가능
- 단일 진입점 (src)

---

## ConfigLoader 비교

### cfg_utils (v1) - Static Method

```python
class ConfigLoader:
    """Static method 중심"""
    
    @staticmethod
    def load(
        cfg_like: Union[BaseModel, PathLike, PathsLike, dict],
        *,
        model: Optional[Type[T]] = None,
        policy: Optional[ConfigPolicy] = None,
        drop_blanks: Optional[bool] = None,
        resolve_reference: Optional[bool] = None,
        merge_mode: Optional[Literal["deep", "shallow"]] = None,
        **overrides: Any
    ) -> Union[dict, T]:
        """한 번 호출로 완료"""
        pass
    
    @classmethod
    def load_with_section(cls, ...):
        """Section 추출"""
        pass
    
    @classmethod
    def load_from_source_paths(cls, ...):
        """SourcePath로 로드"""
        pass
```

**사용 예시**:
```python
# 1회성 로드
config = ConfigLoader.load(
    "config.yaml",
    model=ImagePolicy,
    drop_blanks=True,
    max_width=2048  # Override
)

# Section 추출
data = ConfigLoader.load_with_section(
    "config.yaml",
    section="image",
    model=ImagePolicy
)
```

**특징**:
- ✅ 간단한 사용법 (한 줄)
- ✅ 상태 없음 (Stateless)
- ❌ 반복 호출 시 비효율적
- ❌ 런타임 수정 불가

### cfg_utils_v2 - Instance Method

```python
class ConfigLoader:
    """Instance 중심"""
    
    def __init__(
        self,
        config_loader_cfg_path: Optional[...] = None,
        *,
        policy: Optional[ConfigLoaderPolicy] = None,
        base_sources: Optional[ConfigSourceWithSection] = None,
        override_sources: Optional[ConfigSourceWithSection] = None,
        env: Optional[Union[str, List[str], PathLike, List[PathLike]]] = None,
        env_os: Optional[Union[bool, List[str]]] = None,
        log: Optional[Any] = None,
    ):
        """인스턴스 생성 시 설정"""
        self._state = KeyPathState()
        self._process_base_sources(base_sources)
        self._process_override_sources(override_sources)
        self._process_env(env)
        self._process_env_os(env_os)
    
    def get_state(self) -> KeyPathState:
        """현재 상태 반환"""
        pass
    
    def override(self, keypath: str, value: Any):
        """런타임 Override"""
        pass
    
    def to_dict(self, section: Optional[str] = None) -> dict:
        """Dict로 변환"""
        pass
    
    def to_model(self, model_class: Type[T], section: Optional[str] = None) -> T:
        """Model로 변환"""
        pass
```

**사용 예시**:
```python
# 인스턴스 생성 (초기 설정)
loader = ConfigLoader(
    base_sources=[(ImagePolicy(), "image")],
    override_sources=[
        ("config.yaml", "image"),
        ({"max_width": 2048}, "image")
    ],
    env="env.yaml",
    env_os=["DEBUG"]
)

# 다양한 사용
state = loader.get_state()
data = loader.to_dict(section="image")
policy = loader.to_model(ImagePolicy, section="image")

# 런타임 수정
loader.override("image__quality", 95)
policy2 = loader.to_model(ImagePolicy, section="image")
```

**특징**:
- ✅ 상태 유지 (Stateful)
- ✅ 런타임 수정 가능
- ✅ 다양한 Export (State/Dict/Model)
- ✅ 환경 변수 통합 (env, env_os)
- ❌ 초기 코드가 길어질 수 있음

---

## 사용법 비교

### 시나리오 1: 단순 YAML 로드

#### cfg_utils (v1)
```python
from cfg_utils import ConfigLoader

# Dict로 로드
data = ConfigLoader.load("config.yaml")

# Model로 로드
policy = ConfigLoader.load("config.yaml", model=ImagePolicy)

# Override
policy = ConfigLoader.load(
    "config.yaml",
    model=ImagePolicy,
    max_width=2048,
    quality=95
)
```

#### cfg_utils_v2
```python
from cfg_utils_v2 import ConfigLoader

# Dict로 로드
loader = ConfigLoader(
    override_sources=[("config.yaml", None)]
)
data = loader.to_dict()

# Model로 로드
loader = ConfigLoader(
    base_sources=[(ImagePolicy(), "image")],
    override_sources=[("config.yaml", "image")]
)
policy = loader.to_model(ImagePolicy, section="image")

# Override
loader = ConfigLoader(
    base_sources=[(ImagePolicy(), "image")],
    override_sources=[
        ("config.yaml", "image"),
        ({"max_width": 2048, "quality": 95}, "image")
    ]
)
policy = loader.to_model(ImagePolicy, section="image")
```

**v1이 더 간단함** ✅

### 시나리오 2: 여러 소스 병합

#### cfg_utils (v1)
```python
# 방법 1: 파일 리스트
data = ConfigLoader.load(
    ["base.yaml", "dev.yaml", "local.yaml"],
    model=ImagePolicy
)

# 방법 2: 수동 병합
from cfg_utils.services.merger import MergerFactory

kpd = KeyPathDict()
for path in ["base.yaml", "dev.yaml", "local.yaml"]:
    merger = MergerFactory.create_from_source(path)
    merger.merge(path, kpd, deep=True)

policy = ImagePolicy(**kpd.to_flat_dict())
```

#### cfg_utils_v2
```python
# 순서 보장 자동 병합
loader = ConfigLoader(
    base_sources=[(ImagePolicy(), "image")],
    override_sources=[
        ("base.yaml", "image"),
        ("dev.yaml", "image"),
        ("local.yaml", "image")
    ]
)
policy = loader.to_model(ImagePolicy, section="image")
```

**v2가 더 명확함** ✅

### 시나리오 3: 런타임 수정

#### cfg_utils (v1)
```python
# 불가능 - 매번 새로 로드
policy1 = ConfigLoader.load("config.yaml", model=ImagePolicy)
# → max_width 변경 필요?
# → load() 다시 호출해야 함

policy2 = ConfigLoader.load(
    "config.yaml",
    model=ImagePolicy,
    max_width=2048
)
```

#### cfg_utils_v2
```python
# 가능 - 상태 유지
loader = ConfigLoader(
    base_sources=[(ImagePolicy(), "image")],
    override_sources=[("config.yaml", "image")]
)

policy1 = loader.to_model(ImagePolicy, section="image")

# 런타임 수정
loader.override("image__max_width", 2048)
policy2 = loader.to_model(ImagePolicy, section="image")
```

**v2가 더 유연함** ✅

### 시나리오 4: 환경 변수

#### cfg_utils (v1)
```python
# 방법 1: auto_load_paths (paths.local.yaml만)
policy = ConfigLoader.load(
    "config.yaml",
    model=ImagePolicy,
    policy=ConfigPolicy(auto_load_paths=True)
)

# 방법 2: reference_context 수동 주입
from cfg_utils.services.paths_loader import PathsLoader

policy = ConfigLoader.load(
    "config.yaml",
    model=ImagePolicy,
    policy=ConfigPolicy(
        reference_context=PathsLoader.load()
    )
)
```

#### cfg_utils_v2
```python
# env 인자로 간단히
loader = ConfigLoader(
    base_sources=[(ImagePolicy(), "image")],
    override_sources=[("config.yaml", "image")],
    env=["env.yaml", "DEBUG=true"],
    env_os=["PATH", "HOME"]
)

# env section 자동 생성
state = loader.get_state()
# {
#     'image': {...},
#     'env': {'DEBUG': 'true', 'PATH': '...', ...}
# }
```

**v2가 더 강력함** ✅

---

## 마이그레이션 가이드

### v1 → v2 변환 패턴

#### 패턴 1: 단순 로드
```python
# v1
data = ConfigLoader.load("config.yaml")

# v2
loader = ConfigLoader(override_sources=[("config.yaml", None)])
data = loader.to_dict()
```

#### 패턴 2: Model 로드
```python
# v1
policy = ConfigLoader.load("config.yaml", model=ImagePolicy)

# v2
loader = ConfigLoader(
    base_sources=[(ImagePolicy(), "image")],
    override_sources=[("config.yaml", "image")]
)
policy = loader.to_model(ImagePolicy, section="image")
```

#### 패턴 3: Override
```python
# v1
policy = ConfigLoader.load(
    "config.yaml",
    model=ImagePolicy,
    max_width=2048
)

# v2
loader = ConfigLoader(
    base_sources=[(ImagePolicy(), "image")],
    override_sources=[
        ("config.yaml", "image"),
        ({"max_width": 2048}, "image")
    ]
)
policy = loader.to_model(ImagePolicy, section="image")
```

#### 패턴 4: Section
```python
# v1
data = ConfigLoader.load_with_section(
    "config.yaml",
    section="image",
    model=ImagePolicy
)

# v2
loader = ConfigLoader(
    base_sources=[(ImagePolicy(), "image")],
    override_sources=[("config.yaml", "image")]
)
policy = loader.to_model(ImagePolicy, section="image")
```

---

## 언제 무엇을 사용할까

### cfg_utils (v1)를 사용하는 경우 ✅

1. **단순 YAML 로드만 필요**
   ```python
   data = ConfigLoader.load("config.yaml")
   ```

2. **1회성 사용**
   - 애플리케이션 시작 시 한 번만 로드
   - 런타임 수정 불필요

3. **기존 코드 유지**
   - 이미 v1 기반으로 작성됨
   - 마이그레이션 비용 높음

4. **간단한 Override**
   ```python
   policy = ConfigLoader.load(
       "config.yaml",
       model=ImagePolicy,
       max_width=2048
   )
   ```

### cfg_utils_v2를 사용하는 경우 ✅

1. **다양한 소스 병합**
   ```python
   loader = ConfigLoader(
       base_sources=[(ImagePolicy(), "image")],
       override_sources=[
           ("base.yaml", "image"),
           ("dev.yaml", "image"),
           ({"max_width": 2048}, "image")
       ]
   )
   ```

2. **런타임 수정 필요**
   ```python
   loader.override("image__quality", 95)
   ```

3. **환경 변수 통합**
   ```python
   loader = ConfigLoader(
       base_sources=[(ImagePolicy(), "image")],
       env=["env.yaml"],
       env_os=["DEBUG", "LOG_LEVEL"]
   )
   ```

4. **상태 유지 필요**
   ```python
   state = loader.get_state()
   # ... 여러 작업 ...
   state.set("image__max_width", 4096)
   ```

5. **타입 자동 판단 활용**
   ```python
   loader = ConfigLoader(
       override_sources=[
           ("config.yaml", "image"),      # YAML
           ({"max_width": 2048}, "image"), # Dict
           (Path("final.yaml"), "image")   # Path
       ]
   )
   # → 자동으로 타입 판단하여 처리
   ```

6. **BaseModel Policy 중심 설계**
   ```python
   # Policy 클래스가 기본값 제공
   loader = ConfigLoader(
       base_sources=[
           (ImagePolicy(), "image"),
           (OcrPolicy(), "ocr"),
           (OverlayPolicy(), "overlay")
       ],
       override_sources=[("config.yaml", None)]
   )
   ```

---

## 정리

| 구분 | cfg_utils (v1) | cfg_utils_v2 |
|------|----------------|--------------|
| **설계 철학** | Function-Oriented | Object-Oriented |
| **주 용도** | YAML 로드 + 정규화 | 통합 Config 관리 |
| **장점** | 간단, 직관적 | 유연, 강력 |
| **단점** | 상태 없음, 1회성 | 초기 코드 길어짐 |
| **적합한 경우** | 단순 YAML 로드 | 복잡한 Config 관리 |
| **마이그레이션** | - | 패턴 참고 |

### 권장사항

- **신규 프로젝트**: **cfg_utils_v2** 사용 권장
  - 더 유연하고 확장 가능
  - 환경 변수 통합
  - 런타임 수정 지원

- **기존 프로젝트**: **cfg_utils (v1)** 유지
  - 단순한 경우 마이그레이션 불필요
  - 복잡도가 증가하면 v2 고려

- **혼용**: 가능
  - 모듈별로 다르게 사용 가능
  - 점진적 마이그레이션 가능
