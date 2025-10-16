# 🔬 cfg_utils 모듈 정책값 및 내부 구조 심층 고찰

**작성일**: 2025-10-16  
**분석 기준**: 실제 코드 분석 기반  
**목적**: cfg_utils의 내부 구조, 정책값, 설계 패턴 완전 분석

---

## 📐 1. cfg_utils 모듈 구조 (Physical Structure)

### 1.1 디렉토리 구조

```
cfg_utils/
├── __init__.py              # Public API (ConfigLoader, ConfigNormalizer, ConfigPolicy)
├── configs/
│   └── config_loader.yaml   # ConfigLoader 자체의 설정 (Bootstrap Config)
├── core/
│   └── policy.py            # ConfigPolicy 정의 (데이터 모델)
└── services/
    ├── config_loader.py     # 설정 로딩 총괄 서비스
    ├── helpers.py           # 공통 유틸리티 함수
    ├── merger.py            # 타입별 병합 전략 (Strategy Pattern)
    └── normalizer.py        # 정규화 서비스 (Reference/Blank 처리)
```

### 1.2 Public API (외부 노출)

```python
# __init__.py에서 re-export
from cfg_utils import (
    ConfigLoader,        # 설정 로딩 진입점
    ConfigNormalizer,    # 정규화 서비스
    ConfigPolicy         # 정책 데이터 모델
)
```

**설계 의도**:
- ✅ **최소 노출**: 내부 구현(merger, helpers)은 숨김
- ✅ **명확한 책임**: 3개 클래스만 외부에 노출
- ✅ **단일 진입점**: ConfigLoader.load()가 유일한 시작점

### 1.3 계층 구조 (Layered Architecture)

```
┌─────────────────────────────────────────────┐
│  Public API Layer (외부 인터페이스)          │
│  - ConfigLoader.load() [static method]     │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  Service Layer (비즈니스 로직)               │
│  - ConfigLoader (instance methods)         │
│  - ConfigNormalizer                        │
│  - Merger (Strategy Pattern)               │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  Helper Layer (재사용 함수)                  │
│  - apply_overrides                         │
│  - load_source                             │
│  - merge_sequence                          │
│  - model_to_dict                           │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  Core Layer (데이터 모델)                    │
│  - ConfigPolicy (Pydantic BaseModel)       │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  External Dependencies                      │
│  - structured_io (YamlParser)              │
│  - keypath_utils (KeyPathDict)             │
│  - unify_utils (ReferenceResolver)         │
│  - data_utils (DictOps)                    │
└─────────────────────────────────────────────┘
```

---

## 🎯 2. ConfigPolicy 정책값 완전 분석

### 2.1 ConfigPolicy 필드 정의

```python
class ConfigPolicy(BaseModel):
    """설정 로딩 동작 정책"""
    
    # ==========================================
    # 1. ConfigLoader 자체 설정 경로
    # ==========================================
    config_loader_cfg_path: Optional[str] = Field(
        default="configs/config_loader.yaml",
        description="ConfigLoader 자체의 설정 파일 경로 (Bootstrap)"
    )
    
    # ==========================================
    # 2. YAML 파싱 정책 (structured_io 위임)
    # ==========================================
    yaml: Optional[BaseParserPolicy] = Field(
        default_factory=lambda: BaseParserPolicy(
            source_paths=[],
            enable_env=False,
            enable_include=True,
            enable_placeholder=False,
            enable_reference=True,
            safe_mode=True,
            encoding="utf-8",
            on_error="ignore",
            sort_keys=False,
            default_flow_style=False,
            indent=2
        ),
        description="YAML 파싱 정책"
    )
    
    # ==========================================
    # 3. 정규화 옵션
    # ==========================================
    drop_blanks: bool = Field(
        default=True,
        description="공백 값 제거 (None, '', [], {}, Blank 등)"
    )
    
    resolve_reference: bool = Field(
        default=True,
        description="Reference 해석 활성화 (${ref:key.path} 패턴)"
    )
    
    # ==========================================
    # 4. 병합 옵션
    # ==========================================
    merge_order: Literal["base→yaml→arg"] = Field(
        default="base→yaml→arg",
        description="병합 순서 (현재는 이 순서만 지원)"
    )
    
    merge_mode: Literal["deep", "shallow"] = Field(
        default="deep",
        description="병합 모드 (deep: 중첩 병합, shallow: 최상위만)"
    )
    
    # ==========================================
    # 5. KeyPath 처리 정책 (unify_utils 위임)
    # ==========================================
    keypath: KeyPathNormalizePolicy = Field(
        default_factory=lambda: KeyPathNormalizePolicy(
            recursive=False,
            strict=False,
            sep="__",          # ✅ 프로젝트 관례
            collapse=True,
            accept_dot=True,
            escape_char="\\"
        ),
        description="KeyPath 정규화 정책 (__ 구분자 사용)"
    )
    
    # ==========================================
    # 6. Reference 해석 컨텍스트
    # ==========================================
    reference_context: dict[str, Any] = Field(
        default_factory=dict,
        description="Reference 해석 시 추가 컨텍스트 (paths_dict 등)"
    )
```

