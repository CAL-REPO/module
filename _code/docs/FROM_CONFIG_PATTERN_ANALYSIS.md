# from_config 패턴과 ConfigLoader 기능 충돌 분석

> **작성일**: 2025-10-16  
> **목적**: from_config/from_dict 패턴 도입 시 ConfigLoader 기능과의 충돌 가능성 분석

---

## 📋 현재 ConfigLoader 핵심 기능

### 1️⃣ **3단계 Override 체계**

```python
ConfigLoader.load("config.yaml", model=MyPolicy, key="value")
```

**Override 순서**:
1. **BaseModel 기본값** (Pydantic defaults)
2. **YAML 파일** (있으면 override, 없으면 기본값 유지)
3. **Argument override** (kwargs)

### 2️⃣ **다수 파일 통합**

```python
# YamlParser의 source_paths 기능
ConfigLoader.load(
    None,
    policy_overrides={
        "yaml.source_paths": [
            {"path": "base.yaml", "section": "app"},
            {"path": "prod.yaml", "section": "app"},
            {"path": "local.yaml", "section": "app"}
        ]
    },
    model=MyPolicy
)
```

**특징**:
- 여러 YAML 파일을 순서대로 병합
- 각 파일에서 특정 section만 추출 가능
- Deep merge 지원

### 3️⃣ **Section 자동 감지**

```python
# config.yaml
app:
  image:
    max_width: 1024
    
ocr:
  provider: paddle

# 자동 감지
loader = ConfigLoader("config.yaml")
image_policy = loader.as_model(ImagePolicy)  # "image" 섹션 자동 추출
ocr_policy = loader.as_model(OcrPolicy)      # "ocr" 섹션 자동 추출
```

### 4️⃣ **Reference 해석**

```python
# config.yaml
base_url: "https://api.example.com"
endpoints:
  users: "${base_url}/users"      # -> "https://api.example.com/users"
  products: "${base_url}/products" # -> "https://api.example.com/products"
```

### 5️⃣ **Include 지시자**

```python
# main.yaml
app:
  !include common.yaml
  specific_setting: value

# common.yaml
timeout: 30
retry: 3
```

---

## 🔍 제안된 from_config 패턴

### ❌ 문제가 있는 설계

```python
class ImageLoader:
    @classmethod
    def from_config(cls, config_path: str, **overrides):
        """❌ ConfigLoader 기능 제한됨"""
        # 단순 로딩만 가능
        loader = ConfigLoader(config_path)
        policy = loader.as_model(ImageLoaderPolicy)
        
        # Override 적용 (간단한 update만 가능)
        if overrides:
            policy_dict = policy.model_dump()
            policy_dict.update(overrides)  # ❌ Shallow update만 가능
            policy = ImageLoaderPolicy(**policy_dict)
        
        return cls(policy)
```

**문제점**:
1. ❌ `source_paths` 기능 사용 불가
2. ❌ `policy_overrides` 전달 불가
3. ❌ Deep merge 불가능
4. ❌ Section 선택 불가

---

## ✅ 올바른 설계: ConfigLoader 기능 보존

### 방안 1: ConfigLoader.load()를 그대로 사용

