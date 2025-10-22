# Section Validation 구현 완료 보고서

## ✅ 구현 완료

### 수정 파일
- `modules/cfg_utils/services/source.py`
- `UnifiedSource._extract_yaml()` 메서드

### 구현 내용

#### 1. Section 검증 로직 추가

```python
if section:
    yaml_keys = list(data.keys())
    
    if section in data:
        # Case 1: Section이 YAML에 존재 → 추출
        data = {section: data[section]}
    
    else:
        # Case 2: Section이 YAML에 없음
        
        # Flat 구조 판단
        is_flat_structure = any(not isinstance(data[k], dict) for k in yaml_keys)
        
        if is_flat_structure:
            # Flat 구조 → Wrap
            data = {section: data}
        
        elif len(yaml_keys) == 1:
            # 최상위 키 1개 + 불일치 → Raise!
            yaml_top_key = yaml_keys[0]
            raise ValueError(
                f"Section mismatch in YAML file '{path.name}': "
                f"YAML top-level key is '{yaml_top_key}', "
                f"but section='{section}' was specified. "
                f"\n\nOptions to fix:"
                f"\n  1. Change YAML top-level key from '{yaml_top_key}' to '{section}'"
                f"\n  2. Change section parameter to '{yaml_top_key}'"
                f"\n  3. Use src=(path, '{yaml_top_key}') in ConfigLoader"
            )
        
        else:
            # 최상위 키 여러 개 + section 없음 → Raise!
            raise ValueError(
                f"Section '{section}' not found in YAML file '{path.name}'. "
                f"Available top-level keys: {yaml_keys}. "
                f"\n\nOptions to fix:"
                f"\n  1. Add '{section}:' section to YAML file"
                f"\n  2. Use one of the existing sections: {yaml_keys}"
            )
```

---

## 📊 테스트 결과

### ✅ Case 1: YAML 최상위 == Section
```yaml
image:
  max_width: 1024
```
**결과:** ✅ 정상 추출

---

### ✅ Case 2: YAML 최상위 != Section (1개 키)
```yaml
image_policy:          # ← "image"와 불일치
  max_width: 1024
```
```python
loader = ConfigLoader(src=("file.yaml", "image"))
# ValueError: Section mismatch in YAML file...
```
**결과:** ✅ ValueError Raise

---

### ✅ Case 3: YAML 최상위 여러 개 + Section 없음
```yaml
section1: {...}
section2: {...}        # ← "image" 없음
```
```python
loader = ConfigLoader(src=("file.yaml", "image"))
# ValueError: Section 'image' not found...
```
**결과:** ✅ ValueError Raise

---

### ✅ Case 4: YAML Flat 구조
```yaml
max_width: 1024        # ← Section 구조 아님
format: "JPEG"
```
```python
loader = ConfigLoader(src=("file.yaml", "image"))
# → {'image': {'max_width': 1024, 'format': 'JPEG'}}
```
**결과:** ✅ Wrap 성공

---

### ✅ Case 5: webdriver_china.yaml 실제 테스트
```python
# 올바른 사용
loader = ConfigLoader(src=("webdriver_china.yaml", "webdriver_china"))
# ✅ 성공

# 잘못된 사용
loader = ConfigLoader(src=("webdriver_china.yaml", "webdriver"))
# ✅ ValueError Raise
```

---

## 🎯 요구사항 달성도

| 요구사항 | 구현 전 | 구현 후 |
|---------|--------|--------|
| 1. 동일 구조 YAML 구분 | ⚠️ 중첩 발생 | ✅ 명확한 에러 메시지 |
| 2. 최상위 설정/미설정 | ⚠️ 부분 | ✅ 정상 |
| 3. 일치 시 추출 | ✅ 정상 | ✅ 정상 |
| 4. 불일치 시 Raise | ❌ **미구현** | ✅ **구현 완료** |
| 5. 모듈 기본값 | ⚠️ 부분 | ⚠️ 명시적 지정 필요 |

---

## 🔥 핵심 개선사항

