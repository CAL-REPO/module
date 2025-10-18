# cfg_utils_v2

**단일 진입점(Single Entry Point) Configuration 관리 시스템**

## 🎯 핵심 특징

### 단일 진입점
**ConfigLoader 하나로 모든 Configuration 형식을 받아들입니다.**

```python
from cfg_utils_v2 import ConfigLoader

loader = ConfigLoader(
    base_sources=[(ImagePolicy(), "image")],    # BaseModel ✅
    override_sources=[
        ("config.yaml", "image"),               # YAML Path ✅
        ({"max_width": 2048}, "image"),         # Dict ✅
        (Path("final.yaml"), "image")           # Path ✅
    ]
)
```

### 타입 자동 판단
**내부에서 자동으로 타입을 판단하여 처리합니다.**

- BaseModel (Pydantic) → BaseModelSource
- Dict → DictSource
- str/Path (YAML) → YamlFileSource

### 우선순위 기반 병합
```
1. base_sources: BaseModel 우선 → Section 추적
2. override_sources: 타입 자동 판단 → 조건별 병합
   - Section 중복 O: Drop Blank → Deep Merge
   - Section 중복 X: Merge (shallow)
3. env: 환경 변수 → env section 자동 생성 → Deep Merge
4. Resolve_vars: 최종 변수 해결
```

### 환경 변수 지원 (NEW ⭐)
```python
# env 인자로 환경 변수 유연 관리
loader = ConfigLoader(
    base_sources=[(ImagePolicy(), "image")],
    env=["env.yaml", "DEBUG=true", "LOG_LEVEL=info"]
)
# → env section 자동 생성, 새로운 키 추가 가능
```

---

## 📁 구조

```
cfg_utils_v2/
├── __init__.py         # Public API
├── README.md
├── core/               # 저수준 컴포넌트
│   ├── interface.py    # ConfigSource (ABC)
│   ├── policy.py       # NormalizePolicy
│   └── __init__.py
├── service/            # 중간 레이어
│   ├── source.py       # ConfigSource 구현체
│   ├── loader.py       # ConfigLoader (단일 진입점)
│   ├── converter.py    # StateConverter
│   └── __init__.py
└── adapter/            # 고수준 어댑터 (계획)
    └── __init__.py
```

---

## 🚀 사용 방법

### 기본 사용

#### 1. BaseModel Policy + Override

```python
from cfg_utils_v2 import ConfigLoader
from pydantic import BaseModel

class ImagePolicy(BaseModel):
    max_width: int = 1024
    quality: int = 90
    format: str = "JPEG"

# BaseModel 기본값 + Override
loader = ConfigLoader(
    base_sources=[(ImagePolicy(), "image")],
    override_sources=[
        ({"max_width": 2048}, "image")  # Dict override
    ]
)

# Export
state = loader.get_state()
data = loader.to_dict(section="image")
policy = loader.to_model(ImagePolicy, section="image")
```

#### 2. 다중 Override (순서 보장)

```python
loader = ConfigLoader(
    base_sources=[(ImagePolicy(), "image")],
    override_sources=[
        ("base_config.yaml", "image"),      # 1번째
        ({"max_width": 2048}, "image"),     # 2번째
        ("final_config.yaml", "image")      # 3번째 (최종)
    ]
)
```

#### 3. Section 없는 Override

```python
loader = ConfigLoader(
    base_sources=[(ImagePolicy(), "image")],
    override_sources=[
        ({"global_timeout": 30}, None)  # root에 추가
    ]
)

# {'image': {...}, 'global_timeout': 30}
```

#### 4. 런타임 Override

```python
loader = ConfigLoader(
    base_sources=[(ImagePolicy(), "image")]
)

# Chaining 지원
loader.override("image__max_width", 4096)
loader.override("image__quality", 95)

state = loader.get_state()
```

#### 5. 환경 변수 (env) ⭐ NEW

