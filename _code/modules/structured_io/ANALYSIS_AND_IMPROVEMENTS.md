# structured_io 모듈 분석 및 개선안

**작성일**: 2025-10-19  
**작성자**: GitHub Copilot  
**목적**: structured_io 모듈의 현재 상태 분석 및 개선 방향 제시

---

## 📋 목차

1. [모듈 개요](#1-모듈-개요)
2. [현재 구조 분석](#2-현재-구조-분석)
3. [발견된 문제점](#3-발견된-문제점)
4. [개선안](#4-개선안)
5. [우선순위 및 로드맵](#5-우선순위-및-로드맵)

---

## 1. 모듈 개요

### 1.1 목적
- 구조화된 데이터(YAML, JSON)의 읽기/쓰기 통합 인터페이스 제공
- 환경 변수, placeholder, include 등 고급 기능 지원
- 포맷 독립적인 추상화 계층 제공

### 1.2 현재 구조
```
structured_io/
├── __init__.py              # Factory 함수 제공
├── core/
│   ├── interface.py         # Parser, Dumper 추상 클래스
│   └── policy.py            # 정책 모델 (BaseParserPolicy, BaseDumperPolicy)
├── formats/
│   ├── yaml_io.py           # YamlParser, YamlDumper
│   └── json_io.py           # JsonParser, JsonDumper
└── fileio/
    └── structured_fileio.py # StructuredFileIO (파일 I/O 어댑터)
```

### 1.3 주요 기능
- **YAML 파싱**: `!include`, 환경 변수(`${VAR}`), placeholder(`{{ var }}`)
- **JSON 파싱**: 환경 변수, placeholder (include 제외)
- **Dumping**: 포맷별 직렬화 (들여쓰기, 정렬 등)
- **정책 기반**: `BaseParserPolicy`, `BaseDumperPolicy`로 동작 제어

---

## 2. 현재 구조 분석

### 2.1 강점 ✅

#### ✅ 명확한 책임 분리
- **Interface** (`Parser`, `Dumper`): 추상화 계층 제공
- **Policy**: 동작 정책 분리 (Pydantic 기반)
- **Format**: 포맷별 구현체 (`YamlParser`, `JsonParser`)
- **FileIO**: 파일 I/O 어댑터

#### ✅ 확장 가능한 설계
- 새로운 포맷(TOML, XML 등) 추가 용이
- Factory 함수로 간편한 생성 (`yaml_parser()`, `json_fileio()`)

#### ✅ 고급 기능 지원
- `!include`: YAML 파일 재사용
- 환경 변수 치환: `${VAR}`, `${VAR:default}`
- Placeholder: `{{ var }}`
- VarsResolver 통합

---

### 2.2 약점 및 문제점 ⚠️

#### ⚠️ 1. **Import 경로 불일치**
**문제**:
```python
# yaml_io.py
from structured_io.fileio import BaseParserPolicy  # ❌ 잘못된 경로
from structured_io.core.interface import BaseDumper

# 올바른 경로
from structured_io.core.policy import BaseParserPolicy  # ✅
from structured_io.core.interface import Dumper  # ✅
```

**영향**: 모듈 import 실패, 순환 참조 가능성

---

#### ⚠️ 2. **네이밍 불일치 (Parser vs BaseParser)**
**문제**:
```python
# interface.py
class Parser(ABC):  # 정의
class Dumper(ABC):

# __init__.py
from structured_io.core.interface import BaseParser, BaseDumper  # ❌ 존재하지 않음

# yaml_io.py
class YamlParser(BaseParser):  # ❌ BaseParser는 interface.py에 없음
```

**원인**: `Parser` → `BaseParser` 리네이밍 과정에서 일부 코드만 업데이트

**영향**: NameError, 타입 체크 실패

---

#### ⚠️ 3. **policy.py의 불필요한 필드**
**문제**:
```python
class BaseParserPolicy(BaseModel):
    source_paths: Optional[Union[SourcePathPolicy, List[SourcePathPolicy]]] = None
    # ❌ Parser가 아닌 ConfigLoader의 책임
```

**이유**: `source_paths`는 ConfigLoader가 관리해야 할 필드  
**영향**: 책임 경계 모호, 사용처 없음

---

#### ⚠️ 4. **Reference 치환 책임 불명확**
**문제**:
```python
# policy.py
enable_reference: bool = Field(default=True, description="${ref:path.to.key} 참조 치환")

# yaml_io.py 주석
# Note: Reference 치환(${key.path})은 ConfigNormalizer에서 처리됨

# json_io.py 주석
# Reference 치환은 제거 (ConfigNormalizer에서 처리)
```

**문제**: 
- Policy에는 `enable_reference` 필드 존재
- Parser는 Reference 치환 미구현
- 실제 처리는 `ConfigNormalizer`에게 위임

**영향**: 
- 사용자 혼란 (enable_reference 설정해도 동작 안 함)
- 책임 경계 모호

---

#### ⚠️ 5. **VarsResolver 의존성 하드코딩**
**문제**:
```python
# yaml_io.py
from unify_utils.resolver.vars import VarsResolver
from unify_utils.core.policy import VarsResolverPolicy

resolver = VarsResolver(data={}, policy=vars_policy)
text = resolver._apply_single(text)  # ❌ private 메서드 호출
```

**문제점**:
- `unify_utils` 의존성 강제
- `_apply_single` private 메서드 직접 호출 (캡슐화 위반)
- 테스트 시 모킹 어려움

---

#### ⚠️ 6. **에러 처리 불완전**
**문제**:
```python
# yaml_io.py
except Exception as e:
    if self.policy.on_error == "raise":
        raise RuntimeError(f"YAML 파싱 실패: {e}")  # ✅
    elif self.policy.on_error == "warn":
        print(f"[경고] YAML 파싱 실패: {e}")  # ❌ print 사용
    return {}
```

**문제점**:
- `on_error="warn"`: `print` 대신 logging 사용 필요
- `on_error="ignore"`: 무시하고 빈 dict 반환 (로그 없음)
- 에러 컨텍스트 정보 부족 (파일 경로, 라인 번호 등)

---

#### ⚠️ 7. **Factory 함수 파라미터 불필요**
**문제**:
```python
def yaml_parser(
    *,
    enable_env: bool = True,
    # ... (Parser 관련 파라미터)
    sort_keys: bool = False,  # ❌ Dumper 파라미터
    default_flow_style: bool = False,  # ❌ Dumper 파라미터
    indent: int = 2,  # ❌ Dumper 파라미터
):
    policy = BaseParserPolicy(
        # ...
        sort_keys=sort_keys,  # ❌ 사용되지 않음
        default_flow_style=default_flow_style,
        indent=indent,
    )
```

**이유**: 하위 호환성 유지용이나 혼란 유발

---

#### ⚠️ 8. **StructuredFileIO의 FSOOps 의존성**
**문제**:
```python
# structured_fileio.py
from modules.fso_utils import FSOOps, FSOOpsPolicy

class StructuredFileIO:
    def __init__(self, path: str | Path, parser, dumper, fso_policy: FSOOpsPolicy | None = None):
        self.path = FSOOps(path, fso_policy or FSOOpsPolicy(as_type="file"))
```

**문제점**:
- `fso_utils` 모듈 의존성 (불필요할 수 있음)
- `FSOOps`는 파일 존재 검증/생성 기능 제공하나, 단순 I/O에는 `Path`로 충분
- 복잡도 증가

---

#### ⚠️ 9. **테스트 부재**
**문제**: `tests/` 디렉토리 없음, 단위 테스트 없음

**영향**: 
- 리팩토링 시 회귀 테스트 불가
- 버그 발견 어려움
- 사용 예시 부족

---

#### ⚠️ 10. **문서화 부족**
**문제**: `README.md` 없음

**필요 내용**:
- 사용 가이드
- API 레퍼런스
- 사용 예시
- 고급 기능 설명 (include, placeholder 등)

---

## 3. 발견된 문제점 요약

### 3.1 심각도별 분류

| 심각도 | 문제 | 영향 |
|--------|------|------|
| 🔴 **Critical** | Import 경로 불일치 | 모듈 실행 실패 |
| 🔴 **Critical** | 네이밍 불일치 (`Parser` vs `BaseParser`) | NameError |
| 🟠 **High** | VarsResolver private 메서드 호출 | 캡슐화 위반, 불안정 |
| 🟠 **High** | 테스트 부재 | 품질 보증 불가 |
| 🟡 **Medium** | Reference 치환 책임 불명확 | 사용자 혼란 |
| 🟡 **Medium** | 에러 처리 불완전 | 디버깅 어려움 |
| 🟡 **Medium** | 문서화 부족 | 사용성 저하 |
| 🟢 **Low** | Factory 함수 파라미터 불필요 | 코드 가독성 저하 |
| 🟢 **Low** | `source_paths` 불필요 필드 | 책임 경계 모호 |
| 🟢 **Low** | FSOOps 의존성 | 복잡도 증가 |

---

## 4. 개선안

### 4.1 🔴 Critical 우선순위

#### 개선 1: Import 경로 수정

**파일**: `formats/yaml_io.py`

```python
# ❌ Before
from structured_io.fileio import BaseParserPolicy
from structured_io.core.interface import BaseDumper

# ✅ After
from structured_io.core.policy import BaseParserPolicy
from structured_io.core.interface import Dumper
```

**파일**: `formats/json_io.py`

```python
# ❌ Before
from structured_io.core.interface import BaseParser
from structured_io.core.interface import BaseDumper

# ✅ After
from structured_io.core.interface import Parser, Dumper
```

---

#### 개선 2: 네이밍 일관성 확보

**옵션 A: `Parser`, `Dumper` 사용 (권장)**

```python
# core/interface.py (변경 없음)
class Parser(ABC): ...
class Dumper(ABC): ...

# core/__init__.py
from .interface import Parser, Dumper

__all__ = ["Parser", "Dumper", ...]

# formats/yaml_io.py
from structured_io.core.interface import Parser, Dumper

class YamlParser(Parser): ...
class YamlDumper(Dumper): ...
```

**옵션 B: `BaseParser`, `BaseDumper` 사용**

```python
# core/interface.py
class BaseParser(ABC): ...  # Parser → BaseParser 리네임
class BaseDumper(ABC): ...  # Dumper → BaseDumper 리네임

# 하위 호환성 유지
Parser = BaseParser
Dumper = BaseDumper
```

**권장**: **옵션 A** (더 간결하고 Python 관례에 맞음)

---

### 4.2 🟠 High 우선순위

#### 개선 3: VarsResolver 의존성 추상화

**목적**: 
- `unify_utils` 의존성 제거 또는 추상화
- 테스트 가능한 구조

**방법 A: VarsResolver 인터페이스 추가**

```python
# core/resolver.py (신규)
from abc import ABC, abstractmethod

class VarsResolverInterface(ABC):
    """변수 치환 인터페이스"""
    
    @abstractmethod
    def resolve(self, text: str, context: dict) -> str:
        """텍스트 내 변수를 치환"""
        pass

# unify_utils 어댑터
class UnifyVarsResolver(VarsResolverInterface):
    def resolve(self, text: str, context: dict) -> str:
        from unify_utils.resolver.vars import VarsResolver
        from unify_utils.core.policy import VarsResolverPolicy
        
        policy = VarsResolverPolicy(
            enable_env=True,
            enable_context=True,
            context=context,
            recursive=True,
            strict=False
        )
        resolver = VarsResolver(data={}, policy=policy)
        return resolver.apply_to_string(text)  # ✅ public 메서드 사용
```

**방법 B: 내장 Resolver 구현 (독립성 확보)**

```python
# core/resolver.py (신규)
import os
import re
from typing import Dict, Any

class SimpleVarsResolver:
    """간단한 변수 치환기 (환경 변수, placeholder)"""
    
    ENV_PATTERN = re.compile(r'\$\{([A-Za-z_][A-Za-z0-9_]*?)(?::([^}]*))?\}')
    PLACEHOLDER_PATTERN = re.compile(r'\{\{\s*([A-Za-z_][A-Za-z0-9_]*?)\s*\}\}')
    
    def __init__(self, context: Dict[str, Any] = None, enable_env: bool = True):
        self.context = context or {}
        self.enable_env = enable_env
    
    def resolve(self, text: str) -> str:
        """변수 치환"""
        if self.enable_env:
            text = self._resolve_env(text)
        text = self._resolve_placeholder(text)
        return text
    
    def _resolve_env(self, text: str) -> str:
        """환경 변수 치환: ${VAR} 또는 ${VAR:default}"""
        def replacer(match):
            var_name = match.group(1)
            default = match.group(2) if match.group(2) is not None else ""
            return os.environ.get(var_name, default)
        return self.ENV_PATTERN.sub(replacer, text)
    
    def _resolve_placeholder(self, text: str) -> str:
        """Placeholder 치환: {{ var }}"""
        def replacer(match):
            var_name = match.group(1)
            return str(self.context.get(var_name, match.group(0)))
        return self.PLACEHOLDER_PATTERN.sub(replacer, text)
```

**yaml_io.py 수정**:

```python
# ✅ After
from structured_io.core.resolver import SimpleVarsResolver

class YamlParser(Parser):
    def parse(self, text: str, base_path: Path | None = None) -> dict:
        # 1) Placeholder/Env 치환
        if self.policy.enable_placeholder or self.policy.enable_env:
            resolver = SimpleVarsResolver(
                context=self.context,
                enable_env=self.policy.enable_env
            )
            text = resolver.resolve(text)
        
        # 2) YAML load
        # ...
```

**권장**: **방법 B** (독립성 확보, 의존성 최소화)

---

#### 개선 4: 테스트 추가

**구조**:
```
structured_io/
├── tests/
│   ├── __init__.py
│   ├── conftest.py           # pytest fixtures
│   ├── test_yaml_parser.py
│   ├── test_json_parser.py
│   ├── test_fileio.py
│   └── fixtures/
│       ├── test.yaml
│       └── test.json
```

**예시**: `tests/test_yaml_parser.py`

```python
# tests/test_yaml_parser.py
import pytest
from pathlib import Path
from structured_io import yaml_parser
from structured_io.core.policy import BaseParserPolicy

@pytest.fixture
def sample_yaml():
    return """
    name: Test
    value: ${TEST_VAR:default}
    nested:
      key: {{ user_key }}
    """

@pytest.fixture
def context():
    return {"user_key": "user_value"}

def test_yaml_parser_basic(sample_yaml, context):
    parser = yaml_parser(enable_env=True, enable_placeholder=True)
    data = parser.parse(sample_yaml)
    
    assert data["name"] == "Test"
    assert data["value"] == "default"  # 환경 변수 없으면 기본값
    assert data["nested"]["key"] == "{{ user_key }}"  # context 미전달 시 유지

def test_yaml_parser_with_context(sample_yaml, context):
    policy = BaseParserPolicy(
        enable_env=True,
        enable_placeholder=True
    )
    parser = yaml_parser()
    parser.context = context
    data = parser.parse(sample_yaml)
    
    assert data["nested"]["key"] == "user_value"

def test_yaml_parser_include(tmp_path):
    # !include 테스트
    base_yaml = tmp_path / "base.yaml"
    included_yaml = tmp_path / "included.yaml"
    
    included_yaml.write_text("included_key: included_value")
    base_yaml.write_text("main: !include included.yaml")
    
    parser = yaml_parser(enable_include=True)
    data = parser.parse(base_yaml.read_text(), base_path=base_yaml.parent)
    
    assert data["main"]["included_key"] == "included_value"

def test_yaml_parser_error_handling():
    parser = yaml_parser(on_error="ignore")
    data = parser.parse("invalid: yaml: content: ::::")
    
    assert data == {}  # 에러 무시 시 빈 dict 반환
```

---

### 4.3 🟡 Medium 우선순위

#### 개선 5: Reference 치환 정책 명확화

**옵션 A: Parser에서 구현 (권장)**

```python
# policy.py
class BaseParserPolicy(BaseModel):
    enable_reference: bool = Field(
        default=False,  # 기본값 False (기존 ConfigNormalizer에서만 처리)
        description="${ref:path.to.key} 참조 치환 (structured_io 내부 처리)"
    )
```

**구현**:

```python
# yaml_io.py
class YamlParser(Parser):
    def parse(self, text: str, base_path: Path | None = None) -> dict:
        # 1) Placeholder/Env 치환
        # ...
        
        # 2) YAML load
        data = yaml.load(stream, Loader=loader_cls) or {}
        
        # 3) Reference 치환 (enable_reference=True인 경우)
        if self.policy.enable_reference:
            data = self._resolve_references(data)
        
        return data
    
    def _resolve_references(self, data: dict) -> dict:
        """${ref:path.to.key} 참조 치환"""
        from keypath_utils import KeyPathDict
        
        kpd = KeyPathDict(data)
        # ${ref:...} 패턴 찾아서 치환
        # (구현 생략, keypath_utils 활용)
        return kpd.data
```

**옵션 B: 명시적 비활성화 (현재 방식 유지)**

```python
# policy.py
class BaseParserPolicy(BaseModel):
    enable_reference: bool = Field(
        default=False,  # ❌ 비활성화
        deprecated=True,
        description="[DEPRECATED] Reference 치환은 ConfigNormalizer에서 처리됨"
    )
```

**권장**: **옵션 A** (구현하면 더 완전한 Parser)

---

#### 개선 6: 에러 처리 개선

```python
# yaml_io.py
import logging

logger = logging.getLogger(__name__)

class YamlParser(Parser):
    def parse(self, text: str, base_path: Path | None = None) -> dict:
        try:
            # 파싱 로직
            ...
        except yaml.YAMLError as e:
            error_msg = f"YAML 파싱 실패: {e}"
            if base_path:
                error_msg += f" (파일: {base_path})"
            
            if self.policy.on_error == "raise":
                raise RuntimeError(error_msg) from e
            elif self.policy.on_error == "warn":
                logger.warning(error_msg)  # ✅ logging 사용
            # else: "ignore" → 로그 없음
            
            return {}
```

**추가**: 에러 정보 구조화

```python
# core/exceptions.py (신규)
class StructuredIOError(Exception):
    """Base exception"""
    pass

class ParserError(StructuredIOError):
    """Parsing error"""
    def __init__(self, message: str, file_path: Path = None, line: int = None):
        self.file_path = file_path
        self.line = line
        super().__init__(message)
```

---

#### 개선 7: README.md 추가

**파일**: `structured_io/README.md`

```markdown
# structured_io

구조화된 데이터(YAML, JSON)의 읽기/쓰기 통합 인터페이스

## 설치

```bash
# PYTHONPATH 설정
export PYTHONPATH="${PYTHONPATH}:M:/CALife/CAShop - 구매대행/_code/modules"
```

## 빠른 시작

### YAML 파싱

```python
from structured_io import yaml_parser

parser = yaml_parser(enable_env=True, enable_include=True)
data = parser.parse("""
name: ${PROJECT_NAME:MyProject}
config: !include config.yaml
""")
```

### JSON 파싱

```python
from structured_io import json_parser

parser = json_parser(enable_env=True)
data = parser.parse('{"name": "${USER:guest}"}')
```

### 파일 I/O

```python
from structured_io import yaml_fileio

fileio = yaml_fileio("config.yaml")
data = fileio.read()

data["new_key"] = "value"
fileio.write(data)
```

## 고급 기능

### 1. 환경 변수 치환

```yaml
# config.yaml
database:
  host: ${DB_HOST:localhost}
  port: ${DB_PORT:5432}
```

### 2. Include 지원 (YAML만)

```yaml
# main.yaml
base: !include base.yaml
overrides:
  key: value
```

### 3. Placeholder

```python
parser = yaml_parser()
parser.context = {"version": "1.0.0"}
data = parser.parse("app_version: {{ version }}")
# {"app_version": "1.0.0"}
```

## API 레퍼런스

[자세한 API 문서는 여기 참조]
```

---

### 4.4 🟢 Low 우선순위

#### 개선 8: Policy 정리

```python
# core/policy.py
class BaseParserPolicy(BaseModel):
    # ❌ 제거
    # source_paths: Optional[Union[SourcePathPolicy, List[SourcePathPolicy]]] = None
    
    enable_env: bool = Field(default=True, ...)
    enable_include: bool = Field(default=True, ...)
    enable_placeholder: bool = Field(default=True, ...)
    enable_reference: bool = Field(default=False, ...)  # 명확한 기본값
    encoding: str = Field(default="utf-8", ...)
    on_error: str = Field(default="raise", ...)
    safe_mode: bool = Field(default=True, ...)
```

---

#### 개선 9: Factory 함수 정리

```python
# __init__.py
def yaml_parser(
    *,
    enable_env: bool = True,
    enable_include: bool = True,
    enable_placeholder: bool = True,
    enable_reference: bool = False,
    safe_mode: bool = True,
    encoding: str = "utf-8",
    on_error: str = "raise",
    # ❌ 제거: Dumper 관련 파라미터
):
    policy = BaseParserPolicy(
        enable_env=enable_env,
        enable_include=enable_include,
        enable_placeholder=enable_placeholder,
        enable_reference=enable_reference,
        safe_mode=safe_mode,
        encoding=encoding,
        on_error=on_error,
    )
    return YamlParser(policy)
```

---

#### 개선 10: StructuredFileIO 단순화 (선택)

**현재**:
```python
from modules.fso_utils import FSOOps, FSOOpsPolicy

class StructuredFileIO:
    def __init__(self, path: str | Path, parser, dumper, fso_policy: FSOOpsPolicy | None = None):
        self.path = FSOOps(path, fso_policy or FSOOpsPolicy(as_type="file"))
```

**개선안** (단순화):
```python
class StructuredFileIO:
    def __init__(self, path: str | Path, parser, dumper):
        self.path = Path(path)
        self.parser = parser
        self.dumper = dumper
    
    def read(self) -> Any:
        if not self.path.exists():
            raise FileNotFoundError(f"File not found: {self.path}")
        
        text = self.path.read_text(encoding=self.parser.policy.encoding)
        return self.parser.parse(text, base_path=self.path.parent)
    
    def write(self, data: Any) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)  # 디렉토리 자동 생성
        text = self.dumper.dump(data)
        self.path.write_text(text, encoding=self.dumper.policy.encoding)
        return self.path
```

**장점**: 
- `fso_utils` 의존성 제거
- 더 간단한 구조
- 테스트 용이

**단점**: 
- FSOOps의 고급 기능(검증, 권한 등) 상실
- 기존 코드 영향 (cfg_utils_v2 등에서 사용 중)

**권장**: **현재 구조 유지** (FSOOps 고급 기능 활용 중인 경우)

---

## 5. 우선순위 및 로드맵

### 5.1 Phase 1: Critical 문제 해결 (1일)

| 작업 | 파일 | 예상 시간 |
|------|------|----------|
| Import 경로 수정 | `yaml_io.py`, `json_io.py` | 30분 |
| 네이밍 일관성 (옵션 A 권장) | `interface.py`, `__init__.py`, `yaml_io.py`, `json_io.py` | 1시간 |
| 동작 확인 테스트 | 모든 파일 | 30분 |

**결과**: 모듈 정상 동작 보장

---

### 5.2 Phase 2: High 우선순위 (2-3일)

| 작업 | 파일 | 예상 시간 |
|------|------|----------|
| VarsResolver 추상화 (방법 B 권장) | `core/resolver.py` (신규), `yaml_io.py`, `json_io.py` | 3시간 |
| 테스트 프레임워크 구축 | `tests/` (신규) | 2시간 |
| 핵심 테스트 작성 | `test_yaml_parser.py`, `test_json_parser.py` | 4시간 |
| CI/CD 통합 | `.github/workflows/test.yml` | 1시간 |

**결과**: 안정성 확보, 회귀 방지

---

### 5.3 Phase 3: Medium 우선순위 (2일)

| 작업 | 파일 | 예상 시간 |
|------|------|----------|
| Reference 치환 구현 (옵션 A) | `yaml_io.py`, `json_io.py` | 2시간 |
| 에러 처리 개선 | `core/exceptions.py` (신규), `yaml_io.py`, `json_io.py` | 2시간 |
| README.md 작성 | `README.md` (신규) | 3시간 |
| 사용 예시 추가 | `examples/` (신규) | 2시간 |

**결과**: 완전성 확보, 사용성 개선

---

### 5.4 Phase 4: Low 우선순위 (1일)

| 작업 | 파일 | 예상 시간 |
|------|------|----------|
| Policy 정리 | `policy.py` | 30분 |
| Factory 함수 정리 | `__init__.py` | 30분 |
| StructuredFileIO 단순화 검토 | `structured_fileio.py` | 1시간 |
| 코드 스타일 통일 | 전체 | 1시간 |

**결과**: 코드 품질 향상

---

## 6. 구현 체크리스트

### Phase 1: Critical ✅
- [ ] `yaml_io.py`: Import 경로 수정
- [ ] `json_io.py`: Import 경로 수정
- [ ] `interface.py`: 네이밍 확정 (`Parser`, `Dumper`)
- [ ] `__init__.py`: Export 수정
- [ ] 전체 Import 테스트

### Phase 2: High ✅
- [ ] `core/resolver.py`: SimpleVarsResolver 구현
- [ ] `yaml_io.py`: VarsResolver 교체
- [ ] `json_io.py`: VarsResolver 교체
- [ ] `tests/conftest.py`: pytest fixtures
- [ ] `tests/test_yaml_parser.py`: 기본 테스트
- [ ] `tests/test_json_parser.py`: 기본 테스트
- [ ] `tests/test_fileio.py`: 파일 I/O 테스트

### Phase 3: Medium ✅
- [ ] `yaml_io.py`: Reference 치환 구현
- [ ] `core/exceptions.py`: 예외 클래스
- [ ] 에러 처리 개선 (logging)
- [ ] `README.md`: 사용 가이드
- [ ] `examples/`: 예시 코드

### Phase 4: Low ✅
- [ ] `policy.py`: `source_paths` 제거
- [ ] `__init__.py`: Factory 파라미터 정리
- [ ] 코드 리뷰 및 스타일 통일
- [ ] 최종 문서화

---

## 7. 결론

### 7.1 현재 상태
- ✅ **잘 설계된 구조**: 추상화, 정책 분리
- ⚠️ **구현 불완전**: Import 오류, 네이밍 불일치
- ⚠️ **테스트 부재**: 안정성 보장 어려움

### 7.2 개선 후 기대 효과
1. **안정성**: Import 오류 해결, 테스트 추가
2. **독립성**: VarsResolver 의존성 제거
3. **완전성**: Reference 치환 구현
4. **사용성**: README, 예시 추가
5. **유지보수성**: 명확한 책임 경계, 에러 처리

### 7.3 권장 순서
1. **Phase 1 (Critical)**: 즉시 수정 필요 (모듈 실행 실패 방지)
2. **Phase 2 (High)**: 1주일 내 완료 (안정성 확보)
3. **Phase 3 (Medium)**: 2주일 내 완료 (완전성 확보)
4. **Phase 4 (Low)**: 여유 시 진행 (품질 향상)

---

**문의**: GitHub Issue 또는 PR로 피드백 부탁드립니다.
