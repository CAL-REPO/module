# 미래 개선 사항: Config Architecture 통합

**작성일:** 2025-10-25  
**상태:** 계획 단계 (미구현)  
**우선순위:** Medium

---

## 📋 개요

현재 ConfigLikeLoader와 SectionExtractor의 역할 분리로 인해 발생하는 아키텍처 복잡성을 해결하고, 독립 모듈의 설정 파일 경로 관리를 정책 레벨로 통합하는 개선 사항.

### 현재 상황 (As-Is)

```python
# 독립 모듈 (단일 Policy)
class ImageLoad:
    def _load_config(self, cfg_like, **overrides):
        return ConfigLikeLoader.load(
            cfg_like=cfg_like,
            policy_class=ImageLoadPolicy,
            module_file=__file__,  # ⚠️ 하드코딩
            config_filename="image_load.yaml",  # ⚠️ 하드코딩
            **overrides
        )

# 다중 모듈 (여러 Policy 병합)
class OTO:
    def __init__(self, cfg_like=None, **overrides):
        merged_config = ConfigLikeLoader.load(...)  # 1단계: 전체 로드
        
        # 2단계: 각 Policy별 section 추출
        extracted = SectionExtractor.extract_batch(
            merged_config=merged_config,
            individual_cfgs={
                OTOPolicy: oto_cfg,
                ImageLoadPolicy: image_load_cfg,
                TranslatePolicy: translate_cfg
            }
        )
```

**문제점:**
1. `module_file=__file__`, `config_filename="..."` 파라미터가 모든 `_load_config()` 메서드에 반복
2. ConfigLikeLoader와 SectionExtractor가 분리되어 2단계 로딩 필요
3. 독립 모듈의 기본 YAML 경로를 Policy에서 관리할 수 없음

---

## 🎯 개선 목표

### 1. 독립 모듈 Policy에 `config_file_path` 정책 추가

```python
# image_utils/core/policy.py
class ImageLoadPolicy(BaseModel):
    """ImageLoad 정책"""
    
    name: str = "image_load"
    
    # ✨ NEW: 기본 설정 파일 경로
    config_file_path: Optional[str] = Field(
        default=None,
        description="기본 YAML 설정 파일 경로 (None이면 모듈 내부 configs/ 디렉토리 사용)"
    )
    
    image_source: ImageSourcePolicy = Field(default_factory=ImageSourcePolicy)
    # ... 기타 필드
```

**장점:**
- Policy 레벨에서 기본 설정 파일 위치 제어 가능
- 테스트/프로덕션 환경별 다른 YAML 파일 사용 용이
- `module_file=__file__` 파라미터 제거 가능

---

### 2. ConfigLikeLoader와 SectionExtractor 통합

#### 현재 구조 (분리)

```python
# ConfigLikeLoader (cfg_utils/services/config_like_loader.py)
class ConfigLikeLoader:
    @staticmethod
    def load(cfg_like, policy_class, module_file=None, config_filename=None, **overrides):
        # dict인 경우 Policy.name section 추출 (line 109)
        if isinstance(cfg_like, dict):
            section_name = policy_class().name
            cfg_like = cfg_like.get(section_name, {})
        # ... 나머지 로직

# SectionExtractor (cfg_utils/services/section_extractor.py)
class SectionExtractor:
    @staticmethod
    def extract_batch(merged_config: dict, individual_cfgs: dict) -> dict:
        """여러 Policy의 section을 한 번에 추출"""
        # Policy.name 기반 추출 로직
        # ...
```

**중복 지점:**
- ConfigLikeLoader: dict에서 `policy_class().name` section 추출
- SectionExtractor: dict에서 여러 Policy의 `Policy.name` section 추출
- 동일한 로직이 2개 클래스에 분산

#### 개선 구조 (통합)