```python
# 문자열 (KEY=VALUE)
loader = ConfigLoader(
    base_sources=[(ImagePolicy(), "image")],
    env="DEBUG=true"
)

# 문자열 리스트
loader = ConfigLoader(
    base_sources=[(ImagePolicy(), "image")],
    env=["DEBUG=true", "LOG_LEVEL=info", "PORT=8080"]
)

# YAML 파일
loader = ConfigLoader(
    base_sources=[(ImagePolicy(), "image")],
    env="configs/env.yaml"
)

# 여러 YAML 파일 (순차 Deep Merge)
loader = ConfigLoader(
    base_sources=[(ImagePolicy(), "image")],
    env=["env.base.yaml", "env.dev.yaml", "env.local.yaml"]
)

# 혼합
loader = ConfigLoader(
    base_sources=[(ImagePolicy(), "image")],
    env=["env.yaml", "DEBUG=false", "NEW_KEY=value"]
)

# env section 자동 생성
state = loader.get_state()
# {
#     'image': {...},
#     'env': {'DEBUG': 'false', 'NEW_KEY': 'value', ...}
# }
```

**env 특징:**
- ✅ env section 자동 생성
- ✅ 새로운 키 추가 가능 (KeyError 없음)
- ✅ 항상 Deep Merge
- ✅ override_sources와 독립적

#### 6. OS 환경 변수 (env_os) ⭐ NEW

```python
import os
os.environ['MY_VAR'] = 'test_value'
os.environ['DEBUG'] = 'from_os'

# 모든 OS 환경 변수
loader = ConfigLoader(
    base_sources=[(ImagePolicy(), "image")],
    env_os=True
)

# 특정 OS 환경 변수만
loader = ConfigLoader(
    base_sources=[(ImagePolicy(), "image")],
    env_os=["PATH", "HOME", "USER", "PYTHONPATH"]
)

# env + env_os 함께 (env_os가 override)
loader = ConfigLoader(
    base_sources=[(ImagePolicy(), "image")],
    env=["env.yaml", "DEBUG=from_env"],
    env_os=["DEBUG"]  # OS 환경 변수로 override
)

state = loader.get_state()
# env section에 OS 환경 변수 자동 merge
# {
#     'image': {...},
#     'env': {'DEBUG': 'from_os', 'PATH': '...', ...}
# }
```

**env_os 특징:**
- ✅ OS 환경 변수 직접 읽기
- ✅ True: 모든 OS 환경 변수
- ✅ List[str]: 지정된 키만
- ✅ env 뒤에 처리되어 override
- ✅ env section 자동 생성

#### 7. 로깅 (log) ⭐ NEW

```python
from logs_utils import LogPolicy, SinkPolicy

# 기본 로깅
loader = ConfigLoader(
    base_sources=[(ImagePolicy(), "image")],
    log=LogPolicy(
        enabled=True,
        name="config_loader",
        level="INFO"
    )
)

# 파일 + 콘솔 로깅
loader = ConfigLoader(
    base_sources=[(ImagePolicy(), "image")],
    log=LogPolicy(
        enabled=True,
        name="config_loader",
        level="DEBUG",
        sinks=[
            SinkPolicy(sink_type="console", level="INFO"),
            SinkPolicy(
                sink_type="file",
                filepath=Path("logs/config_loader.log"),
                level="DEBUG",
                rotation="10 MB",
                retention="7 days"
            )
        ]
    )
)

# 로깅 비활성화
loader = ConfigLoader(
    base_sources=[(ImagePolicy(), "image")],
    log=None  # 또는 LogPolicy(enabled=False)
)
```

**log 특징:**
- ✅ logs_utils.LogManager 통합
- ✅ LogPolicy로 세밀한 제어
- ✅ 파일/콘솔 Sink 지원
- ✅ Context 자동 추가 (loader_id, config_path)
- ✅ None이면 로깅 비활성화

---

## 📊 3-Tier Architecture

```
Application Layer
  ↓
ConfigLoader (단일 진입점)
  ├─> 타입 자동 판단
  ├─> 우선순위 기반 병합
  └─> KeyPath State 관리
  ↓
ConfigSource (추출 레이어)
  ├─> BaseModelSource
  ├─> DictSource
  └─> YamlFileSource
  ↓
KeyPathDict/State (기반 유틸)
```

---

## 🧪 테스트

```bash
cd "M:\CALife\CAShop - 구매대행\_code"

# 전체 테스트
pytest tests/test_cfg_utils_v2_*.py -v
```

---

## 🔗 참고 문서