### 2.2 정책값의 기본값 분석

#### ✅ **config_loader.yaml 기본값**
```yaml
config_loader:
  yaml:
    source_paths: []          # ← 비어있음 (테스트용)
    enable_env: false         # ← ${} 패턴이 환경변수로 오해되지 않도록
    enable_include: true      # ← !include 지시자 활성화
    enable_placeholder: false # ← ${} reference 침범 방지
    enable_reference: true    # ← ${ref:...} 패턴 활성화
    safe_mode: true
    encoding: "utf-8"
    on_error: "ignore"
    sort_keys: false
    default_flow_style: false
    indent: 2
  
  drop_blanks: true           # ← None, '', [], {} 제거
  resolve_reference: true     # ← ${ref:key.path} 해석
  
  merge_order: "base→yaml→arg"
  merge_mode: "deep"          # ← 중첩 dict까지 병합
```

**설계 의도**:
1. **source_paths: []**: ConfigLoader 자신은 파일 소스 없음 (Bootstrap)
2. **enable_env: false**: `${PATH}` 같은 패턴이 환경변수로 오해되지 않도록
3. **enable_placeholder: false**: `${}` 패턴이 placeholder로 처리되지 않도록
4. **enable_reference: true**: `${ref:key.path}` 만 활성화

### 2.3 정책값의 우선순위 (Override Priority)

```
낮음 ─────────────────────────────────────────────────────> 높음

1. ConfigPolicy 기본값 (Pydantic Field defaults)
   ↓
2. config_loader.yaml (Bootstrap Config)
   ↓
3. policy_overrides 파라미터 (런타임 개별 오버라이드)
   ↓
4. **overrides (최종 데이터 오버라이드)
```

**예시**:
```python
# 1. ConfigPolicy 기본값
config = ConfigLoader.load("config.yaml")
# → drop_blanks=True (기본값)

# 2. config_loader.yaml로 오버라이드
# config_loader.yaml에 drop_blanks: false 설정
config = ConfigLoader.load("config.yaml")
# → drop_blanks=False

# 3. policy_overrides로 오버라이드
config = ConfigLoader.load(
    "config.yaml",
    policy_overrides={"drop_blanks": True}
)
# → drop_blanks=True (policy_overrides가 최우선)

# 4. **overrides는 데이터에만 적용 (Policy가 아님)
config = ConfigLoader.load(
    "config.yaml",
    model=MyPolicy,
    image__max_width=1024  # ← 데이터 오버라이드
)
# → config.image.max_width = 1024
```

---

## 🏗️ 3. 내부 구조 분석 (Internal Architecture)

### 3.1 ConfigLoader 클래스 구조

#### **Public API**:
```python
class ConfigLoader:
    # ==========================================
    # Static Method (유일한 진입점)
    # ==========================================
    @staticmethod
    @overload
    def load(cfg_like, *, model: Type[T], ...) -> T: ...
    
    @staticmethod
    @overload
    def load(cfg_like, *, model: None = None, ...) -> dict: ...
    
    @staticmethod
    def load(cfg_like, *, model, policy_overrides, **overrides):
        """설정 로딩 메인 메서드"""
        # 1. 타입별 분기
        # 2. ConfigLoader 인스턴스 생성 (필요 시)
        # 3. 최종 dict/model 반환
```

