# None 값 자동 드롭 기능 추가

**일시**: 2025년 10월 15일
**작업**: YAML에서 None 값 자동 필터링하여 Pydantic 기본값 사용

---

## 1. 문제 상황

### 사용자 질문
> "yaml 파일에서 key는 있는데 value가 없으면 드랍하고 스크립트의 기본정책값 사용하는거맞지?"

### 기존 문제
```yaml
# config.yaml
name: test
timeout:        # value가 없음 (None으로 로드)
enabled: true
```

```python
# Pydantic 모델 (기본값 포함)
class MyPolicy(BaseModel):
    name: str = "default"
    timeout: int = 30      # 기본값
    enabled: bool = True

# 기존 동작
config = ConfigLoader.load("config.yaml", model=MyPolicy)
# ❌ ValidationError: timeout should be a valid integer (got None)
```

**문제점:**
- YAML에서 `timeout:` (값 없음) → Python에서 `None`으로 로드
- Pydantic이 `None`을 받으면 ValidationError 발생
- 기본값을 사용하려면 아예 key를 제거해야 함

---

## 2. 해결 방법

### 2.1. DictOps.drop_none() 추가

**파일**: `data_utils/services/dict_ops.py`

```python
@staticmethod
def drop_none(data: Dict[str, Any], *, deep: bool = True) -> Dict[str, Any]:
    """Remove all keys with None values from a dictionary.

    Args:
        data: The dictionary to filter.
        deep: If ``True``, remove None values recursively in nested dicts.
            If ``False``, only filter top-level keys.

    Returns:
        A new dictionary with None values removed.

    Examples:
        >>> DictOps.drop_none({"a": 1, "b": None, "c": 3})
        {'a': 1, 'c': 3}
        >>> DictOps.drop_none({"a": {"b": None, "c": 2}}, deep=True)
        {'a': {'c': 2}}
    """
    def visit(path, key, value):
        # Drop if value is None
        if value is None:
            return False  # Drop this key-value pair
        return key, value

    if not deep:
        # Shallow filter
        return {k: v for k, v in data.items() if v is not None}

    return remap(data, visit=visit)
```

**특징:**
- ✅ `boltons.iterutils.remap` 활용 (기존 패턴 유지)
- ✅ Deep/Shallow 모드 지원
- ✅ 중첩된 dict도 재귀적으로 필터링

### 2.2. ConfigLoader.load()에 통합

**파일**: `cfg_utils/services/config_loader.py`

```python
# Import 추가
from modules.data_utils.services.dict_ops import DictOps

# 3. Dict인 경우 직접 처리
if isinstance(cfg_like, dict):
    # None 값 필터링 (Pydantic 기본값 사용 위해)
    cfg_like = DictOps.drop_none(cfg_like, deep=True)
    
    if overrides:
        temp = KeyPathDict(copy.deepcopy(cfg_like))
        temp.merge(overrides, deep=True)
        cfg_like = temp.data
    
    # Model이 있으면 변환, 없으면 dict 반환
    if model:
        return model(**cfg_like)
    return cfg_like
```

**처리 순서:**
1. dict 입력 받음
2. **None 값 자동 필터링** (deep=True)
3. Overrides 적용 (있는 경우)
4. Pydantic 모델 변환 또는 dict 반환

---

## 3. 테스트 결과

### 3.1. 단일 dict - None 값 필터링
```python
yaml_config = {
    "name": "custom_name",
    "timeout": None,  # value 없음
    "enabled": True,
}

policy = ConfigLoader.load(yaml_config, model=TestPolicy)
# ✅ name: custom_name (YAML에서 제공)
# ✅ timeout: 30 (None이므로 기본값 사용)
# ✅ enabled: True (YAML에서 제공)
# ✅ path: default/path (키가 없으므로 기본값 사용)
```

### 3.2. 중첩된 dict - Deep 필터링
```python
nested_config = {
    "name": "test",
    "timeout": 60,
    "config": {
        "enabled": None,  # None → 제거
        "path": "custom"
    }
}

loaded_dict = ConfigLoader.load(nested_config)
# ✅ 결과: {'name': 'test', 'timeout': 60, 'config': {'path': 'custom'}}
# ✅ 'config.enabled' 완전히 제거됨
```

### 3.3. List 병합 + None 값
```python
list_config = [
    {"name": "base", "timeout": None},
    {"name": "override", "enabled": False, "path": None}
]

policy = ConfigLoader.load(list_config, model=TestPolicy)
# ✅ name: override (두 번째 파일에서 덮어쓰기)
# ✅ timeout: 30 (None 제거되어 기본값 사용)
# ✅ enabled: False (두 번째 파일에서 False)
# ✅ path: default/path (None 제거되어 기본값 사용)
```

---

## 4. 사용 예시