```python
# ✨ NEW: ConfigLikeLoader 내부에 SectionExtractor 기능 통합
class ConfigLikeLoader:
    @staticmethod
    def load(
        cfg_like,
        policy_class,
        config_file_path: Optional[str] = None,  # ✨ NEW: Policy.config_file_path 지원
        **overrides
    ):
        """범용 설정 로더 (section 추출 기능 내장)
        
        Args:
            cfg_like: Policy instance, YAML path, dict, or None
            policy_class: Policy 클래스
            config_file_path: Policy에 정의된 기본 YAML 경로 (우선순위: cfg_like > config_file_path > module default)
            **overrides: Runtime overrides
        """
        # 1. cfg_like가 None인 경우 config_file_path 사용
        if cfg_like is None and config_file_path:
            cfg_like = Path(config_file_path)
        
        # 2. dict인 경우 Policy.name section 자동 추출
        if isinstance(cfg_like, dict):
            section_name = policy_class().name
            cfg_like = cfg_like.get(section_name, {})
        
        # 3. 나머지 로직 (기존 유지)
        # ...
    
    @staticmethod
    def load_batch(
        cfg_like,
        policy_classes: list[type],  # ✨ NEW: 여러 Policy 한 번에 로드
        **overrides
    ) -> dict[str, Any]:
        """여러 Policy를 한 번에 로드 (SectionExtractor 기능 통합)
        
        Args:
            cfg_like: 전체 merged config dict 또는 YAML path
            policy_classes: 로드할 Policy 클래스 리스트
            **overrides: Runtime overrides
        
        Returns:
            {policy_name: Policy instance} dict
        """
        # cfg_like를 dict로 변환
        if not isinstance(cfg_like, dict):
            merged_config = ConfigLoader(...).to_dict()
        else:
            merged_config = cfg_like
        
        result = {}
        for policy_cls in policy_classes:
            policy_name = policy_cls().name
            section_config = merged_config.get(policy_name, {})
            
            # 개별 overrides 적용 (KeyPath 지원)
            policy_overrides = {
                k.replace(f"{policy_name}__", ""): v
                for k, v in overrides.items()
                if k.startswith(f"{policy_name}__")
            }
            
            result[policy_name] = ConfigLikeLoader.load(
                cfg_like=section_config,
                policy_class=policy_cls,
                **policy_overrides
            )
        
        return result
```

---

## 📐 개선 후 사용 패턴 (To-Be)

### 독립 모듈 (단일 Policy)

```python
# image_utils/adapter/load.py
class ImageLoad:
    def __init__(self, cfg_like=None, **overrides):
        # ✨ Policy.config_file_path 자동 사용
        self.config = self._load_config(cfg_like, **overrides)
    
    def _load_config(self, cfg_like, **overrides) -> ImageLoadPolicy:
        """Policy에 정의된 config_file_path 사용"""
        return ConfigLikeLoader.load(
            cfg_like=cfg_like,
            policy_class=ImageLoadPolicy,
            config_file_path=ImageLoadPolicy().config_file_path,  # ✨ Policy에서 가져옴
            **overrides
        )
```

### 다중 모듈 (여러 Policy 병합)

```python
# oto/adapter/oto.py
class OTO:
    def __init__(self, cfg_like=None, oto_cfg=None, image_load_cfg=None, translate_cfg=None, **overrides):
        # ✨ 1단계로 통합: load_batch()로 모든 Policy 한 번에 로드
        policies = ConfigLikeLoader.load_batch(
            cfg_like=cfg_like or self._default_config_path(),
            policy_classes=[OTOPolicy, ImageLoadPolicy, TranslatePolicy],
            **overrides
        )
        
        # 개별 cfg_like 우선순위 적용
        self.config = oto_cfg or policies["oto"]
        self.image_load = ImageLoad(cfg_like=image_load_cfg or policies["image_load"])
        self.translate = Translate(cfg_like=translate_cfg or policies["translate"])
```

---

## 🔄 마이그레이션 단계

### Phase 1: Policy에 config_file_path 필드 추가

**대상 모듈:**
- `image_utils` (ImageLoadPolicy, TextRecognizePolicy, OverlayPolicy)
- `translate_utils` (TranslatePolicy)
- `xl_utils` (ExcelLoadPolicy)
- `crawl_utils` (WebDriverManagerPolicy)

**작업:**
```python
class SomePolicy(BaseModel):
    name: str = "some_module"
    config_file_path: Optional[str] = None  # ✨ 추가
    # ... 기존 필드
```

