# ConfigLikeLoader 역할 분석

## 🎯 ConfigLikeLoader의 역할

### 핵심 목적
**모든 모듈의 EntryPoint에서 반복되는 cfg_like 로드 로직을 통합**

---

## 📋 주요 기능

### 1. 다양한 cfg_like 소스 처리

```python
# 1) Policy 인스턴스 직접 전달
policy = LogPolicy(...)
manager = LogManager(cfg_like=policy)

# 2) YAML 파일 경로
manager = LogManager(cfg_like="configs/log.yaml")

# 3) 딕셔너리
manager = LogManager(cfg_like={"enabled": True, "level": "INFO"})

# 4) None → 기본 설정 파일 사용
manager = LogManager(cfg_like=None)  # → logs_utils/configs/log.yaml
```

---

### 2. 기본 설정 파일 자동 경로 계산

```python
# load_with_caller_path() 메서드
policy = ConfigLikeLoader.load_with_caller_path(
    cfg_like=None,
    policy_class=LogPolicy,
    caller_file=__file__,              # manager.py의 __file__
    default_config_filename="log.yaml"
)

# 자동 계산:
# Path(__file__).parent.parent / "configs" / "log.yaml"
# → logs_utils/configs/log.yaml
```

---

### 3. Section 이름 자동 추출

```python
# Policy 클래스에서 name 필드 추출
section_name = policy_class().name

# 예시:
# LogPolicy().name = "log"
# ImageLoadPolicy().name = "image"
# WebDriverPolicy().name = "webdriver"
```

---

### 4. ConfigLoader 위임

```python
# ConfigLikeLoader는 ConfigLoader를 사용
loader = ConfigLoader(src=(cfg_like, section_name))
```

**중요:** 
- ConfigLikeLoader는 **항상 section을 지정**합니다!
- `src=(cfg_like, section_name)` 형식 사용

---

## 🔍 현재 Section 처리 방식

### ConfigLikeLoader의 동작

```python
# 1. Policy에서 section 추출
section_name = policy_class().name
# ImageLoadPolicy().name = "image"

# 2. ConfigLoader에 section 지정
src = (cfg_like, section_name)
loader = ConfigLoader(src=src)

# 3. Policy로 변환
return loader.to_model(policy_class, section=section_name)
```

### 예제: ImageLoad

```python
class ImageLoad:
    def _load_config(self, cfg_like, **overrides):
        return ConfigLikeLoader.load_with_caller_path(
            cfg_like=cfg_like,
            policy_class=ImageLoadPolicy,
            caller_file=__file__,
            default_config_filename="image.yaml"
        )
```

**동작 흐름:**
1. `cfg_like=None` → `image_utils/configs/image.yaml`
2. `section_name = "image"` (ImageLoadPolicy().name)
3. `src=("image_utils/configs/image.yaml", "image")`
4. ConfigLoader로 로드

---

## 🔥 현재 구조와 요구사항의 관계

### 현재 ConfigLikeLoader의 전제

**ConfigLikeLoader는 항상 section을 명시합니다:**
```python
src = (cfg_like, section_name)  # section_name은 항상 존재!
```

**이는 다음을 의미합니다:**

#### Case 1: YAML에 최상위 키가 있고 일치하는 경우
```yaml
# image.yaml
image:                  # ← section_name과 일치
  max_width: 1024
```
✅ **정상 동작**

#### Case 2: YAML에 최상위 키가 있고 불일치하는 경우
```yaml
# image.yaml
image_policy:           # ← section_name("image")과 불일치!
  max_width: 1024
```
❌ **현재: 중첩 발생** → `{'image': {'image_policy': {...}}}`
⚠️ **요구: Raise**

#### Case 3: YAML이 Flat 구조인 경우
```yaml
# image.yaml
max_width: 1024         # ← 최상위 키 없음 (Flat)
format: "JPEG"
```
✅ **현재: Wrap** → `{'image': {...}}`
✅ **요구: Wrap** (동일)

---

## 🎯 ConfigLikeLoader와 Section Validation

### ConfigLikeLoader는 영향을 받지 않습니다!

**이유:**
- ConfigLikeLoader는 **항상 section을 지정**합니다
- Section validation은 **ConfigLoader/UnifiedSource** 레벨에서 처리
- ConfigLikeLoader는 단순히 ConfigLoader를 호출하는 래퍼

**검증 흐름:**
```
ConfigLikeLoader.load_with_caller_path()
  ↓ section_name 추출 (Policy.name)
  ↓ src=(cfg_like, section_name) 생성
  ↓
ConfigLoader(src=src)
  ↓
UnifiedSource._extract_yaml()
  ↓ YAML 파싱
  ↓ Section 검증 ← 🔥 여기서 검증!
  ↓ 일치: 추출
  ↓ 불일치: Raise
  ↓ Flat: Wrap
  ↓
Policy 반환
```

---

## 📊 요약

| 컴포넌트 | 역할 | Section 처리 |
|---------|------|-------------|
| **ConfigLikeLoader** | cfg_like 소스 통합 처리 | Policy.name을 section으로 추출 |
| **ConfigLoader** | YAML/dict/BaseModel 로드 | src에서 section 파싱 |
| **UnifiedSource** | 실제 YAML 처리 및 검증 | Section validation 수행 |

---

## ✅ 결론

### ConfigLikeLoader의 역할
1. ✅ 모든 모듈의 cfg_like 로드 패턴 통합
2. ✅ Policy 인스턴스/YAML/dict/None 처리
3. ✅ 기본 설정 파일 경로 자동 계산
4. ✅ Policy.name을 section으로 자동 추출
5. ✅ ConfigLoader에 위임 (래퍼 역할)

### Section Validation과의 관계
- ✅ ConfigLikeLoader는 **항상 section 지정**
- ✅ Section validation은 **UnifiedSource**에서 수행
- ✅ ConfigLikeLoader 코드 수정 **불필요**

### 구현 필요 위치
- ❌ ConfigLikeLoader (수정 불필요)
- ✅ **UnifiedSource._extract_yaml()** (여기만 수정!)

---

## 🚀 다음 단계

**Section Validation 구현:**
- 파일: `modules/cfg_utils/services/source.py`
- 메서드: `UnifiedSource._extract_yaml()`
- 내용: YAML 최상위 키 검증 로직 추가

**ConfigLikeLoader는 그대로 사용 가능!**
