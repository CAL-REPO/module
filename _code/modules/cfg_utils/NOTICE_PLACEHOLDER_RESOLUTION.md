# NOTICE: Placeholder Resolution 및 Context Passing 문제 해결

**작성일**: 2025-10-19  
**버전**: cfg_utils v2  
**심각도**: HIGH - 핵심 기능 오류

---

## 📋 요약

ConfigLoader의 env 값 placeholder 해석 및 context 전달 과정에서 발생한 일련의 문제들을 해결했습니다. 주요 원인은 **중복된 상태 초기화**, **Placeholder 패턴 혼동**, **Import 경로 불일치**였습니다.

---

## 🐛 발생한 문제들

### 1. **env 값이 src 경로 해석에 전달되지 않음**

**증상**:
```yaml
src:
  - ["${configs_oto_dir}/image.yaml", "image"]
```
- `${configs_oto_dir}`가 빈 문자열로 해석되어 `/image.yaml`로 변환
- `FileNotFoundError: YAML file not found: /image.yaml`

**근본 원인**: 
- `loader.py` Line 207의 `self._state = None`이 env 처리된 상태를 덮어씀
- `_load()` 메서드 실행 시점에 `self._state`가 `None`
- env context 추출 실패 → 빈 context로 placeholder 해석 시도

### 2. **Placeholder 패턴 혼동**

**문제**:
- `${}`: KeyPath 참조 (예: `${env__CASHOP_PATHS__configs_oto_dir}`)
- `{{}}`: Context placeholder (예: `{{configs_oto_dir}}`)
- 패턴 혼용으로 인한 해석 실패

**영향**:
- KeyPathDict.resolve_all()이 `${configs_oto_dir}`를 KeyPath로 해석 시도
- Context에서 `configs_oto_dir`를 찾지 못해 빈 문자열 반환

### 3. **LogManager의 isinstance() 체크 실패**

**증상**:
```
Error: Failed to initialize logger: YAML file not found: default_log
```

**근본 원인**:
```python
# loader.py
from modules.logs_utils.core.policy import LogPolicy  # ← 이 경로로 import

# manager.py
from logs_utils.core.policy import LogPolicy  # ← 다른 경로로 import
```
- 동일한 클래스를 다른 경로로 import
- Python의 module cache 특성상 다른 객체로 인식
- `isinstance(cfg_like, LogPolicy)` → `False`

---

## ✅ 해결 방법

### 1. **중복된 self._state 초기화 제거**

**파일**: `modules/cfg_utils/service/loader.py`

**변경 전** (Line 147-152, 207):
```python
# Line 147-152: env 처리
self._state = KeyPathState(name="config")
if self.env is not None or (self.env_os is not None and self.env_os is not False):
    from .env_processor import EnvProcessor
    env_processor = EnvProcessor(env=self.env, env_os=self.env_os)
    self._state = env_processor.process(self._state)

# Line 207: 중복 초기화 ❌
self._state: Optional[KeyPathState] = None  # ← env 처리된 상태를 덮어씀!
```

**변경 후**:
```python
# Line 147-152: env 처리
self._state = KeyPathState(name="config")
if self.env is not None or (self.env_os is not None and self.env_os is not False):
    from .env_processor import EnvProcessor
    env_processor = EnvProcessor(env=self.env, env_os=self.env_os)
    self._state = env_processor.process(self._state)

# Line 207: 삭제됨 ✅
# KeyPath State는 이미 Line 147에서 초기화됨!
```

**효과**:
- `_load()` 메서드 실행 시 `self._state`에 env 섹션 유지
- env context 정상 추출 → placeholder 해석 가능

---

### 2. **Placeholder 패턴 통일**

**파일**: `configs/loader/config_loader_oto.yaml`

**변경 전**:
```yaml
source:
  src:
    - ["${configs_oto_dir}/image.yaml", "image"]  # ← KeyPath 패턴 (잘못된 사용)
```