```python
class ImageLoader:
    """ConfigLoader의 모든 기능 활용"""
    
    def __init__(self, policy: ImageLoaderPolicy):
        """Policy 객체만 받는 단순한 생성자"""
        self.policy = policy
        self.reader = ImageReader()
        self.writer = ImageWriter()
    
    @classmethod
    def from_config(
        cls,
        cfg_like: Union[str, Path, dict, list, None],
        *,
        policy_overrides: Optional[dict] = None,
        **overrides
    ) -> "ImageLoader":
        """ConfigLoader의 모든 기능을 그대로 전달
        
        Args:
            cfg_like: ConfigLoader.load()와 동일 (str/Path/dict/list/None)
            policy_overrides: ConfigPolicy 필드 override
            **overrides: 최종 데이터 override (deep merge)
        
        Examples:
            # 단일 파일
            loader = ImageLoader.from_config("image.yaml")
            
            # 여러 파일 병합
            loader = ImageLoader.from_config(["base.yaml", "prod.yaml"])
            
            # source_paths 사용
            loader = ImageLoader.from_config(
                None,
                policy_overrides={
                    "yaml.source_paths": [
                        {"path": "base.yaml", "section": "image"},
                        {"path": "prod.yaml", "section": "image"}
                    ]
                }
            )
            
            # Argument override (deep merge)
            loader = ImageLoader.from_config(
                "image.yaml",
                source__max_width=2048,  # KeyPath 형식
                processing__resize_mode="contain"
            )
        """
        # ConfigLoader.load()에 모든 파라미터 전달
        policy = ConfigLoader.load(
            cfg_like,
            model=ImageLoaderPolicy,
            policy_overrides=policy_overrides,
            **overrides
        )
        return cls(policy)
    
    @classmethod
    def from_dict(cls, config: dict) -> "ImageLoader":
        """Dictionary에서 로딩 (간단한 경우)"""
        policy = ImageLoaderPolicy(**config)
        return cls(policy)
```

**장점**:
- ✅ ConfigLoader의 모든 기능 사용 가능
- ✅ source_paths 지원
- ✅ policy_overrides 지원
- ✅ Deep merge 지원
- ✅ Section 자동 감지
- ✅ Reference/Include 해석

---

## 📊 기능 비교표

| 기능 | ConfigLoader.load() | ❌ 잘못된 from_config | ✅ 올바른 from_config |
|------|---------------------|---------------------|---------------------|
| 단일 파일 로딩 | ✅ | ✅ | ✅ |
| 여러 파일 병합 | ✅ | ❌ | ✅ |
| source_paths | ✅ | ❌ | ✅ |
| Section 자동 감지 | ✅ | ❌ | ✅ |
| Deep merge | ✅ | ❌ | ✅ |
| policy_overrides | ✅ | ❌ | ✅ |
| Reference 해석 | ✅ | ✅ (ConfigLoader 내부) | ✅ |
| Include 지시자 | ✅ | ✅ (ConfigLoader 내부) | ✅ |
| 환경변수 치환 | ✅ | ✅ (ConfigLoader 내부) | ✅ |

---

## 🎯 권장 사항

### 1️⃣ **from_config는 ConfigLoader.load()의 Wrapper로 구현**

```python
@classmethod
def from_config(cls, cfg_like, *, policy_overrides=None, **overrides):
    """단순히 ConfigLoader.load()를 호출하고 cls()로 감싸기만"""
    policy = ConfigLoader.load(
        cfg_like,
        model=cls._get_policy_class(),  # 각 클래스가 자신의 Policy 클래스 반환
        policy_overrides=policy_overrides,
        **overrides
    )
    return cls(policy)
```

### 2️⃣ **from_dict는 간단한 경우에만 사용**

```python
@classmethod
def from_dict(cls, config: dict):
    """테스트나 간단한 경우에만 사용"""
    policy = cls._get_policy_class()(**config)
    return cls(policy)
```

### 3️⃣ **__init__은 Policy 객체만 받기**

```python
def __init__(self, policy: ImageLoaderPolicy):
    """생성자는 단순하게"""
    self.policy = policy
    # ... 초기화
```

---

## 💡 사용 예시

### 예시 1: 단일 파일

```python
# Before (복잡)
loader = ImageLoader("image.yaml", max_width=1024)

# After (명확)
loader = ImageLoader.from_config("image.yaml", source__max_width=1024)
```

### 예시 2: 여러 파일 병합

```python
# Before (불가능했음)
# ...

# After (가능)
loader = ImageLoader.from_config([
    "base.yaml",
    "prod.yaml",
    "local.yaml"
], source__max_width=2048)
```

### 예시 3: source_paths 활용

```python
# 통합 설정 파일에서 여러 섹션 병합
loader = ImageLoader.from_config(
    None,
    policy_overrides={
        "yaml.source_paths": [
            {"path": "unified.yaml", "section": "image_base"},
            {"path": "unified.yaml", "section": "image_prod"},
            {"path": "local.yaml", "section": "image"}
        ]
    },
    source__max_width=2048
)
```