#### **Instance Methods (Private)**:
```python
    def __init__(self, cfg_like, *, policy_overrides):
        """ConfigLoader 인스턴스 생성"""
        self.cfg_like = cfg_like
        self.policy = self._load_loader_policy(policy_overrides)
        self.parser = YamlParser(policy=self.policy.yaml)
        self.data = KeyPathDict(key_separator=self.policy.keypath.sep)
    
    def _load_loader_policy(self, policy_overrides) -> ConfigPolicy:
        """config_loader.yaml 로드 → policy_overrides 적용"""
        # 1. config_loader.yaml 읽기
        # 2. ConfigPolicy 생성
        # 3. policy_overrides 병합
        # 4. 최종 ConfigPolicy 반환
    
    def _merge_sources(self):
        """cfg_like를 self.data에 병합"""
        # MergerFactory로 타입별 Merger 선택
        # Merger.merge() 호출
    
    def _as_dict_internal(self, **overrides) -> dict:
        """dict 반환 (정규화 + overrides 적용)"""
        self._merge_sources()
        normalized = ConfigNormalizer(self.policy).apply(self.data.data)
        if overrides:
            normalized = apply_overrides(normalized, overrides, policy=self.policy)
        return normalized
    
    def _as_model_internal(self, model: Type[T], **overrides) -> T:
        """Pydantic 모델 반환"""
        config_dict = self._as_dict_internal(**overrides)
        return model(**config_dict)
```

### 3.2 Merger Strategy Pattern

#### **BaseMerger (추상 클래스)**:
```python
class BaseMerger(ABC):
    def __init__(self, loader: ConfigLoader):
        self.loader = loader  # ConfigLoader 인스턴스 참조
    
    @abstractmethod
    def merge(self, source: Any, data: KeyPathDict, deep: bool):
        """소스를 data에 병합"""
        ...
```

#### **Concrete Mergers**:
```python
# 1. DictMerger: dict → KeyPathDict
class DictMerger(BaseMerger):
    def merge(self, source: dict, data: KeyPathDict, deep: bool):
        data.merge(source, deep=deep)

# 2. ModelMerger: BaseModel → dict → KeyPathDict
class ModelMerger(BaseMerger):
    def merge(self, source: BaseModel, data: KeyPathDict, deep: bool):
        converted = model_to_dict(source, drop_none=True)
        data.merge(converted, deep=deep)

# 3. PathMerger: Path/str → YAML → dict → KeyPathDict
class PathMerger(BaseMerger):
    def merge(self, source: str | Path, data: KeyPathDict, deep: bool):
        parsed = load_source(source, self.loader.parser)
        if parsed:
            data.merge(parsed, deep=deep)

# 4. SequenceMerger: List[Any] → 각 항목 재귀 병합
class SequenceMerger(BaseMerger):
    def merge(self, source: Sequence, data: KeyPathDict, deep: bool):
        for item in source:
            merger = MergerFactory.get(item, self.loader)
            merger.merge(item, data, deep)
```

#### **MergerFactory (팩토리)**:
```python
class MergerFactory:
    @staticmethod
    def get(source: Any, loader: ConfigLoader) -> BaseMerger:
        if isinstance(source, dict):
            return DictMerger(loader)
        if isinstance(source, BaseModel):
            return ModelMerger(loader)
        if isinstance(source, (str, Path)):
            return PathMerger(loader)
        if isinstance(source, Sequence):
            return SequenceMerger(loader)
        raise TypeError(f"Unsupported: {type(source)}")
```

**설계 장점**:
- ✅ **SRP**: 각 Merger는 하나의 타입만 처리
- ✅ **OCP**: 새 타입 추가 시 새 Merger만 추가
- ✅ **DIP**: ConfigLoader는 BaseMerger에만 의존

### 3.3 ConfigNormalizer 구조

```python
class ConfigNormalizer:
    def __init__(self, policy: ConfigPolicy):
        self.policy = policy
    
    def apply(self, data: dict) -> dict:
        """정규화 적용 (2단계)"""
        result = data.copy()
        
        # 1️⃣ Reference 해석
        if self.policy.resolve_reference:
            context = {**result, **self.policy.reference_context}
            result = ReferenceResolver(
                context,
                recursive=True,
                strict=False
            ).apply(result)
        
        # 2️⃣ Blank 필터링
        if self.policy.drop_blanks:
            result = DictOps.drop_blanks(result, deep=True)
        
        return result
```

**책임**:
- ✅ **Reference 해석**: `${ref:key.path}` → 실제 값으로 치환
- ✅ **Blank 제거**: None, '', [], {}, Blank 객체 제거
- ❌ **병합은 하지 않음**: 병합은 Merger가 담당

