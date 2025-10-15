# 3단 Override 패턴 가이드 (Firefox 스타일)

## 개요

`image_utils`의 모든 EntryPoint는 `FirefoxWebDriver`와 동일한 `__init__` 패턴을 사용합니다.

**핵심 변경사항:**
- ❌ 기존: `from_yaml()`, `from_dict()` classmethod 사용
- ✅ 신규: `__init__(cfg_like, **overrides)` 직접 사용
- ✅ Backward compatibility: 기존 classmethod도 여전히 작동

## Firefox 패턴과의 일치

### FirefoxWebDriver 패턴

```python
from crawl_utils.provider import FirefoxWebDriver

# cfg_like: Policy, Path, str, dict, list, None
driver = FirefoxWebDriver(
    cfg_like,
    policy=ConfigPolicy(...),  # Optional
    **overrides
)
```

### ImageLoader 패턴 (동일!)

```python
from image_utils import ImageLoader

# cfg_like: Policy, Path, str, dict, None
loader = ImageLoader(
    cfg_like,
    section="image_loader",  # Optional (YAML only)
    log=LogManager(...),     # Optional
    **overrides
)
```

## 3단 Override 체계

### 1단: Base Configuration (기본 설정)
YAML 파일 또는 Dictionary에 정의된 기본 설정

### 2단: Section Extraction (섹션 추출)
YAML 파일 사용 시 특정 섹션만 추출 (optional)

### 3단: Runtime Overrides (런타임 오버라이드)
`__init__()` 호출 시 전달되는 `**kwargs`로 동적 오버라이드

## 지원하는 EntryPoint

- `ImageLoader`
- `ImageOCR`
- `ImageOverlay`

## 사용 방법

### 1. Dict로 초기화 (가장 간단)

```python
from image_utils import ImageLoader

# 간단한 초기화
loader = ImageLoader({"source": {"path": "test.jpg"}})

# Runtime override
loader = ImageLoader(
    {"source": {"path": "base.jpg"}, "save": {"suffix": "_base"}},
    save={"suffix": "_override"}  # 3단 override
)

# 결과:
# - source.path: "base.jpg" (유지)
# - save.suffix: "_override" (오버라이드)
```

### 2. YAML 파일에서 로드

```python
from image_utils import ImageLoader

# YAML 파일 구조:
# image_loader:
#   source:
#     path: "base.jpg"
#   save:
#     suffix: "_base"
#     directory: "output/base"

# Section 추출 + Runtime override
loader = ImageLoader(
    "config.yaml",
    section="image_loader",  # 2단: 섹션 지정
    save={"suffix": "_custom", "directory": "output/custom"}  # 3단: 런타임 오버라이드
)

# 결과:
# - source.path: "base.jpg" (YAML에서 유지)
# - save.suffix: "_custom" (런타임 오버라이드)
# - save.directory: "output/custom" (런타임 오버라이드)
```

### 3. Policy 객체로 초기화

```python
from image_utils import ImageLoader, ImageLoaderPolicy

# Policy 생성
policy = ImageLoaderPolicy(
    source={"path": "test.jpg"},
    save={"suffix": "_processed"}
)

# Policy 직접 전달
loader = ImageLoader(policy)

# Policy + Runtime override
loader = ImageLoader(
    policy,
    save={"suffix": "_new"}  # 기존 policy 오버라이드
)

# 결과:
# - source.path: "test.jpg" (유지)
# - save.suffix: "_new" (오버라이드)
```

### 4. Nested Override (중첩 오버라이드)

```python
from image_utils import ImageOCR

base_config = {
    "source": {"path": "test.jpg"},
    "provider": {
        "provider": "paddle",
        "min_conf": 0.5,
        "langs": ["ch", "en"]
    }
}

# 특정 필드만 오버라이드
ocr = ImageOCR(
    base_config,
    provider={"min_conf": 0.9}  # 부분 오버라이드
)

# 결과:
# - provider.provider: "paddle" (유지)
# - provider.min_conf: 0.9 (오버라이드)
# - provider.langs: ["ch", "en"] (유지)
```

### 5. ImageOverlay 예제

```python
from image_utils import ImageOverlay

# Dict + Runtime override
overlay = ImageOverlay(
    {"source": {"path": "original.jpg"}, "texts": [], "background_opacity": 0.5},
    background_opacity=0.9  # 간단한 오버라이드
)

# 결과:
# - source.path: "original.jpg" (유지)
# - texts: [] (유지)
# - background_opacity: 0.9 (오버라이드)
```

## Backward Compatibility

기존 `from_yaml()`, `from_dict()` classmethod도 여전히 작동합니다:

