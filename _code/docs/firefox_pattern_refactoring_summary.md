# Image Utils 리팩토링 완료 요약

## 완료된 작업

### ✅ Firefox 스타일 `__init__` 패턴 구현

**Before (Classmethod 패턴):**
```python
# 여러 개의 classmethod 필요
loader = ImageLoader.from_yaml("config.yaml", section="...", **overrides)
loader = ImageLoader.from_dict({"source": ...}, **overrides)
loader = ImageLoader(policy)  # Policy만 가능
```

**After (Firefox 패턴):**
```python
# __init__에서 모든 입력 형태 처리
loader = ImageLoader(cfg_like, section="...", log=..., **overrides)

# cfg_like 가능한 타입:
# - BaseModel (ImageLoaderPolicy)
# - Path/str (YAML 파일)
# - dict
# - None (빈 설정)
```

### ✅ 구현된 EntryPoint (3개)

1. **ImageLoader**
   - 이미지 로드, 복사, 기본 처리
   - `ImageLoader(cfg_like, section="image_loader", log=..., **overrides)`

2. **ImageOCR**
   - OCR 실행 및 결과 처리
   - `ImageOCR(cfg_like, section="image_ocr", log=..., **overrides)`

3. **ImageOverlay**
   - 텍스트 오버레이
   - `ImageOverlay(cfg_like, section="image_overlay", log=..., **overrides)`

### ✅ 핵심 변경사항

#### 1. `__init__` 시그니처 통일

```python
def __init__(
    self,
    cfg_like: Union[BaseModel, Path, str, dict, None] = None,
    *,
    section: str = "...",  # YAML 섹션명
    log: Optional[LogManager] = None,  # 외부 LogManager
    **overrides: Any  # Runtime overrides
):
    self.policy = self._load_config(cfg_like, section=section, **overrides)
    # ...
```

#### 2. `_load_config` 메서드 추가

```python
def _load_config(
    self,
    cfg_like: Union[BaseModel, Path, str, dict, None],
    *,
    section: str = "...",
    **overrides: Any
) -> Policy:
    # 1. Policy 인스턴스 → Override 적용
    if isinstance(cfg_like, Policy):
        if overrides:
            config_dict = cfg_like.model_dump()
            temp = KeyPathDict(config_dict)
            temp.merge(overrides, deep=True)
            return Policy(**temp.data)
        return cfg_like
    
    # 2. None → 빈 dict
    if cfg_like is None:
        cfg_like = {}
    
    # 3. YAML 파일 → ConfigLoader
    if isinstance(cfg_like, (str, Path)):
        loader = ConfigLoader(cfg_like)
        config_dict = loader.as_dict(section=section)
    # 4. Dict → Deep copy
    elif isinstance(cfg_like, dict):
        config_dict = copy.deepcopy(cfg_like)
    else:
        raise TypeError(f"Unsupported config type: {type(cfg_like)}")
    
    # 5. Runtime overrides → Deep merge
    if overrides:
        temp = KeyPathDict(config_dict)
        temp.merge(overrides, deep=True)
        config_dict = temp.data
    
    return Policy(**config_dict)
```

#### 3. Classmethod → Backward Compatibility Wrapper

```python
@classmethod
def from_yaml(cls, config_path, section="...", log=None, **overrides):
    """Backward compatibility wrapper"""
    return cls(config_path, section=section, log=log, **overrides)

@classmethod
def from_dict(cls, config_dict, log=None, **overrides):
    """Backward compatibility wrapper"""
    return cls(config_dict, log=log, **overrides)
```

### ✅ 테스트 결과

#### Test 1: Backward Compatibility (test_3tier_override.py)
```
✅ 통과: 4/4
- ✅ 3단 Override 패턴
- ✅ ImageOCR Override
- ✅ ImageOverlay Override
- ✅ Deep Merge
```

#### Test 2: New __init__ Pattern (test_new_init_pattern.py)
```
✅ 통과: 4/4
- ✅ ImageLoader 모든 패턴
- ✅ ImageOCR 모든 패턴
- ✅ ImageOverlay 모든 패턴
- ✅ Firefox 패턴 일치
```

### ✅ 사용 예제

#### 1. 가장 간단한 사용
```python
loader = ImageLoader({"source": {"path": "test.jpg"}})
```

#### 2. Runtime Override
```python
loader = ImageLoader(
    {"source": {"path": "base.jpg"}, "save": {"suffix": "_base"}},
    save={"suffix": "_override"}  # Deep merge
)
```

