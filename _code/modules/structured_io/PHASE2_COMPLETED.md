# Phase 2 완료 보고서

**작성일**: 2025-10-19  
**작업자**: GitHub Copilot  
**작업**: cfg_utils import 경로 수정 및 SourcePathPolicy 이동

---

## ✅ 완료된 작업

### 1. cfg_utils import 경로 수정 (4곳) ✅

#### 1.1 `cfg_utils/core/policy.py`
```python
# ❌ Before
from structured_io.core.base_policy import BaseParserPolicy

# ✅ After
from structured_io.core.policy import BaseParserPolicy
```

#### 1.2 `cfg_utils/services/config_loader.py` (상단 import)
```python
# ❌ Before
from modules.structured_io.core.base_policy import BaseParserPolicy, SourcePathPolicy

# ✅ After
from modules.structured_io.core.policy import BaseParserPolicy
from ..core.policy import ConfigPolicy, SourcePathPolicy
```

#### 1.3 `cfg_utils/services/config_loader.py` (내부 import 2곳)
- Line 424: 제거됨 (상단 import로 통합)
- Line 478: 제거됨 (상단 import로 통합)
- Line 519: 제거됨 (상단 import로 통합)

---

### 2. SourcePathPolicy 이동 ✅

#### 2.1 `cfg_utils/core/policy.py`에 SourcePathPolicy 추가
```python
class SourcePathPolicy(BaseModel):
    """ConfigLoader용 소스 파일 설정.
    
    ConfigLoader가 여러 YAML 파일을 로드할 때 사용하는 정책입니다.
    structured_io의 Parser와는 무관하며, cfg_utils 전용입니다.
    
    Attributes:
        path: 파일 경로
        section: 추출할 섹션 (None이면 전체 사용)
    """
    path: Union[str, Path] = Field(..., description="파일 경로")
    section: Optional[str] = Field(None, description="추출할 섹션 (None이면 전체 사용)")
    
    class Config:
        extra = "ignore"
```

#### 2.2 `ConfigPolicy`에 `source_paths` 필드 추가
```python
class ConfigPolicy(BaseModel):
    config_loader_path: Optional[Union[str, Path]] = ...
    source_paths: Optional[Union[
        SourcePathPolicy,
        List[SourcePathPolicy]
    ]] = Field(
        default=None,
        description=(
            "ConfigLoader용 소스 파일 경로. 단일 SourcePathPolicy 또는 리스트. "
            "이 필드는 BaseParserPolicy가 아닌 ConfigPolicy에 속합니다."
        )
    )
    yaml: Optional[BaseParserPolicy] = ...
```

#### 2.3 `structured_io/core/policy.py`에서 제거
```python
# ❌ Before
class SourcePathPolicy(BaseModel):
    path: Union[str, Path] = ...
    section: Optional[str] = ...

class BaseParserPolicy(BaseModel):
    source_paths: Optional[Union[...]] = ...  # ❌ 제거됨
    enable_env: bool = ...
    # ...
```

```python
# ✅ After
class BaseParserPolicy(BaseModel):
    """Parser 정책 (YAML, JSON 공통)
    
    Note:
        - source_paths 필드는 제거됨 (cfg_utils.SourcePathPolicy로 이동)
        - Parser는 파싱만 담당, 소스 관리는 ConfigLoader의 책임
    """
    # source_paths 필드 제거됨
    enable_env: bool = ...
    enable_include: bool = ...
    enable_placeholder: bool = ...
    enable_reference: bool = Field(default=False, ...)  # 기본값 False로 변경
    # ...
```

#### 2.4 `structured_io/core/__init__.py`에서 export 제거
```python
# ❌ Before
__all__ = [
    "BaseParser",
    "BaseDumper",
    "SourcePathPolicy",  # ❌ 제거됨
    "BaseParserPolicy",
    "BaseDumperPolicy",
]

# ✅ After
__all__ = [
    "BaseParser",
    "BaseDumper",
    "BaseParserPolicy",
    "BaseDumperPolicy",
]
```