```python
# ✅ 기존 방식 (여전히 작동)
loader = ImageLoader.from_yaml("config.yaml", section="image_loader")
loader = ImageLoader.from_dict({"source": {"path": "test.jpg"}})

# ✅ 새로운 방식 (권장)
loader = ImageLoader("config.yaml", section="image_loader")
loader = ImageLoader({"source": {"path": "test.jpg"}})
```

## Deep Merge 동작 방식

### KeyPathDict 활용

내부적으로 `keypath_utils.KeyPathDict`의 `merge(deep=True)` 메서드를 사용하여 중첩된 딕셔너리를 안전하게 병합합니다.

```python
# image_loader.py의 _load_config 구현:
def _load_config(self, cfg_like, *, section="image_loader", **overrides):
    # ... (cfg_like 타입 판별)
    
    # Runtime overrides 적용
    if overrides:
        from keypath_utils import KeyPathDict
        temp = KeyPathDict(config_dict)
        temp.merge(overrides, deep=True)
        config_dict = temp.data
    
    return ImageLoaderPolicy(**config_dict)
```

### Deep Merge 예제

```python
base = {
    "source": {
        "path": "base.jpg",
        "must_exist": True,
        "convert_mode": "RGB"
    },
    "save": {
        "suffix": "_base",
        "quality": 90,
        "save_copy": True
    }
}

loader = ImageLoader(
    base,
    source={"path": "override.jpg"}  # source.path만 변경
)

# 병합 결과:
# {
#     "source": {
#         "path": "override.jpg",  # ← 오버라이드
#         "must_exist": True,       # ← 유지
#         "convert_mode": "RGB"     # ← 유지
#     },
#     "save": {
#         "suffix": "_base",        # ← 완전히 유지
#         "quality": 90,
#         "save_copy": True
#     }
# }
```

## Firefox 패턴과의 일관성

### BaseWebDriver 패턴

```python
class BaseWebDriver(ABC, Generic[T]):
    def __init__(
        self,
        cfg_like: Union[BaseModel, Path, str, dict, list, None] = None,
        *,
        policy: Optional[Any] = None,
        **overrides: Any
    ):
        self.config: T = self._load_config(cfg_like, policy=policy, **overrides)
        # ...
    
    @abstractmethod
    def _load_config(self, cfg_like, *, policy=None, **overrides) -> T:
        # Implementation by subclass
        pass
```

### ImageLoader 패턴 (동일 구조!)

```python
class ImageLoader:
    def __init__(
        self,
        cfg_like: Union[BaseModel, Path, str, dict, None] = None,
        *,
        section: str = "image_loader",
        log: Optional[LogManager] = None,
        **overrides: Any
    ):
        self.policy = self._load_config(cfg_like, section=section, **overrides)
        # ...
    
    def _load_config(self, cfg_like, *, section="image_loader", **overrides):
        # 1. Policy 인스턴스 처리
        if isinstance(cfg_like, ImageLoaderPolicy):
            if overrides:
                # Deep merge
                from keypath_utils import KeyPathDict
                config_dict = cfg_like.model_dump()
                temp = KeyPathDict(config_dict)
                temp.merge(overrides, deep=True)
                return ImageLoaderPolicy(**temp.data)
            return cfg_like
        
        # 2. None → 빈 dict
        if cfg_like is None:
            cfg_like = {}
        
        # 3. YAML 파일
        if isinstance(cfg_like, (str, Path)):
            loader = ConfigLoader(cfg_like)
            config_dict = loader.as_dict(section=section)
        # 4. Dict
        elif isinstance(cfg_like, dict):
            config_dict = copy.deepcopy(cfg_like)
        else:
            raise TypeError(f"Unsupported config type: {type(cfg_like)}")
        
        # 5. Runtime overrides 적용
        if overrides:
            from keypath_utils import KeyPathDict
            temp = KeyPathDict(config_dict)
            temp.merge(overrides, deep=True)
            config_dict = temp.data
        
        return ImageLoaderPolicy(**config_dict)
```

## 주요 특징

### 1. 원본 보호 (Immutability)
`copy.deepcopy()`를 사용하여 전달된 `config_dict`를 변경하지 않습니다.

```python
base_config = {"source": {"path": "base.jpg"}}

loader1 = ImageLoader(base_config, source={"path": "one.jpg"})
loader2 = ImageLoader(base_config, source={"path": "two.jpg"})

# base_config는 변경되지 않음!
assert base_config["source"]["path"] == "base.jpg"
```

### 2. 부분 오버라이드 (Partial Override)
중첩된 딕셔너리에서 일부 필드만 오버라이드 가능

```python
ocr = ImageOCR(
    {
        "provider": {
            "provider": "paddle",
            "min_conf": 0.5,
            "langs": ["ch", "en"]
        }
    },
    provider={"min_conf": 0.9}  # min_conf만 변경, 나머지 유지
)
```