### 예시 4: policy_overrides 활용

```python
# ConfigLoader 자체 정책 변경
loader = ImageLoader.from_config(
    "image.yaml",
    policy_overrides={
        "merge_mode": "shallow",      # Deep merge 대신 shallow
        "drop_blanks": False,         # None 값 유지
        "resolve_reference": False    # Reference 해석 비활성화
    }
)
```

---

## 🚨 주의사항

### ❌ 하지 말아야 할 것

```python
# ❌ ConfigLoader 기능을 직접 재구현하지 말 것
@classmethod
def from_config(cls, config_path: str, **overrides):
    # ❌ 이렇게 하면 ConfigLoader의 모든 기능을 잃음
    with open(config_path) as f:
        data = yaml.safe_load(f)
    data.update(overrides)  # Shallow update만 가능
    policy = ImageLoaderPolicy(**data)
    return cls(policy)
```

### ✅ 해야 할 것

```python
# ✅ ConfigLoader.load()를 그대로 활용
@classmethod
def from_config(cls, cfg_like, *, policy_overrides=None, **overrides):
    policy = ConfigLoader.load(
        cfg_like,
        model=ImageLoaderPolicy,
        policy_overrides=policy_overrides,
        **overrides
    )
    return cls(policy)
```

---

## 📝 결론

### ✅ 충돌 없음 - 올바르게 설계하면

**핵심 원칙**:
1. `from_config`는 **ConfigLoader.load()의 Thin Wrapper**로만 구현
2. ConfigLoader의 모든 파라미터를 그대로 전달
3. 추가 로직을 넣지 않음 (단순히 `cls(policy)` 호출)

**장점**:
- ✅ ConfigLoader의 모든 기능 보존
- ✅ 깔끔한 API (`from_config`, `from_dict`)
- ✅ 생성자 단순화
- ✅ 테스트 용이
- ✅ IDE 지원 향상

**주의사항**:
- ⚠️ ConfigLoader 기능을 직접 재구현하지 말 것
- ⚠️ 단순 wrapper만 유지할 것
- ⚠️ 추가 로직이 필요하면 별도 메서드로 분리

---

## 🎯 최종 권장 패턴

```python
class ImageLoader:
    """이미지 로딩 서비스"""
    
    def __init__(self, policy: ImageLoaderPolicy):
        """단순 생성자 - Policy만 받음"""
        self.policy = policy
        self.reader = ImageReader()
        self.writer = ImageWriter()
    
    @classmethod
    def from_config(
        cls,
        cfg_like: Union[str, Path, dict, list, None],
        *,
        policy_overrides: Optional[dict] = None,
        **overrides
    ) -> "ImageLoader":
        """ConfigLoader.load()의 Thin Wrapper
        
        모든 파라미터를 ConfigLoader.load()에 그대로 전달하여
        ConfigLoader의 모든 기능(source_paths, section 감지, 
        deep merge, reference 해석 등)을 사용 가능하게 함.
        """
        policy = ConfigLoader.load(
            cfg_like,
            model=ImageLoaderPolicy,
            policy_overrides=policy_overrides,
            **overrides
        )
        return cls(policy)
    
    @classmethod
    def from_dict(cls, config: dict) -> "ImageLoader":
        """간단한 dict에서 로딩 (테스트용)"""
        policy = ImageLoaderPolicy(**config)
        return cls(policy)
    
    def run(self) -> ImageLoaderResult:
        """실행 (Dataclass 결과 반환)"""
        # ... 실행 로직
        return ImageLoaderResult(...)
```

**사용 예시**:
```python
# 모든 ConfigLoader 기능 사용 가능!
loader = ImageLoader.from_config(
    None,
    policy_overrides={
        "yaml.source_paths": [
            {"path": "base.yaml", "section": "image"},
            {"path": "prod.yaml", "section": "image"}
        ]
    },
    source__max_width=2048,
    processing__resize_mode="contain"
)

result = loader.run()
print(result.image.size)
```

---

**작성자**: GitHub Copilot  
**작성일**: 2025-10-16  
**버전**: 1.0.0
