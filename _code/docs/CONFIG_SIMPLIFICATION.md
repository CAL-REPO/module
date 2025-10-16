# Config System Simplification Report

날짜: 2025-10-16  
작업자: GitHub Copilot

## 📋 작업 요약

env_loader.py에서 발생한 문제를 해결하는 과정에서 추가된 불필요한 복잡성을 제거하고 시스템을 간소화했습니다.

---

## 🔄 제거된 기능

### 1. **Phase 2: YamlParser context 전달** ❌

#### Before:
```python
# ConfigLoader.__init__()
placeholder_context = self._load_placeholder_context()
self.parser = YamlParser(
    policy=self.policy.yaml,
    context=placeholder_context  # ← 불필요한 context 전달
)
```

#### After:
```python
# ConfigLoader.__init__()
self.parser = YamlParser(policy=self.policy.yaml)
```

**제거 이유**: 
- env_loader에서 이미 ReferenceResolver로 모든 placeholder를 치환함
- YamlParser가 context를 받아도 사용하지 않음 (enable_placeholder=False)
- 불필요한 의존성 추가

---

### 2. **BaseParserPolicy.placeholder_source 필드** ❌

#### Before:
```python
class BaseParserPolicy(BaseModel):
    placeholder_source: Optional[Union[str, Path, Dict[str, Any]]] = Field(
        default=None,
        description="Placeholder 해석에 사용할 소스"
    )
```

#### After:
```python
# 필드 제거
```

**제거 이유**:
- ConfigLoader 내부에서만 사용하는 임시 필드
- BaseParserPolicy는 범용 정책이므로 특수 목적 필드 부적합
- `reference_context` (policy_overrides)로 대체

---

### 3. **ConfigLoader._load_placeholder_context()** ❌

#### Before:
```python
def _load_placeholder_context(self) -> Optional[Dict[str, Any]]:
    """policy.yaml.placeholder_source를 처리하여 dict 반환."""
    placeholder_source = self.policy.yaml.placeholder_source
    # ... 50줄의 복잡한 로직
```

#### After:
```python
# 메서드 제거
```

**제거 이유**:
- env_loader에서 paths.local.yaml을 이미 로드함
- 순환 의존성 가능성 (ConfigLoader가 다시 YAML 파싱)
- policy_overrides의 `reference_context`로 대체

---

### 4. **_merge_from_path의 PlaceholderResolver** ❌

#### Before:
```python
def _merge_from_path(self, path: PathLike, ...):
    path_str = str(path)
    
    if "${" in path_str and self.parser.context:
        # PlaceholderResolver를 사용하여 경로 해석
        from unify_utils.normalizers.resolver_placeholder import PlaceholderResolver
        resolver = PlaceholderResolver(context=self.parser.context)
        path_str = resolver.apply(path_str)
    
    path_obj = Path(path_str)
```

#### After:
```python
def _merge_from_path(self, path: PathLike, ...):
    path_obj = Path(str(path))
```

**제거 이유**:
- env_loader에서 이미 모든 경로를 해석함
- `${configs_dir}` 등은 ReferenceResolver로 치환 완료
- 중복 처리

---

## ✅ 유지된 핵심 로직

### **ConfigLoader._load_loader_policy() - ReferenceResolver 적용**

```python
# policy_overrides에서 reference_context(paths_dict)를 context로 사용
context = {}
if policy_overrides and "reference_context" in policy_overrides:
    reference_ctx = policy_overrides["reference_context"]
    if isinstance(reference_ctx, dict):
        context = reference_ctx

# context가 있으면 ReferenceResolver 적용
if context:
    resolver = ReferenceResolver(context, recursive=True, strict=False)
    config_section = resolver.apply(config_section)

policy_state.merge(config_section, deep=True)
```

**유지 이유**:
- config_loader.yaml의 `${configs_dir}` 등을 치환하는 핵심 로직
- env_loader에서 전달한 paths_dict를 활용
- 이 로직이 없으면 source_paths가 빈 문자열로 변환됨

---

## 🎯 키 이름 변경

### `yaml.placeholder_source` → `reference_context`

#### Before:
```python
# env_loader.py
final_overrides["yaml.placeholder_source"] = paths_dict

# config_loader.py
if policy_overrides and "yaml.placeholder_source" in policy_overrides:
    placeholder_src = policy_overrides["yaml.placeholder_source"]
```

#### After:
```python
# env_loader.py
final_overrides["reference_context"] = paths_dict

# config_loader.py
if policy_overrides and "reference_context" in policy_overrides:
    reference_ctx = policy_overrides["reference_context"]
```

