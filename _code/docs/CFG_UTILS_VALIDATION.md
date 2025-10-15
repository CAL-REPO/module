# cfg_utils 검증 및 잠재적 문제점 분석

## ✅ 완벽한 부분

### 1. ConfigLoader 자신의 정책 로드 (Bootstrapping)
```python
def _load_loader_policy(self, policy: Optional[ConfigPolicy] = None) -> ConfigPolicy:
    # 재귀 방지: 간단한 YamlParser로 직접 파싱
    parser = YamlParser(policy=BaseParserPolicy(...))
    parsed = parser.parse(text, base_path=default_loader_policy_path)
    return ConfigPolicy(**policy_dict)
```
- ✅ 재귀 로딩 완벽하게 방지
- ✅ 각 모듈에서 독립적으로 설정 가능

### 2. 각 모듈의 독립성
```python
# image_ocr.py
loader_policy = ConfigPolicy(loader_policy_path=loader_config_path)
loader = ConfigLoader(cfg_like, policy=loader_policy)
section = loader_policy.yaml_policy.default_section
```
- ✅ loader_policy_path로 각 모듈 정책 지정
- ✅ default_section 자동 추출
- ✅ 공통 모듈 제외하고 완전 독립적

---

## ⚠️ 잠재적 문제점

### 1. **ConfigPolicy.loader_policy_path 처리 누락**
**문제:**
```python
class ConfigPolicy(BaseModel):
    loader_policy_path: Optional[Path] = Field(default=None)  # 필드는 추가됨
    
# 하지만 _load_loader_policy()에서 활용 안 됨!
def _load_loader_policy(self, policy: Optional[ConfigPolicy] = None):
    if policy is not None:
        return policy  # ← loader_policy_path를 확인하지 않음!
```

**현재 동작:**
```python
policy = ConfigPolicy(loader_policy_path=Path("custom_loader.yaml"))
loader = ConfigLoader("data.yaml", policy=policy)
# → custom_loader.yaml이 로드되지 않음! policy만 그대로 사용됨
```

**해결 방법:**
```python
def _load_loader_policy(self, policy: Optional[ConfigPolicy] = None) -> ConfigPolicy:
    # 1. policy.loader_policy_path가 있으면 그 파일에서 재로드
    if policy is not None and policy.loader_policy_path is not None:
        # loader_policy_path에서 정책 로드
        parser = YamlParser(policy=BaseParserPolicy(...))
        text = policy.loader_policy_path.read_text(encoding="utf-8")
        parsed = parser.parse(text, base_path=policy.loader_policy_path)
        
        if isinstance(parsed, dict) and "config_policy" in parsed:
            policy_dict = parsed["config_policy"]
            return ConfigPolicy(**policy_dict)
    
    # 2. policy만 있고 loader_policy_path 없으면 그대로 사용
    if policy is not None:
        return policy
    
    # 3. 기본 경로 시도...
```

---

### 2. **섹션 자동 추출 시 재귀 로딩 가능성**
**문제:**
```python
# image_ocr.py
loader_policy = ConfigPolicy(loader_policy_path=loader_config_path)  # ← 여기서 로드 안 됨!
section = loader_policy.yaml_policy.default_section  # ← 기본값 사용됨 (None)
```

**현재 동작:**
```python
# config_loader_ocr.yaml
config_policy:
  yaml_policy:
    default_section: "ocr"

# 하지만 ConfigPolicy(loader_policy_path=...)만 호출하면
# loader_policy_path 파일이 실제로 로드되지 않음!
```

---

### 3. **각 모듈에서 중복 로딩**
**문제:**
```python
# image_ocr.py, image_loader.py, translator.py 모두 동일한 패턴
if loader_config_path.exists():
    loader_policy = ConfigPolicy(loader_policy_path=loader_config_path)
    
loader = ConfigLoader(cfg_like, policy=loader_policy)

if loader_policy and section is None:
    section = loader_policy.yaml_policy.default_section
```

**비효율:**
- 각 모듈마다 동일한 로직 반복
- loader_policy_path 처리가 ConfigLoader 내부가 아닌 외부에서 수행

---

## 💡 권장 수정사항

### 수정 1: _load_loader_policy() 개선
```python
def _load_loader_policy(self, policy: Optional[ConfigPolicy] = None) -> ConfigPolicy:
    # 1. policy.loader_policy_path가 지정되어 있으면 그 파일 로드
    if policy is not None and policy.loader_policy_path is not None:
        loader_policy_path = Path(policy.loader_policy_path)
        if loader_policy_path.exists():
            parser = YamlParser(policy=BaseParserPolicy(...))
            text = loader_policy_path.read_text(encoding="utf-8")
            parsed = parser.parse(text, base_path=loader_policy_path)
            
            if isinstance(parsed, dict) and "config_policy" in parsed:
                policy_dict = parsed["config_policy"]
                return ConfigPolicy(**policy_dict)
    
    # 2. policy만 있으면 그대로 사용
    if policy is not None:
        return policy
    
    # 3. 기본 경로 시도 (cfg_utils/configs/config_loader.yaml)
    default_loader_policy_path = Path(__file__).parent.parent / "configs" / "config_loader.yaml"
    if default_loader_policy_path.exists():
        # ... 기존 로직
```

### 수정 2: 각 모듈 간소화
```python
# Before (복잡)
loader_config_path = Path(__file__).parent.parent / "configs" / "config_loader_ocr.yaml"
loader_policy = None
if loader_config_path.exists():
    loader_policy = ConfigPolicy(loader_policy_path=loader_config_path)

loader = ConfigLoader(cfg_like, policy=loader_policy)

if loader_policy and section is None:
    section = loader_policy.yaml_policy.default_section

# After (간결)
loader_config_path = Path(__file__).parent.parent / "configs" / "config_loader_ocr.yaml"
loader_policy = ConfigPolicy(loader_policy_path=loader_config_path) if loader_config_path.exists() else None

loader = ConfigLoader(cfg_like, policy=loader_policy)
section = loader.policy.yaml_policy.default_section  # ← ConfigLoader가 이미 로드함!
```

---

## ✅ 독립성 확인

### 공통 모듈 제외하고 완전 독립적인가?

**YES!** ✅

각 모듈은 다음만 의존:
1. **cfg_utils** (ConfigLoader, ConfigPolicy) - 공통 모듈
2. **logs_utils** (LogManager) - 공통 모듈  
3. **자신의 configs/ 디렉토리** - 완전 독립

**테스트 시나리오:**
```python
# image_utils만 독립적으로 테스트
from image_utils import ImageOCR

# configs/config_loader_ocr.yaml에서 자동 로드
# default_section="ocr" 자동 적용
ocr = ImageOCR("test_data.yaml")
result = ocr.run()

# translate_utils와 완전히 독립
# logs_utils, cfg_utils만 공통 의존
```

---

## 📋 수정 우선순위

1. **HIGH**: _load_loader_policy()에서 loader_policy_path 처리 추가
2. **MEDIUM**: 각 모듈 코드 간소화 (ConfigLoader가 section 자동 추출하도록)
3. **LOW**: 성능 최적화 (config_loader.yaml 캐싱 고려)

---

## 결론

**현재 상태:**
- ✅ 구조는 완벽 (각 모듈 독립성 확보)
- ⚠️ loader_policy_path 처리 누락 (기능 미완성)
- ⚠️ 각 모듈에서 중복 로직 (간소화 가능)

**다음 단계:**
1. _load_loader_policy() 수정
2. 각 모듈 코드 간소화
3. 테스트 작성 및 검증