### 3.4 Helper Functions

```python
# 1. apply_overrides: KeyPath 기반 오버라이드
def apply_overrides(
    data: dict,
    overrides: dict,
    separator: str = ".",
    normalizer: Optional[KeyPathNormalizer] = None,
    policy: Optional[ConfigPolicy] = None
) -> dict:
    """
    overrides = {"a.b.c": 1, "x__y": 2}
    → data["a"]["b"]["c"] = 1
    → data["x"]["y"] = 2
    """

# 2. load_source: Path/str → dict
def load_source(src: str | Path, parser: YamlParser) -> dict:
    """
    Path.exists() → 파일 읽기 → parser.parse()
    else → raw YAML string → parser.parse()
    """

# 3. merge_sequence: List[Path] → 순차 병합
def merge_sequence(
    seq: Iterable[str | Path],
    parser: YamlParser,
    deep: bool
) -> dict:
    """
    ["base.yaml", "prod.yaml"] → 순차 deep merge
    """

# 4. model_to_dict: BaseModel → dict
def model_to_dict(model: BaseModel, drop_none: bool = True) -> dict:
    """
    model.model_dump() → None 제거
    """
```

---

## 🔄 4. 설정 로딩 플로우 (Complete Flow)

### 4.1 시나리오 1: Path 입력 (가장 일반적)

```python
config = ConfigLoader.load("config.yaml", model=MyPolicy, key="value")
```

**플로우**:
```
1. ConfigLoader.load() [static]
   ├─ isinstance(cfg_like, (str, Path)) → True
   └─ loader = ConfigLoader("config.yaml", policy_overrides=None)

2. ConfigLoader.__init__()
   ├─ self.cfg_like = "config.yaml"
   ├─ self.policy = self._load_loader_policy(None)
   │  ├─ config_loader.yaml 읽기
   │  ├─ ConfigPolicy 생성
   │  └─ return ConfigPolicy(...)
   ├─ self.parser = YamlParser(policy=self.policy.yaml)
   └─ self.data = KeyPathDict(key_separator="__")

3. loader._as_model_internal(MyPolicy, key="value")
   ├─ config_dict = loader._as_dict_internal(key="value")
   │  ├─ self._merge_sources()
   │  │  ├─ merger = MergerFactory.get("config.yaml", loader)
   │  │  │  └─ return PathMerger(loader)
   │  │  └─ merger.merge("config.yaml", self.data, deep=True)
   │  │     ├─ parsed = load_source("config.yaml", parser)
   │  │     │  ├─ text = Path("config.yaml").read_text()
   │  │     │  └─ return parser.parse(text)
   │  │     └─ self.data.merge(parsed, deep=True)
   │  │
   │  ├─ normalized = ConfigNormalizer(policy).apply(self.data.data)
   │  │  ├─ ReferenceResolver.apply() [if resolve_reference=True]
   │  │  └─ DictOps.drop_blanks() [if drop_blanks=True]
   │  │
   │  └─ normalized = apply_overrides(normalized, {"key": "value"}, policy)
   │     ├─ kp = KeyPathDict(normalized)
   │     ├─ kp.apply_overrides({"key": "value"}, normalizer)
   │     └─ return kp.data
   │
   └─ return MyPolicy(**config_dict)
```

### 4.2 시나리오 2: 여러 파일 병합

```python
config = ConfigLoader.load(["base.yaml", "prod.yaml"], model=MyPolicy)
```

**플로우**:
```
1. ConfigLoader.load() [static]
   ├─ isinstance(cfg_like, (list, tuple)) → True
   ├─ temp_parser = YamlParser(ConfigPolicy().yaml)
   ├─ merged_dict = merge_sequence(["base.yaml", "prod.yaml"], temp_parser, deep=True)
   │  ├─ merged = {}
   │  ├─ for item in ["base.yaml", "prod.yaml"]:
   │  │  ├─ d = load_source(item, parser)
   │  │  ├─ temp = KeyPathDict(merged)
   │  │  ├─ temp.merge(d, deep=True)
   │  │  └─ merged = temp.data
   │  └─ return merged
   │
   └─ return MyPolicy(**merged_dict)
```

### 4.3 시나리오 3: policy_overrides 사용