**변경 후**:
```yaml
source:
  src:
    - ["{{configs_oto_dir}}/image.yaml", "image"]  # ← Context placeholder (올바른 사용)
```

**효과**:
- VarsResolver가 context에서 `configs_oto_dir` 검색
- `M:/CALife/CAShop - 구매대행/_code/configs/oto` 정상 resolve

---

### 3. **Duck Typing으로 isinstance() 대체**

**파일**: `modules/logs_utils/services/manager.py`

**변경 전**:
```python
def _load_config(self, cfg_like, **overrides) -> "LogPolicy":
    from logs_utils.core.policy import LogPolicy
    
    # isinstance() 체크 - import 경로 불일치로 실패 ❌
    if isinstance(cfg_like, LogPolicy):
        return cfg_like
```

**변경 후**:
```python
def _load_config(self, cfg_like, **overrides) -> "LogPolicy":
    from logs_utils.core.policy import LogPolicy
    
    # Duck typing: 클래스 이름으로 체크 ✅
    if cfg_like is not None and cfg_like.__class__.__name__ == "LogPolicy":
        if overrides:
            return cfg_like.model_copy(update=overrides)
        return cfg_like
```

**효과**:
- Import 경로와 무관하게 LogPolicy 인스턴스 인식
- Logger 정상 초기화

---

## ⚠️ 주의사항

### 1. **self._state 초기화는 한 번만!**

```python
# ❌ 잘못된 패턴
self._state = KeyPathState(name="config")
# ... 작업 ...
self._state = None  # 절대 재초기화 금지!

# ✅ 올바른 패턴
self._state = KeyPathState(name="config")
# ... 작업 ...
# self._state 유지
```

**이유**: env 처리 결과를 담은 `self._state`를 덮어쓰면 context 손실

---

### 2. **Placeholder 패턴 규칙 준수**

| 패턴 | 용도 | 예시 | 처리 |
|------|------|------|------|
| `${}` | KeyPath 참조 | `${env__CASHOP_PATHS__configs_dir}` | KeyPathDict.resolve_all() |
| `{{}}` | Context placeholder | `{{configs_oto_dir}}` | VarsResolver |

**규칙**:
1. **YAML 파일 경로**에는 `{{}}` 사용 (flat context)
2. **KeyPath 참조**에는 `${}` + `__` separator 사용
3. **Self-reference** (paths.local.yaml)에는 `{{}}` 사용

**예시**:
```yaml
# ✅ 올바른 사용
src:
  - ["{{configs_oto_dir}}/image.yaml", "image"]  # Context placeholder

# ❌ 잘못된 사용
src:
  - ["${configs_oto_dir}/image.yaml", "image"]  # KeyPath로 해석 시도 → 실패
```

---

### 3. **Import 경로 일관성 유지**

**문제가 되는 패턴**:
```python
# 모듈 A
from modules.logs_utils.core.policy import LogPolicy

# 모듈 B
from logs_utils.core.policy import LogPolicy  # 다른 경로!

# isinstance(obj, LogPolicy) → False (다른 객체로 인식)
```

**해결책**:
1. **Duck Typing 사용**: `obj.__class__.__name__ == "LogPolicy"`
2. **Import 경로 통일**: 프로젝트 전체에서 동일한 경로 사용

**권장 패턴**:
```python
# 모든 모듈에서 동일하게 사용
from modules.logs_utils.core.policy import LogPolicy
```

---

### 4. **Context Passing 체인 확인**

**흐름**:
```
1. EnvProcessor.process(state)
   → self._state에 env 섹션 생성

2. loader.py _load() 
   → env_context = self._state.to_dict().get("env", {})

3. SourcePolicy 생성
   → SourcePolicy(src=..., context=env_context)

4. source.py _extract_yaml()
   → self.policy.context에서 flattened_context 생성
   → KeyPathDict.resolve_all(context=flattened_context)
```