### 3. 타입 안전성 (Type Safety)
Pydantic Policy 클래스를 통해 타입 검증

```python
loader = ImageLoader(
    {"source": {"path": "test.jpg"}},
    save={"quality": "invalid"}  # ← ValidationError 발생!
)
```

## 테스트 검증

### 테스트 파일
- `scripts/test_3tier_override.py` - Backward compatibility 테스트 (4/4 통과)
- `scripts/test_new_init_pattern.py` - 새로운 __init__ 패턴 테스트 (4/4 통과)

### 검증 항목
1. ✅ Dict로 초기화
2. ✅ Dict + Runtime override
3. ✅ Policy 직접 전달
4. ✅ Policy + Runtime override
5. ✅ YAML 파일 로드
6. ✅ YAML + Section + Runtime override
7. ✅ Nested override with preservation
8. ✅ Deep merge 동작
9. ✅ Backward compatibility (from_yaml, from_dict)

### 실행 방법

```bash
# 새로운 패턴 테스트
cd "m:\CALife\CAShop - 구매대행\_code"
python scripts\test_new_init_pattern.py

# Backward compatibility 테스트
python scripts\test_3tier_override.py
```

### 예상 출력

```
============================================================
테스트 결과 요약
============================================================

✅ 통과: 4/4
❌ 실패: 0/4

🎉 모든 테스트 통과!
```

## 마이그레이션 가이드

### 기존 코드 (Classmethod)

```python
# 기존: ConfigLoader 직접 사용
from cfg_utils import ConfigLoader
from image_utils.core.policy import ImageLoaderPolicy

loader_cfg = ConfigLoader("config.yaml")
config = loader_cfg.as_dict(section="image_loader")
policy = ImageLoaderPolicy(**config)

# 수동으로 오버라이드
policy.save.suffix = "_custom"
```

### 새로운 코드 (3단 Override)

```python
# 새로운: EntryPoint 사용
from image_utils import ImageLoader

loader = ImageLoader.from_yaml(
    "config.yaml",
    section="image_loader",
    save={"suffix": "_custom"}  # 한 줄로 오버라이드!
)
```

## 베스트 프랙티스

### 1. YAML 구조화

```yaml
# config/image.yaml
image_loader:
  source:
    must_exist: true
    convert_mode: RGB
  save:
    save_copy: true
    suffix: _processed
    quality: 90
    directory: output/images

image_ocr:
  provider:
    name: paddle
    min_conf: 0.5
    langs: [ch, en]
  save:
    save_results: true
```

### 2. 환경별 오버라이드

```python
# 개발 환경
loader = ImageLoader.from_yaml(
    "config/image.yaml",
    section="image_loader",
    save={"directory": "output/dev"}
)

# 프로덕션 환경
loader = ImageLoader.from_yaml(
    "config/image.yaml",
    section="image_loader",
    save={"directory": "/var/app/output"}
)
```

### 3. 동적 설정 생성

```python
def create_loader(env: str, suffix: str):
    return ImageLoader.from_yaml(
        "config/image.yaml",
        section="image_loader",
        save={
            "directory": f"output/{env}",
            "suffix": suffix
        }
    )

dev_loader = create_loader("dev", "_dev")
prod_loader = create_loader("prod", "_final")
```

## 문제 해결

### Path 타입 비교 이슈

Policy는 Path 객체를 사용하므로 문자열 비교 시 `str()` 변환 필요:

```python
loader = ImageLoader.from_dict(
    {"source": {"path": "test.jpg"}},
    source={"path": "override.jpg"}
)

# ❌ 잘못된 비교
assert loader.policy.source.path == "override.jpg"  # False!

# ✅ 올바른 비교
assert str(loader.policy.source.path) == "override.jpg"  # True
```

### Deep Copy 누락 시

원본 dict가 변경되는 문제:

```python
# ❌ 문제 발생
base = {"source": {"path": "base.jpg"}}
loader1 = ImageLoader.from_dict(base, source={"path": "one.jpg"})
loader2 = ImageLoader.from_dict(base, source={"path": "two.jpg"})
# base["source"]["path"] = "two.jpg" (변경됨!)

# ✅ 해결: from_dict 내부에서 copy.deepcopy() 사용
# EntryPoint 구현에서 이미 처리됨
```

## 관련 문서

- [firefox.py 구현](../modules/firefox/driver.py)
- [KeyPathDict 가이드](../modules/keypath_utils/___README___.md)
- [ImageLoader API](./image_utils_api.md)
- [테스트 코드](../scripts/test_3tier_override.py)

## 업데이트 이력

- 2024-10-15: 3단 override 패턴 구현 완료 (4/4 테스트 통과)
- 2024-10-15: Deep copy 추가로 원본 dict 보호
- 2024-10-15: 문서 작성
