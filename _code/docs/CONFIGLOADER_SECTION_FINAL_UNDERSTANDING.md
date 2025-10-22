# ConfigLoader Section 동작 - 최종 이해 확인

## 📋 요구사항 정리

### ConfigLoader의 source에 section 값이 없을 경우

#### Case 1: YAML 최상위 키가 존재하는 경우

**1-1) 최상위 키 != 기본 section명 (불일치)**
```yaml
# image.yaml
image_policy:           # ← 최상위 키 존재
  max_width: 1024
```

```python
# ConfigLoader에서 section 미지정
loader = ConfigLoader(src="image.yaml")  # ← section 없음
# default_config_filename = "image.yaml"
# → 기본 section명: "image" (파일명에서 추출)

# 검증:
# YAML 최상위: "image_policy"
# 기본 section: "image"
# → 불일치! → Raise!
```

**동작:** ❌ **ValueError Raise**
```python
raise ValueError(
    f"Section mismatch: "
    f"YAML top-level key is 'image_policy', "
    f"but expected section='image' (from default_config_filename). "
    f"Please rename YAML key to 'image' or specify section explicitly."
)
```

---

**1-2) 최상위 키가 여러 개 존재하는 경우**
```yaml
# multi.yaml
section1:
  key: value1
section2:
  key: value2
```

```python
loader = ConfigLoader(src="multi.yaml")  # ← section 없음
# default_config_filename = "image.yaml"
# → 기본 section명: "image"

# 검증:
# YAML 최상위: ["section1", "section2"]  (여러 개)
# 기본 section: "image"
# → "image" 키가 YAML에 없음! → Raise!
```

**동작:** ❌ **ValueError Raise**
```python
raise ValueError(
    f"Section 'image' not found in YAML. "
    f"Available sections: {list(yaml_keys)}. "
    f"Specify section explicitly in ConfigLoader."
)
```

---

#### Case 2: YAML 최상위 키가 존재하지 않는 경우 (Flat 구조)

```yaml
# image_flat.yaml (최상위 Section 없음!)
max_width: 1024         # ← 바로 최상위
max_height: 768
format: "JPEG"
```

```python
loader = ConfigLoader(src="image_flat.yaml")  # ← section 없음
# default_config_filename = "image.yaml"
# → 기본 section명: "image"

# 검증:
# YAML 구조: flat (최상위 Section 없음)
# 기본 section: "image"
# → Wrap 필요! → {'image': {...}}
```

**동작:** ✅ **Wrap**
```python
# 파싱 후:
# {'max_width': 1024, 'max_height': 768, 'format': 'JPEG'}

# section="image"로 wrap:
# {'image': {'max_width': 1024, 'max_height': 768, 'format': 'JPEG'}}

config = loader.to_dict(section="image")
# → {'max_width': 1024, 'max_height': 768, 'format': 'JPEG'}
```

---

## 🎯 동작 시나리오 정리

| YAML 구조 | 최상위 키 | 기본 section | 결과 |
|-----------|----------|-------------|------|
| `image: {...}` | `image` | `image` | ✅ 일치 → 정상 추출 |
| `image_policy: {...}` | `image_policy` | `image` | ❌ 불일치 → Raise |
| `section1: {...}`<br>`section2: {...}` | 여러 개 | `image` | ❌ `image` 없음 → Raise |
| `max_width: 1024`<br>`format: "JPEG"` | 없음 (flat) | `image` | ✅ Wrap → `{'image': {...}}` |

---

## 🔍 구분 방법: 최상위 키 존재 여부

### 최상위 키가 존재하는 경우
```python
yaml_keys = list(data.keys())
# ['image'], ['image_policy'], ['section1', 'section2'] 등

# 모든 키가 dict 값을 가지면 → Section 구조
if all(isinstance(data[k], dict) for k in yaml_keys):
    # Case 1: 최상위 키 존재
    ...
```

### 최상위 키가 없는 경우 (Flat)
```python
yaml_keys = list(data.keys())
# ['max_width', 'format', 'quality'] 등

# 일부 키가 primitive 값이면 → Flat 구조
if any(not isinstance(data[k], dict) for k in yaml_keys):
    # Case 2: Flat 구조
    ...
```

---

## 💻 구현 로직

```python
def _extract_yaml(self) -> KeyPathDict:
    # YAML 파싱
    data = parser.parse(text)
    
    # Section 처리
    if section:
        # section이 명시적으로 지정된 경우
        if section in data:
            data = {section: data[section]}
        elif len(data.keys()) == 1:
            yaml_key = list(data.keys())[0]
            if yaml_key != section:
                raise ValueError(f"Section mismatch: YAML='{yaml_key}', expected='{section}'")
        else:
            # 여러 키 또는 flat → wrap
            data = {section: data}
    else:
        # section 미지정 → 기본 section 사용
        default_section = _extract_section_from_filename(default_config_filename)
        # default_section = "image" (from "image.yaml")
        
        yaml_keys = list(data.keys())
        
        # Case 1: 최상위 키 존재 (Section 구조)
        if all(isinstance(data[k], dict) for k in yaml_keys):
            if default_section in data:
                # 일치
                data = {default_section: data[default_section]}
            elif len(yaml_keys) == 1:
                yaml_key = yaml_keys[0]
                # 불일치
                raise ValueError(
                    f"Section mismatch: "
                    f"YAML top-level key is '{yaml_key}', "
                    f"but expected '{default_section}' (from {default_config_filename}). "
                    f"Rename YAML key or specify section explicitly."
                )
            else:
                # 여러 키
                raise ValueError(
                    f"Section '{default_section}' not found in YAML. "
                    f"Available: {yaml_keys}. "
                    f"Specify section explicitly."
                )
        
        # Case 2: Flat 구조 (최상위 키 없음)
        else:
            # Wrap
            data = {default_section: data}
    
    return KeyPathDict(data=data)
```

---

## ✅ 이해 확인

### 1. 최상위 키 존재 + 불일치
```yaml
# image.yaml
image_policy: {...}     # ← "image"와 불일치
```
**동작:** ❌ Raise

### 2. 최상위 키 존재 + 없음
```yaml
# image.yaml
section1: {...}
section2: {...}         # ← "image" 키 없음
```
**동작:** ❌ Raise

### 3. 최상위 키 없음 (Flat)
```yaml
# image.yaml
max_width: 1024         # ← Section 구조 아님
format: "JPEG"
```
**동작:** ✅ Wrap → `{'image': {...}}`

---

## 🎯 최종 확인

**이해한 내용:**
1. ✅ ConfigLoader source에 section 없을 때 → default_config_filename에서 추출
2. ✅ 최상위 키 존재 + 불일치 → Raise
3. ✅ 최상위 키 존재 + 없음 → Raise
4. ✅ 최상위 키 없음 (Flat) → default section으로 Wrap

**올바르게 이해했습니까?** 🙋‍♂️