---

### 3. config_loader.py 코드 업데이트 ✅

#### 3.1 `policy.yaml.source_paths` → `policy.source_paths`

**Before**:
```python
if temp_policy.yaml and temp_policy.yaml.source_paths:
    yaml_policy_copy = temp_policy.yaml.model_copy(update={"source_paths": []})
    temp_policy = temp_policy.model_copy(update={"yaml": yaml_policy_copy})
```

**After**:
```python
if temp_policy.source_paths:
    temp_policy = temp_policy.model_copy(update={"source_paths": []})
```

#### 3.2 `_load_with_section_from_policy` 함수

**Before**:
```python
if not policy.yaml or not policy.yaml.source_paths:
    raise TypeError("No source_paths configured in policy.yaml")

source_paths = cls._apply_default_section_to_paths(
    policy.yaml.source_paths,
    default_section
)

yaml_policy = policy.yaml.model_copy(update={"source_paths": source_paths})
new_policy = policy.model_copy(update={"yaml": yaml_policy})
```

**After**:
```python
if not policy.source_paths:
    raise TypeError("No source_paths configured in policy")

source_paths = cls._apply_default_section_to_paths(
    policy.source_paths,
    default_section
)

new_policy = policy.model_copy(update={"source_paths": source_paths})
```

#### 3.3 `_clear_source_paths` 함수

**Before**:
```python
if policy.yaml and policy.yaml.source_paths:
    yaml_policy_copy = policy.yaml.model_copy(update={"source_paths": []})
    return policy.model_copy(update={"yaml": yaml_policy_copy})
return policy
```

**After**:
```python
if policy.source_paths:
    return policy.model_copy(update={"source_paths": []})
return policy
```

#### 3.4 `_load_and_merge` 함수

**Before**:
```python
if self.policy.yaml and hasattr(self.policy.yaml, 'source_paths') and self.policy.yaml.source_paths:
    for src_cfg in self._normalize_source_paths(self.policy.yaml.source_paths):
```

**After**:
```python
if self.policy.source_paths:
    for src_cfg in self._normalize_source_paths(self.policy.source_paths):
```

#### 3.5 `_normalize_source_paths` 함수

**Before**:
```python
def _normalize_source_paths(...) -> List[SourcePathPolicy]:
    """source_paths를 SourcePathConfig 리스트로 정규화."""
    if type(source_paths).__name__ == 'SourcePathConfig':
        return [source_paths]
    # ...
    if type(item).__name__ == 'SourcePathConfig':
        normalized.append(item)
```

**After**:
```python
def _normalize_source_paths(...) -> List[SourcePathPolicy]:
    """source_paths를 SourcePathPolicy 리스트로 정규화."""
    if isinstance(source_paths, SourcePathPolicy):
        return [source_paths]
    # ...
    if isinstance(item, SourcePathPolicy):
        normalized.append(item)
```

---

### 4. structured_io/core/interface.py Alias 추가 ✅

```python
# Backward compatibility aliases
Parser = BaseParser
Dumper = BaseDumper
```

---

## 📊 변경 파일 목록

### ✅ structured_io 모듈
1. `core/interface.py` - Parser/Dumper alias 추가
2. `core/policy.py` - SourcePathPolicy 제거, source_paths 필드 제거
3. `core/__init__.py` - SourcePathPolicy export 제거

### ✅ cfg_utils 모듈
4. `core/policy.py` - SourcePathPolicy 정의, ConfigPolicy.source_paths 필드 추가, import 경로 수정
5. `services/config_loader.py` - import 경로 수정 (4곳), policy.yaml.source_paths → policy.source_paths 변경 (6곳)

---

## 🎯 개선 효과