```python
config = ConfigLoader.load(
    "config.yaml",
    model=MyPolicy,
    policy_overrides={"drop_blanks": False}
)
```

**플로우**:
```
1. ConfigLoader.load() [static]
   ├─ temp_policy = ConfigPolicy(**policy_overrides)  # 임시 정책
   └─ loader = ConfigLoader("config.yaml", policy_overrides={"drop_blanks": False})

2. ConfigLoader.__init__()
   ├─ self.policy = self._load_loader_policy({"drop_blanks": False})
   │  ├─ loader_path = "configs/config_loader.yaml"
   │  ├─ loader_config = load_source(loader_path, temp_parser)
   │  ├─ loader_config.update(policy_overrides)  # ← drop_blanks: False 적용
   │  └─ return ConfigPolicy(**loader_config)
   │
   └─ ...

3. ConfigNormalizer.apply()
   ├─ if self.policy.resolve_reference: ...
   └─ if self.policy.drop_blanks:  # ← False이므로 Skip
       # (drop_blanks 실행 안 됨)
```

### 4.4 시나리오 4: None 입력 (특수 케이스)

```python
config = ConfigLoader.load(
    None,
    model=MyPolicy,
    policy_overrides={"yaml.source_paths": ["config.yaml"]}
)
```

**플로우**:
```
1. ConfigLoader.load() [static]
   ├─ cfg_like is None → True
   ├─ policy_overrides에 "yaml.source_paths" 존재 → True
   ├─ loader = ConfigLoader({}, policy_overrides={"yaml.source_paths": [...]})
   │  ├─ self.cfg_like = {}
   │  └─ self.policy = self._load_loader_policy(policy_overrides)
   │     ├─ config_loader.yaml 읽기
   │     ├─ loader_config["yaml"]["source_paths"] = ["config.yaml"]
   │     └─ return ConfigPolicy(**loader_config)
   │
   └─ loader._as_model_internal(MyPolicy, **overrides)
      # (source_paths는 structured_io에서 자동 로드)
```

---

## 🎨 5. 설계 패턴 분석

### 5.1 사용된 디자인 패턴

#### 1. **Strategy Pattern (전략 패턴)**
```python
# Merger가 Strategy
BaseMerger (interface)
├─ DictMerger (concrete strategy)
├─ ModelMerger (concrete strategy)
├─ PathMerger (concrete strategy)
└─ SequenceMerger (concrete strategy)

# MergerFactory가 Context
MergerFactory.get(source) → 타입에 맞는 Strategy 반환
```

**장점**:
- ✅ 타입별 병합 로직 캡슐화
- ✅ 새 타입 추가 시 기존 코드 수정 불필요 (OCP)

#### 2. **Facade Pattern (파사드 패턴)**
```python
# ConfigLoader.load()가 Facade
ConfigLoader.load() → 복잡한 내부 로직 숨김
├─ ConfigPolicy 로딩
├─ YamlParser 생성
├─ Merger 선택 및 병합
├─ ConfigNormalizer 적용
└─ Pydantic 모델 변환
```

**장점**:
- ✅ 사용자는 간단한 API만 사용
- ✅ 내부 복잡도 숨김

#### 3. **Factory Pattern (팩토리 패턴)**
```python
# MergerFactory
MergerFactory.get(source, loader) → BaseMerger

# 타입 기반 객체 생성
if isinstance(source, dict):
    return DictMerger(loader)
elif isinstance(source, BaseModel):
    return ModelMerger(loader)
# ...
```

**장점**:
- ✅ 객체 생성 로직 중앙화
- ✅ 타입 체크를 Factory에 위임

#### 4. **Template Method Pattern (템플릿 메서드)**
```python
# ConfigLoader._as_dict_internal()
def _as_dict_internal(self, **overrides):
    # 1. 병합 (하위 클래스가 구현 가능)
    self._merge_sources()
    
    # 2. 정규화 (항상 실행)
    normalized = ConfigNormalizer(self.policy).apply(self.data.data)
    
    # 3. 오버라이드 (옵션)
    if overrides:
        normalized = apply_overrides(normalized, overrides)
    
    return normalized
```

**장점**:
- ✅ 알고리즘 뼈대 고정
- ✅ 각 단계 독립적으로 테스트 가능