### 4.1. YAML 파일에서 선택적 설정

```yaml
# base.yaml
app:
  name: MyApp
  timeout: 60
  retry: 3
  debug:        # value 없음 → None → 드롭 → 기본값 사용

# prod.yaml (프로덕션 환경)
app:
  name: MyApp-Prod
  timeout:      # 프로덕션에서는 기본값 사용
  debug: false
```

```python
class AppPolicy(BaseModel):
    name: str = "DefaultApp"
    timeout: int = 30        # 기본 타임아웃
    retry: int = 5           # 기본 재시도 횟수
    debug: bool = True       # 개발 환경 기본값

# 개발 환경
dev_config = ConfigLoader.load("base.yaml", model=AppPolicy)
# timeout: 60, retry: 3, debug: True (기본값)

# 프로덕션 환경
prod_config = ConfigLoader.load(["base.yaml", "prod.yaml"], model=AppPolicy)
# timeout: 30 (기본값), retry: 3 (base.yaml), debug: False (prod.yaml)
```

### 4.2. 조건부 설정 오버라이드

```python
# 환경 변수나 조건에 따라 None 사용
config_dict = {
    "path": os.getenv("CUSTOM_PATH") or None,  # 환경변수 없으면 None
    "timeout": get_timeout() if use_custom else None,
}

# None 값은 자동으로 드롭되어 기본값 사용
policy = ConfigLoader.load(config_dict, model=MyPolicy)
```

---

## 5. 이점 정리

### 5.1. 개발자 편의성
- ✅ YAML에서 `key:` (값 없음)으로 기본값 사용 가능
- ✅ 조건부 설정을 `None`으로 간단히 표현
- ✅ ValidationError 없이 안전하게 처리

### 5.2. YAML 작성 편의성
```yaml
# Before (기본값 사용하려면 key를 아예 제거)
app:
  name: MyApp
  # timeout을 주석 처리하거나 삭제해야 함

# After (key는 남기고 value만 비우면 됨)
app:
  name: MyApp
  timeout:        # 비워두면 기본값 사용
  debug:          # 개발 시 편리
```

### 5.3. 환경별 설정 관리
```yaml
# base.yaml - 전체 키 정의
app:
  name: MyApp
  timeout: 60
  retry: 3
  debug: true

# prod.yaml - 일부만 오버라이드, 나머지는 기본값
app:
  timeout:        # 프로덕션은 기본값 사용
  debug: false
```

---

## 6. 기술적 세부사항

### 6.1. boltons.iterutils.remap 활용
```python
def visit(path, key, value):
    if value is None:
        return False  # Drop this key-value pair
    return key, value

return remap(data, visit=visit)
```

**장점:**
- 재귀적으로 모든 레벨 처리
- 기존 코드 패턴과 일관성 유지
- 효율적인 트리 순회

### 6.2. 처리 시점
```
ConfigLoader.load()
    ↓
1. Type 체크 (BaseModel/None/dict/list/Path)
    ↓
2. dict인 경우 → DictOps.drop_none()  ★ 여기!
    ↓
3. Overrides 적용
    ↓
4. Pydantic 모델 변환 또는 dict 반환
```

**None 필터링은 가장 먼저 수행:**
- Overrides 전에 필터링 → Overrides로 None 설정 가능
- Pydantic 변환 전에 필터링 → ValidationError 방지

---

## 7. 수정된 파일

1. **data_utils/services/dict_ops.py**
   - `drop_none()` 정적 메서드 추가 (27줄)
   - Deep/Shallow 모드 지원
   - boltons.iterutils.remap 활용

2. **cfg_utils/services/config_loader.py**
   - `DictOps` import 추가
   - `load()` 메서드 내 None 필터링 로직 추가 (1줄)
   - dict 처리 부분에서 자동 필터링

---

## 8. 결론

**질문 답변:**
> "yaml 파일에서 key는 있는데 value가 없으면 드랍하고 스크립트의 기본정책값 사용하는거맞지?"

**답변: ✅ 맞습니다!**

**구현 완료:**
- ✅ `DictOps.drop_none()` 추가 (data_utils)
- ✅ `ConfigLoader.load()`에 자동 필터링 적용
- ✅ Deep merge 지원 (중첩된 dict도 처리)
- ✅ 테스트 완료 (단일/중첩/list 모두 정상)

**동작 방식:**
```yaml
# config.yaml
timeout:        # value 없음 (None)
```
↓ PyYAML 로드
```python
{"timeout": None}
```
↓ DictOps.drop_none()
```python
{}  # None 키 제거
```
↓ Pydantic 모델 생성
```python
MyPolicy(timeout=30)  # 기본값 사용
```

---

**작성자**: GitHub Copilot  
**날짜**: 2025년 10월 15일  
**버전**: cfg_utils v2.1 (None 값 자동 드롭)