**변경 이유**:
1. **명확성**: BaseParserPolicy의 placeholder_source와 혼동 방지
2. **용도**: ReferenceResolver의 context로 사용됨을 명시
3. **범위**: policy_overrides 전용 (BasePolicy 필드 아님)

---

## 📊 간소화 결과

| 항목 | Before | After | 변화 |
|------|--------|-------|------|
| ConfigLoader.__init__ 라인 수 | 26줄 | 17줄 | **-9줄** |
| _load_placeholder_context 메서드 | 50줄 | 제거 | **-50줄** |
| BaseParserPolicy 필드 | +1 (placeholder_source) | 제거 | **-8줄** |
| _merge_from_path 라인 수 | 24줄 | 13줄 | **-11줄** |
| **총 감소** | - | - | **-78줄** |

---

## 🧪 테스트 결과

### 테스트 명령:
```powershell
python -c "from script_utils import EnvBasedConfigInitializer; \
paths = EnvBasedConfigInitializer.load_paths_from_env(); \
loader = EnvBasedConfigInitializer.create_config_loader('configs_loader_file_oto', paths); \
print('Source paths:', loader.policy.yaml.source_paths)"
```

### 결과:
```
✅ Paths loaded
✅ ConfigLoader created
Source paths: [
  SourcePathConfig(path='M:/CALife/CAShop - 구매대행/_code/configs/oto/image.yaml', section='image'),
  SourcePathConfig(path='M:/CALife/CAShop - 구매대행/_code/configs/oto/ocr.yaml', section='ocr'),
  SourcePathConfig(path='M:/CALife/CAShop - 구매대행/_code/configs/oto/overlay.yaml', section='overlay'),
  SourcePathConfig(path='M:/CALife/CAShop - 구매대행/_code/configs/oto/translate.yaml', section='translate')
]
```

**✅ 모든 placeholder 정상 해석됨**

---

## 🔍 code_dir → base_path 통일 확인

### paths.local.yaml:
```yaml
# Before (일부):
code_dir: "${root}/_code"
scripts_dir: "${code_dir}/scripts"

# After (통일):
base_path: "M:/CALife/CAShop - 구매대행/_code"
scripts_dir: "${base_path}/scripts"
```

**변경 사항**:
- `code_dir` 키 제거
- 모든 참조를 `base_path`로 통일
- nested reference 단계 감소 (3단계 → 2단계)

---

## 📝 최종 아키텍처

```mermaid
graph TD
    A[ENV: CASHOP_PATHS] --> B[paths.local.yaml]
    B --> C[EnvBasedConfigInitializer.load_paths_from_env]
    C --> D[ReferenceResolver - nested 치환]
    D --> E[paths_dict]
    E --> F[EnvBasedConfigInitializer.create_config_loader]
    F --> G[policy_overrides: reference_context]
    G --> H[ConfigLoader.__init__]
    H --> I[_load_loader_policy]
    I --> J[config_loader_oto.yaml 파싱]
    J --> K[ReferenceResolver.apply - ${configs_dir} 치환]
    K --> L[ConfigPolicy.yaml.source_paths]
    L --> M[정상 경로]
```

---

## 🎓 교훈

1. **문제의 근본 원인을 먼저 해결하라**
   - env_loader의 문제를 다른 곳에서 우회하려다 복잡성 증가
   - 순환 의존성은 설계 수준에서 제거해야 함

2. **범용 정책에 특수 필드를 추가하지 마라**
   - BaseParserPolicy는 YAML/JSON 공용 정책
   - 특수 목적(ConfigLoader 전용)은 policy_overrides 활용

3. **중복 처리를 경계하라**
   - PlaceholderResolver + ReferenceResolver 동시 사용
   - env_loader + ConfigLoader 양쪽에서 placeholder 처리
   - 한 곳에서 한 번만 처리하도록 설계

4. **테스트로 검증하라**
   - 리팩토링 후 즉시 테스트
   - 78줄 제거해도 기능은 그대로 유지

---

## 🚀 다음 단계

1. ✅ **간소화 완료**: 불필요한 코드 제거
2. ⏭️ **OTO 파이프라인 테스트**: 실제 이미지 처리 테스트
3. ⏭️ **문서화**: env_loader 사용 가이드 작성
4. ⏭️ **다른 스크립트 적용**: xlcrawl.py 등에도 env_loader 적용

---

## 📚 관련 문서

- [CFG_UTILS_FINAL_REPORT.md](./CFG_UTILS_FINAL_REPORT.md)
- [XLOTO_IMPROVEMENTS.md](./XLOTO_IMPROVEMENTS.md)
- [STRUCTURED_DATA_UNIFIED.md](./STRUCTURED_DATA_UNIFIED.md)