#### 3. Policy 직접 전달
```python
policy = ImageLoaderPolicy(source={"path": "test.jpg"})
loader = ImageLoader(policy)
```

#### 4. Policy + Override
```python
loader = ImageLoader(policy, save={"suffix": "_new"})
```

#### 5. YAML 파일
```python
loader = ImageLoader("config.yaml", section="image_loader")
```

#### 6. YAML + Override
```python
loader = ImageLoader(
    "config.yaml",
    section="image_loader",
    save={"suffix": "_override"}
)
```

#### 7. Backward Compatibility
```python
# 기존 코드도 여전히 작동
loader = ImageLoader.from_yaml("config.yaml", section="...")
loader = ImageLoader.from_dict({"source": ...})
```

## Firefox 패턴과의 비교

### BaseWebDriver (Firefox)
```python
class BaseWebDriver(ABC, Generic[T]):
    def __init__(
        self,
        cfg_like: Union[BaseModel, Path, str, dict, list, None] = None,
        *,
        policy: Optional[Any] = None,  # ConfigPolicy
        **overrides: Any
    ):
        self.config: T = self._load_config(cfg_like, policy=policy, **overrides)
    
    @abstractmethod
    def _load_config(self, cfg_like, *, policy=None, **overrides) -> T:
        pass
```

### ImageLoader (Image Utils)
```python
class ImageLoader:
    def __init__(
        self,
        cfg_like: Union[BaseModel, Path, str, dict, None] = None,
        *,
        section: str = "image_loader",  # YAML section
        log: Optional[LogManager] = None,  # LogManager
        **overrides: Any
    ):
        self.policy = self._load_config(cfg_like, section=section, **overrides)
    
    def _load_config(self, cfg_like, *, section="...", **overrides) -> Policy:
        # Implementation
        pass
```

### 차이점 및 공통점

#### 공통점:
- ✅ `cfg_like` 파라미터로 다양한 입력 형태 지원
- ✅ `**overrides`로 3단 override 지원
- ✅ `_load_config` 메서드에서 설정 처리
- ✅ `__init__`에서 모든 로직 집중

#### 차이점:
- `policy` (Firefox) vs `section` (Image Utils)
  - Firefox: ConfigPolicy로 merge_mode 등 제어
  - Image Utils: YAML section name 지정
- `log` 파라미터 추가 (Image Utils)
  - 외부 LogManager 주입 가능

## 장점

### 1. 일관성
- **Before:** 각 EntryPoint마다 다른 초기화 방식
- **After:** Firefox와 동일한 패턴 → 학습 비용 감소

### 2. 간결성
- **Before:** from_yaml, from_dict, __init__ 각각 구현
- **After:** _load_config 하나로 모든 케이스 처리

### 3. 유연성
- 다양한 입력 형태 지원: Policy, YAML, dict, None
- 3단 override: Base → Section → Runtime
- Deep merge: KeyPathDict로 중첩 오버라이드

### 4. Backward Compatibility
- 기존 from_yaml, from_dict도 작동
- 점진적 마이그레이션 가능

### 5. 타입 안전성
- Pydantic Policy로 검증
- TypeErrors, ValidationErrors 명확

## 파일 변경 내역

### Modified Files:

1. **`modules/image_utils/entry_points/image_loader.py`**
   - `__init__` 시그니처 변경
   - `_load_config` 메서드 추가
   - `from_yaml`, `from_dict` → backward compatibility wrapper

2. **`modules/image_utils/entry_points/image_ocr.py`**
   - 동일한 패턴 적용

3. **`modules/image_utils/entry_points/image_overlay.py`**
   - 동일한 패턴 적용

### New Files:

4. **`scripts/test_new_init_pattern.py`** (NEW)
   - 새로운 __init__ 패턴 테스트
   - 4/4 테스트 통과

5. **`docs/3tier_override_guide.md`** (UPDATED)
   - Firefox 패턴 비교 추가
   - 새로운 사용 예제 추가
   - Backward compatibility 설명 추가

## 다음 단계 (선택)

### Phase 4: 추가 문서화
- [ ] API Reference 문서
- [ ] Tutorial 가이드
- [ ] Migration 가이드 상세화

### Phase 5: 선택적 리팩토링
- [ ] `font_utils` 동일 패턴 적용
- [ ] `color_utils` 동일 패턴 적용

## 업데이트 이력

- **2024-10-15:** Firefox 스타일 `__init__` 패턴 구현 완료
- **2024-10-15:** 모든 테스트 통과 (8/8)
- **2024-10-15:** 문서 업데이트
