# Translator 설계 원칙 및 사용 가이드

## 핵심 설계 철학

### ✅ Override 패턴으로 모든 것을 해결

`Translator`는 **Config + Runtime Override** 패턴을 따릅니다.
- `translate_text()` 같은 별도 메서드는 **불필요**
- `run()` 메서드만으로 모든 시나리오 처리 가능

```python
# ❌ 나쁜 설계 (translate_text 메서드 추가)
class Translator:
    def run(self) -> Dict[str, str]:
        """Config 기반 번역"""
        ...
    
    def translate_text(self, text: str) -> str:
        """동적 텍스트 번역 (중복!)"""
        ...

# ✅ 좋은 설계 (Override로 모든 것 해결)
class Translator:
    def run(self) -> Dict[str, str]:
        """Config + Override 패턴"""
        ...
```

## 사용 패턴

### 1. Config 파일 기반 (기본)

```python
from translate_utils import Translator

# YAML에 source.text 정의
translator = Translator("config/translate.yaml")
result = translator.run()
print(result)  # {"Hello": "안녕하세요", ...}
```

### 2. Runtime Override (동적 텍스트)

```python
# Config는 유지하되, 텍스트만 동적으로 주입
translator = Translator(
    "config/translate.yaml",
    source__text=["你好", "谢谢", "再见"]  # Override
)
result = translator.run()
print(result)  # {"你好": "안녕하세요", "谢谢": "감사합니다", ...}
```

### 3. Dict Config (간단한 사용)

```python
translator = Translator({
    "source": {"text": ["Hello", "World"]},
    "provider": {
        "provider": "deepl",
        "source_lang": "EN",
        "target_lang": "KO"
    }
})
result = translator.run()
```

### 4. Multiple Override (복합)

```python
# Provider도 변경하고 텍스트도 주입
translator = Translator(
    "config/translate.yaml",
    source__text=["Hello"],
    provider__provider="google",
    provider__target_lang="JA"
)
result = translator.run()
print(result)  # {"Hello": "こんにちは"}
```

## xloto.py 적용 예시

### ❌ 잘못된 방법 (translate_text 사용)

```python
class ImageOTOProcessor:
    def __init__(self, xloto_cfg_path):
        # 인스턴스 재사용 의도
        self.translator = Translator(xloto_cfg_path)
    
    def process_image(self, image_path):
        ocr_texts = ["你好", "谢谢"]
        
        # translate_text() 메서드 필요 (나쁜 설계)
        translated = self.translator.translate_text(ocr_texts)
```

**문제점:**
- `translate_text()` 메서드 추가 → SRP 위반
- `Translator` 인스턴스 재사용 시 config 고정 → 유연성 감소

### ✅ 올바른 방법 (Override 패턴)

```python
class ImageOTOProcessor:
    def __init__(self, xloto_cfg_path):
        # Config 경로만 저장
        self.xloto_cfg_path = xloto_cfg_path
    
    def process_image(self, image_path):
        ocr_texts = ["你好", "谢谢"]
        
        # 매번 새 인스턴스 생성 + source override
        translator = Translator(
            self.xloto_cfg_path,
            section="translate",
            source__text=ocr_texts  # 동적 주입
        )
        result = translator.run()
        
        # Dict → List 변환
        translated = [result.get(text, text) for text in ocr_texts]
```

**장점:**
1. ✅ **캐시 공유**: 같은 `db_dir`을 사용하면 인스턴스가 달라도 캐시 공유
2. ✅ **설계 일관성**: 다른 모듈(ImageLoader, FirefoxWebDriver)과 동일한 패턴
3. ✅ **유연성**: 필요 시 provider, target_lang 등도 override 가능

## Cache 동작 원리

### Cache는 인스턴스가 달라도 공유됨!

```yaml
# xloto.yaml
translate:
  store:
    save_db: true
    db_dir: "${db_dir}"  # M:\CALife\CAShop - 구매대행\_code\data\db
    db_name: "translate_cache.sqlite3"
```

```python
# 인스턴스 1
translator1 = Translator("xloto.yaml", section="translate", source__text=["你好"])
result1 = translator1.run()  # API 호출, Cache 저장

# 인스턴스 2 (다른 인스턴스지만 같은 DB 사용)
translator2 = Translator("xloto.yaml", section="translate", source__text=["你好"])
result2 = translator2.run()  # Cache Hit! API 호출 안 함
```