### 1. 명확한 에러 메시지
**Before:**
```python
# 중첩만 발생, 에러 없음
# {'webdriver': {'webdriver_china': {...}}}
```

**After:**
```python
ValueError: Section mismatch in YAML file 'webdriver_china.yaml': 
YAML top-level key is 'webdriver_china', but section='webdriver' was specified.

Options to fix:
  1. Change YAML top-level key from 'webdriver_china' to 'webdriver'
  2. Change section parameter to 'webdriver_china'
  3. Use src=(path, 'webdriver_china') in ConfigLoader
```

---

### 2. Flat 구조 자동 감지
```python
# Flat 구조 판단 로직
is_flat_structure = any(not isinstance(data[k], dict) for k in yaml_keys)
```

**동작:**
- primitive 값이 하나라도 있으면 → Flat 구조
- 모든 값이 dict이면 → Section 구조

---

### 3. 실제 사용 시나리오 보호
```python
# webdriver_china.yaml
webdriver_china: {...}

# 잘못된 사용 (이제 차단됨!)
loader = ConfigLoader(src=("webdriver_china.yaml", "webdriver"))
# ❌ ValueError: Section mismatch!

# 올바른 사용
loader = ConfigLoader(src=("webdriver_china.yaml", "webdriver_china"))
# ✅ 정상
```

---

## 📝 사용 가이드

### ✅ 올바른 패턴

#### Pattern 1: YAML 최상위 키와 section 일치
```yaml
# webdriver_china.yaml
webdriver_china:
  region: "china"
```
```python
loader = ConfigLoader(src=("webdriver_china.yaml", "webdriver_china"))
config = loader.to_dict(section="webdriver_china")
```

#### Pattern 2: Flat 구조 + section으로 wrap
```yaml
# image_flat.yaml
max_width: 1024
format: "JPEG"
```
```python
loader = ConfigLoader(src=("image_flat.yaml", "image"))
config = loader.to_dict(section="image")
# → {'max_width': 1024, 'format': 'JPEG'}
```

---

### ❌ 잘못된 패턴 (이제 차단됨)

#### Anti-Pattern 1: Section 불일치
```yaml
# webdriver_china.yaml
webdriver_china: {...}
```
```python
# ❌ 잘못됨!
loader = ConfigLoader(src=("webdriver_china.yaml", "webdriver"))
# ValueError: Section mismatch!
```

#### Anti-Pattern 2: Section 없음
```yaml
# multi.yaml
section1: {...}
section2: {...}
```
```python
# ❌ 잘못됨!
loader = ConfigLoader(src=("multi.yaml", "image"))
# ValueError: Section 'image' not found!
```

---

## 🚀 다음 단계

### ConfigLikeLoader는 수정 불필요
- ✅ ConfigLikeLoader는 항상 section 지정
- ✅ Section validation은 UnifiedSource에서 자동 수행
- ✅ 기존 코드 변경 없이 즉시 적용됨

### 실제 적용 예시
```python
# ImageLoad에서 (코드 변경 없음!)
policy = ConfigLikeLoader.load_with_caller_path(
    cfg_like="image.yaml",
    policy_class=ImageLoadPolicy,
    caller_file=__file__,
    default_config_filename="image.yaml"
)
# → section="image" (자동 추출)
# → UnifiedSource에서 자동 검증!
```

---

## ✅ 최종 확인

**구현 완료:**
- ✅ Section mismatch 검증
- ✅ Section not found 검증
- ✅ Flat 구조 자동 감지
- ✅ 명확한 에러 메시지
- ✅ 실제 파일 테스트 통과

**영향 범위:**
- ✅ UnifiedSource만 수정
- ✅ ConfigLikeLoader 수정 불필요
- ✅ 기존 코드 호환성 유지
- ✅ 잘못된 사용만 차단

**테스트 결과:**
- ✅ 모든 Case 통과
- ✅ webdriver_china.yaml 실제 테스트 성공
- ✅ 에러 메시지 명확성 확인

---

## 🎉 구현 완료!

**요구사항 4번 "불일치 시 Raise" 구현 완료!** ✅