#### 5. **Dependency Injection (의존성 주입)**
```python
# ConfigNormalizer는 Policy를 주입받음
class ConfigNormalizer:
    def __init__(self, policy: ConfigPolicy):
        self.policy = policy  # ← DI
    
    def apply(self, data: dict):
        # Policy에 따라 동작 변경
        if self.policy.resolve_reference:
            # ...
```

**장점**:
- ✅ 테스트 시 Mock Policy 주입 가능
- ✅ 런타임에 Policy 변경 가능

### 5.2 SOLID 원칙 준수도

| 원칙 | 설명 | 준수도 | 평가 |
|------|------|--------|------|
| **S**RP | 단일 책임 원칙 | ✅ 우수 | 각 클래스가 명확한 책임 |
| **O**CP | 개방-폐쇄 원칙 | ✅ 우수 | 새 Merger 추가 시 기존 코드 불변 |
| **L**SP | 리스코프 치환 원칙 | ✅ 우수 | BaseMerger 하위 클래스 완전 대체 가능 |
| **I**SP | 인터페이스 분리 원칙 | ✅ 우수 | BaseMerger는 단일 메서드만 |
| **D**IP | 의존성 역전 원칙 | ✅ 우수 | ConfigLoader는 BaseMerger에 의존 |

---

## 🧩 6. 외부 의존성 분석

### 6.1 직접 의존성 (Direct Dependencies)

```python
# cfg_utils가 직접 import하는 모듈들

1. structured_io
   ├─ YamlParser: YAML 파싱
   └─ BaseParserPolicy: 파싱 정책

2. keypath_utils
   ├─ KeyPathDict: KeyPath 기반 dict 조작
   └─ KeyPathState: KeyPath 상태 관리

3. unify_utils
   ├─ ReferenceResolver: ${ref:...} 해석
   ├─ KeyPathNormalizer: KeyPath 정규화
   └─ KeyPathNormalizePolicy: 정규화 정책

4. data_utils
   └─ DictOps: dict 유틸리티 (drop_none, drop_blanks)

5. Pydantic
   └─ BaseModel: 데이터 검증
```

### 6.2 의존성 방향 (Dependency Flow)

```
cfg_utils (최상위)
    │
    ├─> structured_io (YAML 파싱)
    │       └─> fso_utils (파일 읽기)
    │
    ├─> keypath_utils (KeyPath 처리)
    │       └─> type_utils (타입 추론)
    │
    ├─> unify_utils (정규화)
    │       ├─> keypath_utils
    │       └─> type_utils
    │
    └─> data_utils (dict 조작)
            └─> type_utils
```

### 6.3 순환 의존성 분석

#### ✅ **현재 상태: 순환 의존 없음**
```python
# cfg_utils → structured_io (O)
# structured_io → cfg_utils (X)

# cfg_utils → keypath_utils (O)
# keypath_utils → cfg_utils (X)

# 모든 의존성이 단방향
```

#### ⚠️ **잠재적 위험: TYPE_CHECKING 사용**
```python
# merger.py에서
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from modules.cfg_utils.services.config_loader import ConfigLoader

# 런타임에는 import 안 됨, 타입 힌트만 사용
# → 순환 의존 방지
```

---

## 📊 7. 정책값 변경 영향 분석

### 7.1 drop_blanks 변경 시 영향

```python
# drop_blanks=True (기본값)
config = {"a": None, "b": "", "c": [], "d": {}, "e": 1}
# → {"e": 1}

# drop_blanks=False
config = {"a": None, "b": "", "c": [], "d": {}, "e": 1}
# → {"a": None, "b": "", "c": [], "d": {}, "e": 1}
```

**영향 받는 컴포넌트**:
- ✅ ConfigNormalizer.apply() → DictOps.drop_blanks() 호출 여부
- ❌ Merger → 영향 없음 (병합만 담당)
- ❌ helpers → 영향 없음

### 7.2 resolve_reference 변경 시 영향

```python
# resolve_reference=True (기본값)
config = {"base": "/path", "full": "${ref:base}/file.txt"}
# → {"base": "/path", "full": "/path/file.txt"}

# resolve_reference=False
config = {"base": "/path", "full": "${ref:base}/file.txt"}
# → {"base": "/path", "full": "${ref:base}/file.txt"}
```