### Phase 2: ConfigLikeLoader.load_batch() 메서드 추가

**파일:** `modules/cfg_utils/services/config_like_loader.py`

**작업:**
1. `load_batch()` 정적 메서드 구현
2. KeyPath 기반 overrides 분배 로직 추가
3. 단위 테스트 작성

### Phase 3: SectionExtractor 사용처 마이그레이션

**대상:**
- `modules/oto/adapter/oto.py`
- `modules/crawl_utils/adapter/sync_crawl.py`

**변경:**
```python
# Before
merged_config = ConfigLikeLoader.load(...)
extracted = SectionExtractor.extract_batch(merged_config, individual_cfgs)

# After
policies = ConfigLikeLoader.load_batch(cfg_like, policy_classes, **overrides)
```

### Phase 4: SectionExtractor 클래스 Deprecate

**파일:** `modules/cfg_utils/services/section_extractor.py`

**작업:**
1. `@deprecated` 데코레이터 추가
2. Docstring에 `ConfigLikeLoader.load_batch()` 사용 권장 명시
3. 6개월 후 제거 계획 공지

---

## ✅ 예상 효과

### 1. 코드 간소화
```python
# Before (21줄)
def _load_config(self, cfg_like, **overrides):
    from cfg_utils.services import ConfigLikeLoader
    
    return ConfigLikeLoader.load(
        cfg_like=cfg_like,
        policy_class=ImageLoadPolicy,
        module_file=__file__,
        config_filename="image_load.yaml",
        **overrides
    )

# After (6줄)
def _load_config(self, cfg_like, **overrides):
    return ConfigLikeLoader.load(
        cfg_like=cfg_like,
        policy_class=ImageLoadPolicy,
        config_file_path=ImageLoadPolicy().config_file_path,
        **overrides
    )
```

### 2. 유지보수성 향상
- 설정 파일 경로를 Policy에서 중앙 관리
- 테스트 시 `config_file_path` override로 다른 YAML 사용 가능
- 하드코딩된 `module_file`, `config_filename` 파라미터 제거

### 3. 아키텍처 단순화
- ConfigLikeLoader 단일 진입점으로 통합
- SectionExtractor 제거로 학습 곡선 감소
- 2단계 로딩 → 1단계 로딩 (load_batch)

---

## ⚠️ 고려사항

### 1. 하위 호환성
- 기존 `module_file`, `config_filename` 파라미터 유지 (deprecated)
- 6개월 전환 기간 후 제거

### 2. 성능 영향
- `load_batch()`는 여러 Policy를 순차 로드 (병렬화 불가)
- 대부분 케이스에서 무시할 수준 (3-5개 Policy)

### 3. 테스트 커버리지
- ConfigLikeLoader.load_batch() 단위 테스트 필수
- OTO, SyncCrawl 통합 테스트 업데이트 필요

---

## 📚 참고 문서

- [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md) - ConfigLoader 환경변수 설정
- [MODULE_ANALYSIS_AND_XLOTO_IMPROVEMENTS.md](./MODULE_ANALYSIS_AND_XLOTO_IMPROVEMENTS.md) - 모듈 분석
- [cfg_utils/services/config_like_loader.py](../modules/cfg_utils/services/config_like_loader.py) - 현재 ConfigLikeLoader 구현
- [cfg_utils/services/section_extractor.py](../modules/cfg_utils/services/section_extractor.py) - 현재 SectionExtractor 구현

---

## 🗓️ 일정 (예상)

| Phase | 작업 내용 | 예상 소요 | 우선순위 |
|-------|----------|----------|---------|
| Phase 1 | Policy에 config_file_path 추가 | 1일 | High |
| Phase 2 | ConfigLikeLoader.load_batch() 구현 | 2일 | High |
| Phase 3 | OTO/SyncCrawl 마이그레이션 | 1일 | Medium |
| Phase 4 | SectionExtractor deprecate | 0.5일 | Low |

**총 예상 소요:** 4.5일

---

**작성자:** GitHub Copilot  
**검토자:** (미정)  
**승인자:** (미정)