**결론:**
- 매번 새 인스턴스 생성해도 괜찮음
- Cache DB가 공유되므로 성능 문제 없음

## 성능 비교

### 시나리오: 100개 이미지, 이미지당 OCR 텍스트 10개

| 방식 | Translator 생성 | API 호출 | Cache 활용 | 성능 |
|------|----------------|----------|-----------|------|
| **❌ translate_text() 메서드** | 1회 | 1000회 | ⚠️ 복잡 | 느림 |
| **✅ Override 패턴** | 100회 | 1000회 → 100회 (Cache) | ✅ 자동 | 빠름 |

**Override 패턴 성능:**
- 첫 실행: 1000회 API 호출
- 두 번째 실행: 0회 API 호출 (Cache Hit)
- Translator 생성 오버헤드: 무시할 수 있는 수준 (< 1ms)

## 다른 모듈과의 일관성

### ImageLoader 패턴

```python
# Config 기반
loader = ImageLoader("config.yaml")
result = loader.run()

# Override
loader = ImageLoader("config.yaml", source__path="image.jpg")
result = loader.run()
```

### FirefoxWebDriver 패턴

```python
# Config 기반
driver = FirefoxWebDriver("config.yaml")
driver.run()

# Override
driver = FirefoxWebDriver("config.yaml", headless=True)
driver.run()
```

### Translator 패턴 (동일!)

```python
# Config 기반
translator = Translator("config.yaml")
result = translator.run()

# Override
translator = Translator("config.yaml", source__text=["Hello"])
result = translator.run()
```

## 결론

### 설계 원칙

1. **단일 진입점**: `run()` 메서드만 제공
2. **Override 패턴**: Runtime에 모든 설정 변경 가능
3. **모듈 일관성**: 모든 서비스 클래스가 동일한 패턴 사용
4. **캐시 공유**: 인스턴스가 달라도 DB 공유로 성능 확보

### 금지 사항

- ❌ `translate_text()` 같은 별도 메서드 추가
- ❌ 인스턴스를 억지로 재사용하려는 시도
- ❌ Config와 Runtime API를 섞어서 사용

### 권장 사항

- ✅ Override 패턴으로 동적 처리
- ✅ Cache 설정으로 성능 확보
- ✅ 간단한 경우 Dict Config 사용
- ✅ 복잡한 경우 YAML + Override 조합

## 추가 예시

### OCR 결과 번역 (xloto.py)

```python
def process_image(self, image_path: Path) -> bool:
    # 1. OCR
    ocr_result = self.ocr.run(source_override=str(image_path))
    ocr_texts = [item.text for item in ocr_result['ocr_items']]
    
    # 2. 번역 (Override 패턴)
    translator = Translator(
        self.xloto_cfg_path,
        section="translate",
        source__text=ocr_texts  # 동적 주입
    )
    translation_dict = translator.run()
    
    # 3. 결과 변환
    translated = [translation_dict.get(text, text) for text in ocr_texts]
    
    # 4. Overlay
    # ...
```

### 언어별 번역

```python
# 중국어 → 한국어
translator_ko = Translator(
    "config.yaml",
    source__text=["你好"],
    provider__target_lang="KO"
)
result_ko = translator_ko.run()  # {"你好": "안녕하세요"}

# 중국어 → 영어
translator_en = Translator(
    "config.yaml",
    source__text=["你好"],
    provider__target_lang="EN"
)
result_en = translator_en.run()  # {"你好": "Hello"}
```

### Batch vs Single

```python
# Batch (권장)
translator = Translator(
    "config.yaml",
    source__text=["你好", "谢谢", "再见"]  # 한 번에 처리
)
result = translator.run()

# Single (비효율)
for text in ["你好", "谢谢", "再见"]:
    translator = Translator("config.yaml", source__text=[text])
    result = translator.run()  # 매번 API 호출
```

## 마이그레이션 가이드

### translate_text() 제거 후

**Before:**
```python
translator = Translator(config)
result = translator.translate_text(["你好", "谢谢"])
```

**After:**
```python
translator = Translator(config, source__text=["你好", "谢谢"])
result = translator.run()
translated_list = [result[text] for text in ["你好", "谢谢"]]
```

또는:

```python
# 더 간단하게
translator = Translator({
    "source": {"text": ["你好", "谢谢"]},
    "provider": {"provider": "deepl", "target_lang": "KO"}
})
result = translator.run()
```
