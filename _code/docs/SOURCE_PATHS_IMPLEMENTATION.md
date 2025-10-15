# Section 이름 변경 및 source_paths 기능 추가 완료

**일시**: 2025년 10월 15일
**작업**: ConfigLoader 섹션명 변경 + source_paths 자동 로드 구현

---

## 1. 변경 사항

### 1.1. 섹션명 변경
- ✅ `config_policy` → `config_loader` (ConfigLoader 기본 섹션)
- ✅ `yaml_policy` → `yaml` (yaml 파싱 정책 섹션)

### 1.2. 필드명 변경
- ✅ `file_path` → `source_paths` (단일 또는 리스트 지원)

### 1.3. 자동 로드 기능 추가
- ✅ `yaml.source_paths`가 지정되어 있으면 자동 병합

---

## 2. 수정된 파일

### 2.1. 코어 파일
1. **structured_io/core/base_policy.py**
   ```python
   source_paths: Optional[Union[str, Path, List[Union[str, Path]]]]
   ```

2. **cfg_utils/core/policy.py**
   ```python
   yaml: BaseParserPolicy = Field(..., alias="yaml_policy")  # 하위 호환성
   ```

3. **cfg_utils/services/config_loader.py**
   - `policy.yaml_policy` → `policy.yaml`
   - `source_paths` 자동 로드 로직 추가
   - `config_loader` 섹션 인식 (하위 호환성: `config_policy`도 지원)

### 2.2. YAML 파일 (9개)
- `cfg_utils/configs/config_loader.yaml`
- `image_utils/configs/config_loader_image.yaml`
- `image_utils/configs/config_loader_ocr.yaml`
- `image_utils/configs/config_loader_overlay.yaml`
- `crawl_utils/configs/config_loader_firefox.yaml`
- `translate_utils/configs/config_loader.yaml`
- `logs_utils/configs/config_loader.yaml`
- `xl_utils/configs/config_loader.yaml`

모두 `config_policy` → `config_loader`, `yaml_policy` → `yaml`, `file_path` → `source_paths`로 변경

---

## 3. 사용 예시

### 3.1. 기본 사용 (source_paths 없음)
```yaml
# config_loader.yaml
config_loader:
  yaml:
    source_paths: null
    default_section: "image"
```

```python
loader = ImageLoader()
# → config_loader.yaml 읽음
# → source_paths가 null이므로 cfg_like만 처리
```

### 3.2. source_paths 단일 파일
```yaml
# config_loader.yaml
config_loader:
  yaml:
    source_paths: "configs/base.yaml"
    default_section: "image"
```

```python
loader = ImageLoader()
# → config_loader.yaml 읽음
# → source_paths에서 base.yaml 자동 로드
```

### 3.3. source_paths 여러 파일 (핵심!)
```yaml
# config_loader.yaml
config_loader:
  yaml:
    source_paths:
      - "configs/base.yaml"
      - "configs/image_specific.yaml"
    default_section: "image"
```

```python
loader = ImageLoader()
# → config_loader.yaml 읽음
# → source_paths의 파일들을 순서대로 병합
# → base.yaml + image_specific.yaml (deep merge)
```

### 3.4. source_paths + cfg_like 조합
```yaml
# config_loader.yaml
config_loader:
  yaml:
    source_paths:
      - "configs/base.yaml"
      - "configs/image.yaml"
```

```python
loader = ImageLoader("custom.yaml")
# 병합 순서:
# 1. base.yaml (source_paths[0])
# 2. image.yaml (source_paths[1])
# 3. custom.yaml (cfg_like)
# → 순서대로 deep merge
```

### 3.5. 런타임 오버라이드
```python
loader = ImageLoader(
    "custom.yaml",
    resize_to=(800, 600)
)
# 병합 순서:
# 1. source_paths (있으면)
# 2. custom.yaml
# 3. resize_to=(800, 600) (최종 오버라이드)
```

---

## 4. 우선순위 체계

```
런타임 Argument (**overrides) - 최고 우선순위
    ↓
cfg_like (ConfigLoader.load() 첫 번째 인자)
    ↓
yaml.source_paths[n] (마지막 파일)
    ↓
yaml.source_paths[...]
    ↓
yaml.source_paths[0] (첫 번째 파일)
    ↓
Pydantic Model 기본값 - 최저 우선순위
```

---

## 5. 장점

### 5.1. 설정 파일 재사용
```yaml
# base.yaml - 공통 설정
image:
  save_copy: true
  quality: 95

# image_specific.yaml - 모듈별 설정
image:
  directory: "output/images"
  resize_to: [800, 600]
```

```yaml
# image_loader의 config_loader.yaml
config_loader:
  yaml:
    source_paths:
      - "configs/base.yaml"
      - "configs/image_specific.yaml"
```

```yaml
# ocr의 config_loader.yaml
config_loader:
  yaml:
    source_paths:
      - "configs/base.yaml"
      - "configs/ocr_specific.yaml"
```

### 5.2. 환경별 설정
```yaml
config_loader:
  yaml:
    source_paths:
      - "configs/base.yaml"
      - "configs/env/production.yaml"
```

### 5.3. 모듈 간 설정 공유
```yaml
# image_loader의 config_loader.yaml
config_loader:
  yaml:
    source_paths:
      - "../../common/base.yaml"  # 공통 설정
      - "configs/image.yaml"      # 이미지 전용
```

---

## 6. 하위 호환성

### 6.1. 필드명 alias
```python
# ConfigPolicy
yaml: BaseParserPolicy = Field(..., alias="yaml_policy")
```

```yaml
# 둘 다 동작
config_loader:
  yaml: ...

# 또는 (하위 호환성)
config_loader:
  yaml_policy: ...
```

### 6.2. 섹션명 fallback
```python
# ConfigLoader._load_loader_policy()
if "config_loader" in parsed:
    policy_dict = parsed["config_loader"]
elif "config_policy" in parsed:  # 하위 호환성
    policy_dict = parsed["config_policy"]
```

---

## 7. 테스트 필요

```python
# 1. source_paths 단일 파일
# 2. source_paths 여러 파일
# 3. source_paths + cfg_like
# 4. source_paths + overrides
# 5. 하위 호환성 (yaml_policy, config_policy)
```

---

## 8. 결론

**완료된 작업:**
- ✅ 섹션명 변경: `config_policy` → `config_loader`, `yaml_policy` → `yaml`
- ✅ 필드명 변경: `file_path` → `source_paths`
- ✅ source_paths 자동 로드 구현
- ✅ 9개 YAML 파일 수정
- ✅ 하위 호환성 유지

**효과:**
- 다른 모듈에서 config_loader의 yaml 정책 재사용 가능
- 설정 파일 병합으로 유연한 구성
- 환경별 설정 관리 간편화

---

**작성자**: GitHub Copilot  
**날짜**: 2025년 10월 15일  
**버전**: ConfigLoader v2.2 (source_paths 지원)
