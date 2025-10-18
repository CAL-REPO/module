# cfg_utils_v2 Configuration Guide

## 📋 목차
1. [정책 파일 구조](#정책-파일-구조)
2. [타입별 정책 설명](#타입별-정책-설명)
3. [사용 예시](#사용-예시)
4. [설계 원칙](#설계-원칙)

---

## 정책 파일 구조

### 📂 `configs/config_loader.yaml`

```yaml
source:                    # SourcePolicy - 통합 소스 정책
  base_model_normalizer:   # BaseModel 정규화 정책
  base_model_merge:        # BaseModel 병합 정책
  dict_normalizer:         # Dict 정규화 정책
  dict_merge:              # Dict 병합 정책
  yaml_parser:             # YAML 파서 정책
  yaml_normalizer:         # YAML 정규화 정책
  yaml_merge:              # YAML 병합 정책

keypath:                   # KeyPathStatePolicy
  separator: "__"

log:                       # LogPolicy
  enabled: true
  name: "cfg_loader"
  level: "INFO"
```

---

## 타입별 정책 설명

### 1️⃣ BaseModel 소스 정책

**용도**: Pydantic BaseModel 인스턴스를 dict로 변환하여 사용

```yaml
base_model_normalizer:
  normalize_keys: true    # ✅ 키 정규화 (일관성)
  drop_blanks: false      # ❌ 빈 값 유지 (기본값 중요)
  resolve_vars: false     # ❌ 변수 해결 안함 (타입 안전)

base_model_merge:
  deep: false             # Shallow merge (평면 구조)
  overwrite: false        # ❌ 덮어쓰기 방지 (기본값 유지)
```

**특징**:
- BaseModel은 **타입 안전**하고 **기본값이 중요**
- 빈 값(0, "", None)도 의미가 있을 수 있음
- Override보다는 **기본값 제공** 용도

**예시**:
```python
class ImagePolicy(BaseModel):
    max_width: int = 1920   # 기본값
    format: str = "PNG"

policy = SourcePolicy(src=(ImagePolicy(), "image"))
source = UnifiedSource(policy)
kpd = source.extract()
# → {"image": {"max_width": 1920, "format": "PNG"}}
```

---

### 2️⃣ Dict 소스 정책

**용도**: 런타임 dict 데이터를 처리 (주로 Override 용도)

```yaml
dict_normalizer:
  normalize_keys: true    # ✅ 키 정규화
  drop_blanks: true       # ✅ 빈 값 제거 (의미 없는 데이터)
  resolve_vars: false     # ❌ 변수 해결 안함 (단순 데이터)

dict_merge:
  deep: false             # Shallow merge
  overwrite: true         # ✅ 덮어쓰기 (Override 용도)
```

**특징**:
- Dict는 **런타임 데이터** (사용자 입력, API 응답 등)
- 빈 값은 **의미 없는 데이터**로 간주 → 제거
- **Override 용도**로 많이 사용 → 덮어쓰기 허용

**예시**:
```python
# 사용자 입력 override
override_dict = {
    "max_width": 2048,
    "format": "",      # ← drop_blanks=True로 제거됨
}

policy = SourcePolicy(src=(override_dict, "image"))
source = UnifiedSource(policy)
kpd = source.extract()
# → {"image": {"max_width": 2048}}  # format은 제거됨
```

---

### 3️⃣ YAML 소스 정책

**용도**: YAML 설정 파일 파싱 및 처리 (Override 용도)

```yaml
yaml_parser:
  safe_mode: true           # ✅ Safe YAML (보안)
  encoding: "utf-8"
  enable_env: true          # ✅ 환경변수 치환 (${ENV_VAR})
  enable_include: true      # ✅ !include 지시자
  enable_placeholder: true  # ✅ Placeholder (${var})
  enable_reference: true    # ✅ 참조 해결 ($ref:)

yaml_normalizer:
  normalize_keys: true      # ✅ 키 정규화
  drop_blanks: true         # ✅ 빈 값 제거 (Override 용도)
  resolve_vars: true        # ✅ 변수 참조 해결

yaml_merge:
  deep: true                # ✅ Deep merge (계층 구조)
  overwrite: true           # ✅ 덮어쓰기
```

**특징**:
- YAML은 **설정 파일 Override** 용도
- **변수 참조, 환경변수** 많음
- **계층 구조** → Deep merge 필요
- **빈 값은 무의미한 데이터** → 제거

**예시**:
```yaml
# config.yaml - Override 설정
database:
  host: ${DB_HOST}           # 환경변수
  port: 5432
  timeout: ${db.timeout}     # 변수 참조
  password: ""               # ← drop_blanks=true로 제거됨
```

```python
policy = SourcePolicy(src=("config.yaml", "database"))
source = UnifiedSource(policy)
kpd = source.extract()
# → password는 제거됨 (빈 값이므로)
# → 환경변수/변수 참조 모두 해결됨
```

---

## 타입별 정책 비교표

| 속성 | BaseModel | Dict | YAML | 이유 |
|------|-----------|------|------|------|
| **normalize_keys** | ✅ true | ✅ true | ✅ true | 모두 키 정규화 필요 |
| **drop_blanks** | ❌ false | ✅ true | ✅ true | BaseModel만 빈 값 유지 (기본값 중요) |
| **resolve_vars** | ❌ false | ❌ false | ✅ true | YAML만 변수 해결 |
| **merge.deep** | ❌ false | ❌ false | ✅ true | YAML만 계층 구조 |
| **merge.overwrite** | ❌ false | ✅ true | ✅ true | BaseModel만 기본값 유지 |

---

## 사용 예시

### 1. YAML 파일에서 정책 로드

```python
from cfg_utils_v2.core.policy import ConfigLoaderPolicy
from structured_io import YamlParser

# YAML 파일 로드
parser = YamlParser()
policy_dict = parser.parse_file("configs/config_loader.yaml")
policy = ConfigLoaderPolicy(**policy_dict)
```

### 2. ConfigLoader에서 사용

```python
from cfg_utils_v2 import ConfigLoader

loader = ConfigLoader(
    policy=policy,  # YAML에서 로드한 정책
    base_sources=[
        (ImagePolicy(), "image"),  # BaseModel → base_model_* 정책 사용
    ],
    override_sources=[
        ("config.yaml", "image"),  # YAML → yaml_* 정책 사용
        ({"max_width": 2048}, "image")  # Dict → dict_* 정책 사용
    ]
)

# 각 소스별로 적절한 정책이 자동 적용됨
state = loader.get_state()
```

### 3. UnifiedSource 직접 사용

```python
from cfg_utils_v2 import UnifiedSource, SourcePolicy

# BaseModel
policy = SourcePolicy(
    src=(ImagePolicy(), "image"),
    base_model_normalizer=NormalizePolicy(drop_blanks=False)
)
source = UnifiedSource(policy)
kpd = source.extract()

# Dict
policy = SourcePolicy(
    src=({"max_width": 2048}, "image"),
    dict_normalizer=NormalizePolicy(drop_blanks=True)
)
source = UnifiedSource(policy)
kpd = source.extract()

# YAML
policy = SourcePolicy(
    src=("config.yaml", "image"),
    yaml_normalizer=NormalizePolicy(resolve_vars=True)
)
source = UnifiedSource(policy)
kpd = source.extract()
```

---

## 설계 원칙

### 🎯 BaseModel: 타입 안전 + 기본값 제공
- **목적**: 각 모듈의 Policy 클래스에서 타입 안전한 기본값 제공
- **특징**: 빈 값도 의미 있음 (0, "", None), 덮어쓰기 방지
- **사용**: ImagePolicy, OcrPolicy 등 모듈별 기본 설정
- **빈 값 처리**: drop_blanks=false (빈 값도 의미 있는 기본값)

### 🎯 Dict: 런타임 데이터 + Override
- **목적**: 런타임 데이터 처리, Override
- **특징**: 빈 값 제거 (무의미한 데이터), 덮어쓰기 허용
- **사용**: User input, API response, Runtime override
- **빈 값 처리**: drop_blanks=true (빈 값은 무의미)

### 🎯 YAML: 설정 파일 + Override
- **목적**: 설정 파일 Override, 환경별 설정
- **특징**: 변수 참조 해결, Deep merge, 빈 값 제거, 덮어쓰기 허용
- **사용**: Configuration files, Environment-specific settings
- **빈 값 처리**: drop_blanks=true (Override 용도, 빈 값은 무의미)

---

## 주의사항

### ⚠️ Pydantic Union 타입 문제

**문제**: `Union[BaseModel, dict]` 타입을 사용하면 dict가 BaseModel로 변환됨

```python
# ❌ 문제 발생
src: Union[BaseModel, dict]  # dict 입력 시 BaseModel로 변환 → 데이터 소실

# ✅ 해결
src: Any  # 타입 그대로 유지
```

**이유**: Pydantic v2는 Union에 BaseModel이 있으면 자동 변환 시도

### ⚠️ drop_blanks 설정 주의

- **BaseModel**: `false` - 빈 값(0, "", None)도 의미 있는 기본값
  - 예: ImagePolicy(max_width=0) → 0은 "제한 없음"을 의미할 수 있음
  - 각 모듈의 Policy 클래스에서 기본값 관리
  
- **Dict**: `true` - 빈 값은 무의미한 데이터로 간주
  - 예: {"name": "", "age": 0} → name은 제거, age는 유지 (0도 유효값)
  - Override 용도로 사용, 빈 값은 "설정 안함"을 의미
  
- **YAML**: `true` - Override 용도, 빈 값은 무의미
  - 예: config.yaml에 password: "" → 제거됨 (빈 패스워드는 무의미)
  - 설정 파일 Override에서 빈 값은 "덮어쓰지 않음"을 의미

### ⚠️ resolve_vars 설정 주의

- **BaseModel**: `false` - 타입 안전성 유지
- **Dict**: `false` - 단순 데이터
- **YAML**: `true` - 변수 참조가 많음

---

## 더 알아보기

- [cfg_utils_v2 README](../README.md)
- [SourcePolicy API](../core/policy.py)
- [UnifiedSource API](../service/source.py)
- [ConfigLoader API](../service/loader.py)