**영향 받는 컴포넌트**:
- ✅ ConfigNormalizer.apply() → ReferenceResolver.apply() 호출 여부
- ❌ Merger → 영향 없음
- ⚠️ structured_io → enable_reference와 혼동 주의!
  - **structured_io.enable_reference**: YAML 파일 내 reference 해석
  - **cfg_utils.resolve_reference**: 병합된 dict의 reference 해석

### 7.3 merge_mode 변경 시 영향

```python
# merge_mode="deep" (기본값)
base = {"a": {"b": 1}}
override = {"a": {"c": 2}}
# → {"a": {"b": 1, "c": 2}}

# merge_mode="shallow"
base = {"a": {"b": 1}}
override = {"a": {"c": 2}}
# → {"a": {"c": 2}}  # ← 최상위만 병합, 하위는 덮어씀
```

**영향 받는 컴포넌트**:
- ✅ 모든 Merger → merge() 메서드의 deep 파라미터
- ✅ KeyPathDict.merge() → deep 플래그 전달

### 7.4 keypath.sep 변경 시 영향

```python
# keypath.sep="__" (프로젝트 기본값)
overrides = {"a__b__c": 1}
# → {"a": {"b": {"c": 1}}}

# keypath.sep="."
overrides = {"a.b.c": 1}
# → {"a": {"b": {"c": 1}}}
```

**영향 받는 컴포넌트**:
- ✅ apply_overrides() → KeyPathNormalizer 생성 시 sep 사용
- ✅ KeyPathDict() → key_separator 파라미터
- ⚠️ 프로젝트 전체 관례와 일치해야 함 (copilot-instructions.md)

---

## 🎓 8. 모범 사례 (Best Practices)

### 8.1 ConfigPolicy 사용 패턴

#### ✅ **권장: 기본값 사용**
```python
# 대부분의 경우 기본값으로 충분
config = ConfigLoader.load("config.yaml", model=MyPolicy)
```

#### ✅ **권장: 개별 필드만 오버라이드**
```python
# drop_blanks만 변경
config = ConfigLoader.load(
    "config.yaml",
    model=MyPolicy,
    policy_overrides={"drop_blanks": False}
)
```

#### ⚠️ **주의: 전체 Policy 교체**
```python
# 모든 기본값 날아감!
custom_policy = ConfigPolicy(
    drop_blanks=False,
    resolve_reference=False
    # yaml은? keypath는? → 누락됨
)

# 대신 이렇게
custom_policy = ConfigPolicy(
    **ConfigPolicy().model_dump(),  # 기본값 유지
    drop_blanks=False               # 변경만
)
```

### 8.2 Overrides 사용 패턴

#### ✅ **권장: KeyPath 구분자 사용**
```python
# __ 구분자 (프로젝트 관례)
config = ConfigLoader.load(
    "config.yaml",
    model=MyPolicy,
    image__max_width=1024,
    source__path="/new/path"
)
```

#### ⚠️ **주의: . 구분자 (가능하지만 비권장)**
```python
# . 구분자도 작동하지만 프로젝트 관례 위반
config = ConfigLoader.load(
    "config.yaml",
    model=MyPolicy,
    **{"image.max_width": 1024}  # ← Dict로만 가능
)
```

### 8.3 여러 파일 병합 패턴

#### ✅ **권장: 순서 명시**
```python
# 순서가 중요! (나중 것이 덮어씀)
config = ConfigLoader.load(
    [
        "base.yaml",        # 기본 설정
        "dev.yaml",         # 개발 환경
        "local.yaml"        # 로컬 오버라이드
    ],
    model=MyPolicy
)
```

#### ❌ **비권장: 너무 많은 파일**
```python
# 파일이 너무 많으면 디버깅 어려움
config = ConfigLoader.load(
    [
        "base.yaml",
        "middleware.yaml",
        "db.yaml",
        "cache.yaml",
        "dev.yaml",
        "local.yaml"
        # ... 10개 넘으면 위험
    ],
    model=MyPolicy
)
```

---

## 🔍 9. 개선 방향 제안

### 9.1 즉시 개선 (High Priority)

#### **1. policy_overrides를 명시적 파라미터로**
```python
# Before: 불명확
config = ConfigLoader.load(
    "config.yaml",
    policy_overrides={"drop_blanks": False}
)

# After: 명시적
config = ConfigLoader.load(
    "config.yaml",
    drop_blanks=False,      # ← 직접 파라미터
    resolve_reference=True,
    merge_mode="deep"
)
```

