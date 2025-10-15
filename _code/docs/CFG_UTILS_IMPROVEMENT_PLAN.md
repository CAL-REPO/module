# cfg_utils 완벽화 계획

## 현재 문제점

### 1. 각 모듈에서 50줄 이상의 반복 코드
```python
# image_loader.py, image_ocr.py, translator.py 등 모든 모듈에서 동일
def _load_config(self, cfg_like, *, policy=None, **overrides):
    section = None
    
    # Policy 인스턴스 체크
    if isinstance(cfg_like, MyPolicy):
        if overrides:
            config_dict = cfg_like.model_dump()
            temp = KeyPathDict(config_dict)
            temp.merge(overrides, deep=True)
            return MyPolicy(**temp.data)
        return cfg_like
    
    # None 처리
    if cfg_like is None:
        default_config = Path(...) / "default.yaml"
        if default_config.exists():
            cfg_like = default_config
        else:
            cfg_like = {}
    
    # YAML 로드
    if isinstance(cfg_like, (str, Path)):
        loader = ConfigLoader(cfg_like)
        section = loader.policy.yaml_policy.default_section
        config_dict = loader.as_dict(section=section)
    elif isinstance(cfg_like, dict):
        config_dict = copy.deepcopy(cfg_like)
    
    # Overrides 적용
    if overrides:
        temp = KeyPathDict(config_dict)
        temp.merge(overrides, deep=True)
        config_dict = temp.data
    
    return MyPolicy(**config_dict)
```

**문제:**
- 7개 모듈에서 동일한 로직 반복
- 유지보수 어려움 (한 곳 수정하면 7곳 수정)
- 각 모듈 개발자가 복잡한 로직 이해 필요

---

## 해결 방안

### 1. ConfigLoader에 헬퍼 메서드 추가

#### `ConfigLoader.load_as_model()` - 정적 메서드
```python
# cfg_utils/services/config_loader.py

@staticmethod
def load_as_model(
    cfg_like: Union[BaseModel, PathLike, dict, None],
    model_class: Type[BaseModel],
    *,
    policy: Optional[ConfigPolicy] = None,
    default_file: Optional[Path] = None,
    **overrides: Any
) -> BaseModel:
    """설정을 Pydantic 모델로 로드 (헬퍼 메서드)
    
    Args:
        cfg_like: 설정 소스 (BaseModel/Path/dict/None)
        model_class: 타겟 Pydantic 모델 클래스
        policy: ConfigPolicy (optional)
        default_file: cfg_like가 None일 때 사용할 기본 파일
        **overrides: 런타임 오버라이드
    
    Returns:
        model_class 인스턴스
    
    Example:
        >>> config = ConfigLoader.load_as_model(
        ...     "image.yaml",
        ...     ImageLoaderPolicy,
        ...     source__path="override.jpg"
        ... )
    """
    # 1. 이미 모델 인스턴스인 경우
    if isinstance(cfg_like, model_class):
        if not overrides:
            return cfg_like
        # Overrides 적용
        config_dict = cfg_like.model_dump()
        from keypath_utils import KeyPathDict
        temp = KeyPathDict(config_dict)
        temp.merge(overrides, deep=True)
        return model_class(**temp.data)
    
    # 2. None인 경우 기본 파일 사용
    if cfg_like is None:
        if default_file and default_file.exists():
            cfg_like = default_file
        else:
            cfg_like = {}
    
    # 3. ConfigLoader로 로드
    if isinstance(cfg_like, (str, Path)):
        loader = ConfigLoader(cfg_like, policy=policy)
        section = loader.policy.yaml_policy.default_section
        return loader.as_model(model_class, section=section, **overrides)
    
    # 4. Dict인 경우
    elif isinstance(cfg_like, dict):
        if overrides:
            from keypath_utils import KeyPathDict
            temp = KeyPathDict(copy.deepcopy(cfg_like))
            temp.merge(overrides, deep=True)
            return model_class(**temp.data)
        return model_class(**cfg_like)
    
    else:
        raise TypeError(f"Unsupported config type: {type(cfg_like)}")
```

---

### 2. 각 모듈 코드 간소화