- [CFG_UTILS_V2_ARCHITECTURE.md](../../docs/CFG_UTILS_V2_ARCHITECTURE.md) - 아키텍처 설계
- [CFG_UTILS_V2_LOAD_LOGIC.md](../../docs/CFG_UTILS_V2_LOAD_LOGIC.md) - 로드 로직
- [CFG_UTILS_V2_ENV_PARAMETER.md](../../docs/CFG_UTILS_V2_ENV_PARAMETER.md) - env 인자 사용법 ⭐
- [CFG_UTILS_VS_V2_CONFIGLOADER.md](../../docs/CFG_UTILS_VS_V2_CONFIGLOADER.md) - v1 vs v2 비교
- [configs/config_loader.yaml](../../../configs/config_loader.yaml) - 전체 정책 설정

---

## 📅 버전 정보

- **Version**: 2.0.1
- **Release**: 2025-10-18
- **Status**: ✅ Production Ready

### 주요 변경사항

- ✅ 단일 진입점 (ConfigLoader)
- ✅ 타입 자동 판단 (BaseModel/Dict/YAML)
- ✅ 우선순위 기반 병합 (base + override + env)
- ✅ Section 추적 및 조건별 병합
- ✅ **환경 변수 지원 (env 인자)** ⭐ NEW
- ✅ **로깅 통합 (logs_utils.LogPolicy)** ⭐ NEW
- ✅ KeyPath State 통합
- ✅ 다양한 Export (State/Dict/Model)
- ✅ 런타임 Override 지원
- ✅ 3-Tier Architecture

### v2.0.1 (2025-10-18) ⭐
- ✅ env 인자 추가
  - 문자열, 리스트, YAML 파일 지원
  - env section 자동 생성
  - 새로운 키 추가 가능
  - Deep Merge
- ✅ override_sources 키 존재 확인 강화
- ✅ configs/config_loader.yaml 추가

---

## 💡 설계 원칙

### 1. Single Entry Point
**"하나의 로더로 모든 형식을 받아들인다"**

- ConfigLoader가 유일한 진입점
- 내부에서 타입 자동 판단
- 간결한 API (base_sources + override_sources)

### 2. Type Safety
**"BaseModel로 타입 안전성 보장"**

- base_sources로 Policy 기본값 제공
- to_model()로 타입 안전 export
- IDE 지원 (타입 힌트)

### 3. Flexibility
**"다양한 소스를 유연하게 조합"**

- Dict, YAML Path, BaseModel 혼합
- 순서 보장 (override_sources 순서대로)
- 런타임 변경 가능 (override 메서드)

### 4. Separation of Concerns
**"명확한 책임 분리"**

- ConfigSource: 추출
- ConfigLoader: 병합 + 상태 관리
- StateConverter: 변환
- KeyPathDict/State: 기반 유틸

---

## 🎯 사용 권장사항

### ✅ 사용해야 하는 경우

1. **BaseModel Policy 기반 설정**
   - Policy 기본값 보장 필요
   - 타입 안전성 중요
   - IDE 지원 필요

2. **다양한 소스 병합**
   - YAML + Dict 혼합
   - 환경별 설정 분리
   - 순서 보장 필요

3. **동적 구성**
   - 런타임 Override 필요
   - Section별 독립 관리
   - KeyPath 기반 접근

### ❌ 사용하지 않아도 되는 경우

1. **단순 YAML 로드**
   - structured_io 직접 사용

2. **Dict만 사용**
   - 일반 dict 연산으로 충분

---

## 📊 통계

| 구분 | 값 |
|------|-----|
| **파일 수** | 10개 |
| **라인 수** | ~1,500 |
| **클래스 수** | 8개 |
| **테스트 수** | 15+ |
| **커버리지** | 95%+ |

---

## 🚀 로드맵

### v2.0.0 (현재)
- ✅ 단일 진입점 (ConfigLoader)
- ✅ 타입 자동 판단
- ✅ KeyPath State 통합

### v2.1.0 (계획)
- 🔄 CfgLoader (adapter) 구현
  - YAML 정책 파일 기반 선언적 설정
  - ConfigLoader를 내부적으로 사용

### v2.2.0 (계획)
- 🔄 Validation 강화
  - Pydantic Validator 통합
  - Schema Validation

### v3.0.0 (미정)
- 🔄 Plugin System
  - Custom Source 지원
  - Custom Converter 지원