#### **2. 로딩 결과 Dataclass화**
```python
@dataclass
class ConfigLoadResult:
    config: dict | BaseModel
    policy: ConfigPolicy
    loaded_files: List[Path]
    merge_stats: dict

# 사용
result = ConfigLoader.load_with_metadata("config.yaml")
print(f"Loaded from: {result.loaded_files}")
print(f"Merged {result.merge_stats['file_count']} files")
```

### 9.2 중기 개선 (Medium Priority)

#### **1. Policy 검증 강화**
```python
class ConfigPolicy(BaseModel):
    @model_validator(mode='after')
    def validate_combinations(self):
        # 논리적으로 불가능한 조합 검증
        if self.merge_mode == "shallow" and self.resolve_reference:
            warnings.warn("shallow merge + reference may not work as expected")
        return self
```

#### **2. 캐싱 추가**
```python
class ConfigLoader:
    _cache: Dict[str, dict] = {}
    
    @staticmethod
    def load(cfg_like, *, cache: bool = False, ...):
        if cache and isinstance(cfg_like, (str, Path)):
            key = str(Path(cfg_like).resolve())
            if key in ConfigLoader._cache:
                return ConfigLoader._cache[key]
        # ...
```

### 9.3 장기 개선 (Low Priority)

#### **1. 비동기 로딩**
```python
async def load_async(
    cfg_like: List[PathLike],
    *,
    model: Type[T],
    **overrides
) -> T:
    # 여러 파일 병렬 로드
    tasks = [asyncio.to_thread(load_source, path, parser) for path in cfg_like]
    results = await asyncio.gather(*tasks)
    # ...
```

---

## 📋 10. 최종 평가

### 10.1 강점 (Strengths)

| 항목 | 평가 | 근거 |
|------|------|------|
| **SRP 준수** | ⭐⭐⭐⭐⭐ | 각 클래스가 단일 책임 |
| **확장성** | ⭐⭐⭐⭐⭐ | Strategy 패턴으로 타입 추가 용이 |
| **타입 안전성** | ⭐⭐⭐⭐⭐ | Pydantic + Overload |
| **일관성** | ⭐⭐⭐⭐⭐ | 모든 모듈이 동일 패턴 |
| **테스트 가능성** | ⭐⭐⭐⭐☆ | DI 사용하지만 테스트 부족 |
| **문서화** | ⭐⭐⭐☆☆ | Docstring 있지만 예시 부족 |

### 10.2 약점 (Weaknesses)

| 항목 | 평가 | 개선 방안 |
|------|------|----------|
| **None 케이스 복잡** | ⚠️ | 명시적 메서드 추가 |
| **policy_overrides 암묵적** | ⚠️ | 직접 파라미터화 |
| **캐싱 부재** | ⚠️ | 옵션 캐싱 추가 |
| **비동기 미지원** | ⚠️ | async 버전 추가 |

### 10.3 종합 평가

**점수**: 92/100

**평가 요약**:
> cfg_utils는 SRP 원칙을 철저히 준수하며, Strategy 패턴과 Dependency Injection을 활용한 우수한 설계를 보여준다. 타입 안전성, 확장성, 일관성 모두 최상급이다. 다만 사용성 개선(policy_overrides, None 케이스)과 성능 최적화(캐싱, 비동기)가 필요하다.

---

## 🚀 11. 액션 플랜

### Phase 1: 즉시 실행 (1주)
- [ ] policy_overrides를 명시적 파라미터로 리팩토링
- [ ] None 케이스 전용 메서드 추가
- [ ] ConfigLoadResult Dataclass 추가
- [ ] 기본 테스트 코드 작성 (merger, normalizer)

### Phase 2: 중기 실행 (2주)
- [ ] Policy 검증 로직 추가 (@model_validator)
- [ ] 캐싱 메커니즘 구현 (선택적)
- [ ] 사용 예시 문서 작성 (README)
- [ ] 에러 메시지 개선

### Phase 3: 장기 실행 (1개월)
- [ ] 비동기 로딩 구현
- [ ] 성능 벤치마크
- [ ] 고급 기능 추가 (lazy loading 등)

---

**작성자**: GitHub Copilot  
**기준**: 실제 코드 분석  
**결론**: cfg_utils는 우수한 설계를 가진 핵심 인프라 모듈이며, 사용성 개선을 통해 더욱 강력해질 수 있다.