#### Before (50줄):
```python
def _load_config(self, cfg_like, *, policy=None, **overrides):
    section = None
    
    if isinstance(cfg_like, ImageLoaderPolicy):
        if overrides:
            config_dict = cfg_like.model_dump()
            temp = KeyPathDict(config_dict)
            temp.merge(overrides, deep=True)
            return ImageLoaderPolicy(**temp.data)
        return cfg_like
    
    if cfg_like is None:
        default_config = Path(__file__).parent.parent.parent.parent / "configs" / "image.yaml"
        if default_config.exists():
            cfg_like = default_config
        else:
            cfg_like = {}
    
    if isinstance(cfg_like, (str, Path)):
        loader = ConfigLoader(cfg_like)
        section = loader.policy.yaml_policy.default_section
        config_dict = loader.as_dict(section=section)
    elif isinstance(cfg_like, dict):
        config_dict = copy.deepcopy(cfg_like)
    else:
        raise TypeError(f"Unsupported config type: {type(cfg_like)}")
    
    if overrides:
        temp = KeyPathDict(config_dict)
        temp.merge(overrides, deep=True)
        config_dict = temp.data
    
    return ImageLoaderPolicy(**config_dict)
```

#### After (5줄):
```python
def _load_config(self, cfg_like, *, policy=None, **overrides):
    default_file = Path(__file__).parent.parent.parent.parent / "configs" / "image.yaml"
    return ConfigLoader.load_as_model(
        cfg_like, ImageLoaderPolicy, policy=policy, default_file=default_file, **overrides
    )
```

---

### 3. 더 나아가기: Auto-discovery

#### `ConfigLoader.auto_load()` - 규칙 기반 자동 로드
```python
@staticmethod
def auto_load(
    cfg_like: Union[BaseModel, PathLike, dict, None],
    model_class: Type[BaseModel],
    *,
    policy: Optional[ConfigPolicy] = None,
    module_name: str,  # "image_utils", "translate_utils" 등
    **overrides: Any
) -> BaseModel:
    """규칙 기반 자동 로드
    
    Args:
        module_name: 모듈명 (configs/{module_name}.yaml 자동 탐색)
    
    Example:
        >>> config = ConfigLoader.auto_load(
        ...     None,  # 자동으로 configs/image.yaml 찾음
        ...     ImageLoaderPolicy,
        ...     module_name="image"
        ... )
    """
    # 기본 파일 자동 탐색
    if cfg_like is None:
        # 프로젝트 루트/configs/{module_name}.yaml
        project_root = Path.cwd()
        while project_root.parent != project_root:
            configs_dir = project_root / "configs"
            if configs_dir.exists():
                default_file = configs_dir / f"{module_name}.yaml"
                if default_file.exists():
                    cfg_like = default_file
                    break
            project_root = project_root.parent
    
    return ConfigLoader.load_as_model(
        cfg_like, model_class, policy=policy, **overrides
    )
```

#### 사용 예시:
```python
# image_loader.py
def _load_config(self, cfg_like, *, policy=None, **overrides):
    return ConfigLoader.auto_load(
        cfg_like, 
        ImageLoaderPolicy, 
        module_name="image",
        policy=policy,
        **overrides
    )
```

---

## 구현 우선순위

### Phase 1: 핵심 헬퍼 메서드 (HIGH)
- ✅ `ConfigLoader.load_as_model()` 구현
- ✅ 모든 모듈에 적용 (7개)
- ✅ 테스트 작성

### Phase 2: Auto-discovery (MEDIUM)
- `ConfigLoader.auto_load()` 구현
- 프로젝트 루트 탐색 로직
- 모듈명 기반 자동 매핑

### Phase 3: 고급 기능 (LOW)
- `ConfigLoader.from_env()` - 환경 변수에서 로드
- `ConfigLoader.from_multiple()` - 여러 파일 병합
- `ConfigLoader.watch()` - 파일 변경 감지

---

## 최종 목표: 사용자 경험

### Before:
```python
class ImageLoader:
    def __init__(self, cfg_like=None, *, policy=None, **overrides):
        self.config = self._load_config(cfg_like, policy=policy, **overrides)
    
    def _load_config(self, cfg_like, *, policy=None, **overrides):
        # 50줄의 복잡한 로직...
        section = None
        if isinstance(cfg_like, ImageLoaderPolicy):
            # ...
        if cfg_like is None:
            # ...
        if isinstance(cfg_like, (str, Path)):
            # ...
        # ...
        return ImageLoaderPolicy(**config_dict)
```

### After:
```python
class ImageLoader:
    def __init__(self, cfg_like=None, *, policy=None, **overrides):
        self.config = ConfigLoader.load_as_model(
            cfg_like, 
            ImageLoaderPolicy,
            policy=policy,
            default_file=Path(__file__).parent.parent.parent.parent / "configs" / "image.yaml",
            **overrides
        )
```

**절감:**
- 50줄 → 5줄 (90% 감소)
- 복잡도: O(50) → O(1)
- 유지보수: 7곳 → 1곳

---

## 다음 단계

1. `ConfigLoader.load_as_model()` 구현
2. 7개 모듈에 적용
3. 테스트 및 검증
4. 문서화

**예상 소요 시간:** 30분
**예상 코드 감소:** ~350줄 (50줄 × 7개 모듈)