**체크포인트**:
- [ ] `self._state`가 None이 아닌가?
- [ ] `env_context`에 CASHOP_PATHS가 있는가?
- [ ] `SourcePolicy.context`가 전달되었는가?
- [ ] Flattened context에 필요한 키가 있는가?

---

## 🔍 디버깅 가이드

### 문제: "Placeholder가 빈 문자열로 해석됨"

**1단계**: self._state 확인
```python
# loader.py _load() 시작 부분
print(f"self._state is None: {self._state is None}")
if self._state:
    print(f"state keys: {list(self._state.to_dict().keys())}")
```

**2단계**: env_context 확인
```python
env_context = self._state.to_dict().get("env", {})
print(f"env_context keys: {list(env_context.keys())}")
```

**3단계**: source.py context 확인
```python
# source.py _extract_yaml()
print(f"self.policy.context: {self.policy.context}")
```

---

### 문제: "Logger 초기화 실패"

**1단계**: LogPolicy 타입 확인
```python
# loader.py _init_logger()
print(f"_log_policy type: {type(self._log_policy)}")
print(f"_log_policy class name: {self._log_policy.__class__.__name__}")
```

**2단계**: LogManager isinstance() 확인
```python
# manager.py _load_config()
print(f"cfg_like type: {type(cfg_like)}")
print(f"cfg_like module: {cfg_like.__class__.__module__}")
print(f"LogPolicy module: {LogPolicy.__module__}")
```

---

## 📊 테스트 결과

### 성공 케이스

```bash
$ python test_placeholder_resolution.py

================================================================================
Placeholder Resolution Test
================================================================================
2025-10-19 07:22:44 | INFO | ConfigLoader initialized with logger: cfg_loader
2025-10-19 07:22:44 | INFO | ConfigLoader._load() started
2025-10-19 07:22:44 | DEBUG | Processing multiple sources: 4 items
2025-10-19 07:22:44 | DEBUG | Processing source [0]: ('{{configs_oto_dir}}/image.yaml', 'image')
2025-10-19 07:22:44 | INFO | ConfigLoader._load() completed

1. ENV Section:
--------------------------------------------------------------------------------
CASHOP_PATHS keys: [..., 'configs_oto_dir', ...]
  configs_oto_dir: M:/CALife/CAShop - 구매대행/_code/configs/oto

2. Image Section:
--------------------------------------------------------------------------------
Image keys: ['source', 'save', 'meta', 'log']...

================================================================================
✅ Test completed!
================================================================================
```

**확인 사항**:
- ✅ Logger 초기화 성공
- ✅ env 섹션에 configs_oto_dir 존재
- ✅ Placeholder 정상 해석
- ✅ 모든 YAML 파일 로드 성공

---

## 📝 체크리스트

새로운 기능 개발 시 확인사항:

- [ ] `self._state` 재초기화 코드가 없는가?
- [ ] Placeholder 패턴이 올바른가? (`${}` vs `{{}}`)
- [ ] Import 경로가 프로젝트 표준을 따르는가?
- [ ] Context가 필요한 모든 계층에 전달되는가?
- [ ] isinstance() 대신 duck typing을 사용했는가? (필요 시)

---

## 🔗 관련 파일

- `modules/cfg_utils/service/loader.py` - ConfigLoader 핵심 로직
- `modules/cfg_utils/service/source.py` - Placeholder 해석
- `modules/cfg_utils/service/env_processor.py` - env 처리
- `modules/logs_utils/services/manager.py` - LogManager
- `configs/loader/config_loader_oto.yaml` - 설정 파일 예시

---

## 📚 참고 자료

1. **Placeholder Resolution 흐름도**: (TODO: 다이어그램 추가)
2. **Context Passing 아키텍처**: (TODO: 다이어그램 추가)
3. **Import 경로 표준**: `modules/` prefix 사용

---

**작성자**: AI Assistant  
**검토자**: (TODO)  
**승인일**: (TODO)