### Before (문제)
1. **책임 혼란**: `SourcePathPolicy`가 `structured_io`에 있지만 사용하지 않음
2. **잘못된 위치**: `BaseParserPolicy.source_paths` 필드 (Parser와 무관)
3. **잘못된 경로**: `structured_io.core.base_policy` (존재하지 않는 경로)
4. **복잡한 접근**: `policy.yaml.source_paths` (2단계 접근)

### After (개선)
1. **책임 명확화**: `SourcePathPolicy`는 `cfg_utils`에만 존재 ✅
2. **올바른 위치**: `ConfigPolicy.source_paths` (ConfigLoader 전용) ✅
3. **올바른 경로**: `structured_io.core.policy` ✅
4. **간결한 접근**: `policy.source_paths` (1단계 접근) ✅

---

## ✅ 에러 체크 결과

### structured_io
- `core/interface.py`: ✅ No errors
- `core/policy.py`: ✅ No errors
- `core/__init__.py`: ✅ No errors

### cfg_utils
- `core/policy.py`: ⚠️ 1 warning (기존 KeyPathNormalizePolicy import 문제 - 무관)
- `services/config_loader.py`: ✅ No errors

---

## 📝 문서화

### BaseParserPolicy 주석 개선
```python
class BaseParserPolicy(BaseModel):
    """Parser 정책 (YAML, JSON 공통)
    
    Parser의 동작을 제어하는 정책입니다.
    
    Note:
        - source_paths 필드는 제거됨 (cfg_utils.SourcePathPolicy로 이동)
        - Parser는 파싱만 담당, 소스 관리는 ConfigLoader의 책임
    """
```

### SourcePathPolicy 주석 개선
```python
class SourcePathPolicy(BaseModel):
    """ConfigLoader용 소스 파일 설정.
    
    ConfigLoader가 여러 YAML 파일을 로드할 때 사용하는 정책입니다.
    structured_io의 Parser와는 무관하며, cfg_utils 전용입니다.
    
    Examples:
        >>> # 단일 파일 로드
        >>> source = SourcePathPolicy(path="config.yaml", section="database")
        
        >>> # 여러 파일 로드
        >>> sources = [
        ...     SourcePathPolicy(path="base.yaml", section=None),
        ...     SourcePathPolicy(path="override.yaml", section="production")
        ... ]
    """
```

---

## 🚀 다음 단계 (Phase 3)

### 권장 작업
1. **테스트 추가**:
   - `test_yaml_parser.py`: VarsResolver public API 테스트
   - `test_json_parser.py`: VarsResolver public API 테스트
   - `test_config_loader.py`: SourcePathPolicy 통합 테스트

2. **README 업데이트**:
   - `structured_io/README.md`: SourcePathPolicy 제거 안내
   - `cfg_utils/README.md`: SourcePathPolicy 사용법 추가

3. **Migration Guide**:
   - 기존 코드에서 `structured_io.core.policy.SourcePathPolicy` 사용하던 경우
   - → `cfg_utils.core.policy.SourcePathPolicy`로 변경 필요

---

## 🎉 최종 정리

### Phase 1 (완료)
- ✅ Base 접두사 통일 (BaseParser, BaseDumper)
- ✅ Import 경로 수정 (yaml_io.py, json_io.py)
- ✅ VarsResolver private 메서드 호출 제거

### Phase 2 (완료)
- ✅ cfg_utils import 경로 수정 (4곳)
- ✅ SourcePathPolicy 이동 (structured_io → cfg_utils)
- ✅ BaseParserPolicy.source_paths 필드 제거
- ✅ ConfigPolicy.source_paths 필드 추가
- ✅ config_loader.py 코드 업데이트 (6곳)

### 전체 성과
- **코드 품질**: 책임 분리 명확화, 캡슐화 개선
- **유지보수성**: Import 경로 정확화, 네이밍 일관성
- **안정성**: Private API 사용 제거, 타입 안정성 향상

**작업 완료!** 🎊
