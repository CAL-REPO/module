# xloto.py 엔트리 포인트 실행을 위한 개선 필요 항목

## 🔴 긴급 (Critical) - 스크립트 실행 필수

### 1. **Translator API 단순화 필요**
**현재 문제:**
- `xloto.py`에서 단일 텍스트 번역을 위해 매번 config dict를 생성
- `Translator.run()`은 source 설정 기반으로만 작동 (동적 텍스트 불가)

**해결 방법:**
```python
# translate_utils/services/translator.py 또는 adapter 추가

class Translator:
    # 기존 run() 유지
    def run(self) -> Dict[str, str]:
        """Execute translation based on config"""
        ...
    
    # 추가 필요
    def translate_text(
        self, 
        text: str | List[str],
        *, 
        source_lang: str = "AUTO",
        target_lang: str = "KO"
    ) -> str | List[str]:
        """단일/다중 텍스트 즉시 번역
        
        Args:
            text: 번역할 텍스트 (str 또는 list)
            source_lang: 소스 언어 (기본: AUTO)
            target_lang: 타겟 언어 (기본: KO)
        
        Returns:
            번역된 텍스트 (입력과 동일한 타입)
        """
        is_single = isinstance(text, str)
        texts = [text] if is_single else text
        
        # Provider 사용
        provider = self.provider or self._create_provider()
        results = provider.translate_text(
            texts,
            source_lang=source_lang,
            target_lang=target_lang,
        )
        
        return results[0] if is_single else results
```

**적용 위치:**
- `modules/translate_utils/services/translator.py`
- 또는 `modules/translate_utils/adapter/simple_translator.py` (새로 생성)

---

### 2. **ImageOverlay texts 파라미터 처리 개선**
**현재 문제:**
- `xloto.py`에서 `texts=overlay_texts` 런타임 오버라이드
- `overlay_texts`는 `List[Dict]` 형태이지만 `OverlayTextPolicy` 필요

**해결 방법 A: Policy 자동 변환**
```python
# image_utils/services/image_overlay.py

def _load_config(...) -> ImageOverlayPolicy:
    ...
    # 5. Runtime overrides 적용
    if overrides:
        # texts 파라미터 특별 처리
        if 'texts' in overrides and isinstance(overrides['texts'], list):
            texts_list = []
            for item in overrides['texts']:
                if isinstance(item, dict):
                    # Dict → OverlayTextPolicy 자동 변환
                    texts_list.append(OverlayTextPolicy(**item))
                elif isinstance(item, OverlayTextPolicy):
                    texts_list.append(item)
            overrides['texts'] = texts_list
        
        from keypath_utils import KeyPathDict
        temp = KeyPathDict(config_dict)
        temp.merge(overrides, deep=True)
        config_dict = temp.data
    
    return ImageOverlayPolicy(**config_dict)
```

**해결 방법 B: Adapter 함수 추가**
```python
# image_utils/adapter/overlay_adapter.py (새로 생성)

from typing import List, Dict, Any
from ..core.policy import OverlayTextPolicy
from ..services.image_overlay import ImageOverlay

def create_overlay_from_ocr(
    source_path: str,
    ocr_items: List[Dict[str, Any]],
    xloto_config: str,
    output_dir: str,
) -> Dict[str, Any]:
    """OCR 결과에서 바로 오버레이 생성
    
    Args:
        source_path: 소스 이미지 경로
        ocr_items: [{'bbox': [...], 'text': '...'}] 형태
        xloto_config: xloto.yaml 경로
        output_dir: 저장 디렉토리
    
    Returns:
        ImageOverlay.run() 결과
    """
    # Dict → OverlayTextPolicy 변환
    overlay_texts = [
        OverlayTextPolicy(
            bbox=item['bbox'],
            text=item['text'],
            # 기타 기본값은 yaml에서 가져옴
        )
        for item in ocr_items
    ]
    
    overlay = ImageOverlay(
        xloto_config,
        section="overlay",
        source__path=source_path,
        save__directory=output_dir,
        texts=overlay_texts,  # Policy 리스트
    )
    
    return overlay.run()
```

**적용 위치:**
- 방법 A: `modules/image_utils/services/image_overlay.py`의 `_load_config()` 수정
- 방법 B: `modules/image_utils/adapter/overlay_adapter.py` 생성

---

## 🟡 중요 (High Priority) - UX 개선

### 3. **환경변수 설정 자동화**
**현재 문제:**
- 수동으로 `$env:CASHOP_PATHS` 설정 필요
- 경로 오타 시 에러 메시지만 출력

**해결 방법:**
```python
# scripts/setup_env.py (새로 생성)

import os
from pathlib import Path

def setup_cashop_env():
    """CASHOP_PATHS 환경변수 자동 설정"""
    script_dir = Path(__file__).parent.resolve()
    config_path = script_dir.parent / "configs" / "paths.local.yaml"
    
    if config_path.exists():
        os.environ["CASHOP_PATHS"] = str(config_path)
        print(f"✅ CASHOP_PATHS 설정: {config_path}")
        return True
    else:
        print(f"❌ paths.local.yaml 없음: {config_path}")
        return False

if __name__ == "__main__":
    setup_cashop_env()
```

**xloto.py 수정:**
```python
# xloto.py 상단에 추가
import sys
from pathlib import Path

# 자동 환경변수 설정 시도
if "CASHOP_PATHS" not in os.environ:
    setup_script = Path(__file__).parent / "setup_env.py"
    if setup_script.exists():
        exec(setup_script.read_text())
```

---

### 4. **Translation Cache 활성화 확인**
**현재 상태:**
- `translate_utils`에 cache 기능 있음
- `xloto.yaml`에 설정 필요

**확인 사항:**
```yaml
# configs/translate.yaml (새로 생성 또는 xloto.yaml에 추가)

translate:
  provider:
    provider: "deepl"
    source_lang: "ZH"
    target_lang: "KO"
  
  cache:
    enabled: true
    db_path: "${db_dir}/translate_cache.sqlite3"
```

**적용:**
- `modules/translate_utils/services/storage.py` 확인
- Cache 저장 경로 설정 검증

---

## 🟢 선택 (Medium Priority) - 성능 최적화

### 5. **Batch Translation 지원**
**현재 문제:**
- OCR 결과마다 개별 번역 요청
- API 호출 횟수 증가 → 속도 저하

**해결 방법:**
```python
# xloto.py 수정

def process_image(self, image_path: Path, output_dir: Path) -> bool:
    # ... OCR 실행 ...
    
    # 모든 텍스트를 한 번에 번역
    original_texts = [item.text for item in ocr_items]
    
    # Batch translation
    translated_texts = self.translator.translate_text(
        original_texts,
        source_lang="ZH",
        target_lang="KO"
    )
    
    # OCR item + 번역 결과 매핑
    overlay_texts = [
        {
            'bbox': ocr_items[i].bbox,
            'text': translated_texts[i],
        }
        for i in range(len(ocr_items))
    ]
```

**필요 작업:**
- Translator.translate_text() 메서드 구현 (위 #1)

---

### 6. **PaddleOCR 인스턴스 재사용**
**현재 문제:**
- ImageOCR 매번 새로운 인스턴스 생성 가능
- GPU 메모리 낭비

**해결 방법:**
```python
# xloto.py 수정

class ImageOTOProcessor:
    def __init__(self, ...):
        # OCR 인스턴스 한 번만 생성
        self.ocr = ImageOCR(
            self.xloto_cfg_path,
            section="ocr",
        )
        self.translator = Translator()
    
    def process_image(self, image_path: Path, output_dir: Path) -> bool:
        # source_override만 사용
        ocr_result = self.ocr.run(source_override=str(image_path))
```

**확인 사항:**
- `image_utils/services/image_ocr.py`의 OCR 엔진 lazy-loading 구현 확인

---

## 🔵 향후 개선 (Low Priority) - 장기 개선

### 7. **진행 상태 저장/재개 기능**
```python
# xloto_state.json
{
  "last_processed": "CAPFB-001",
  "timestamp": "2025-10-15 14:30:00",
  "processed_count": 45,
  "failed": ["CAPFB-003", "CAPFB-007"]
}
```

### 8. **병렬 처리 (멀티프로세싱)**
```python
from multiprocessing import Pool

def process_cas_batch(cas_list, processor):
    with Pool(processes=4) as pool:
        results = pool.map(processor.process_cas_no, cas_list)
```

### 9. **웹 UI 대시보드**
- Flask/FastAPI 기반 진행 상황 모니터링
- 실시간 로그 스트리밍
- 이미지 비교 뷰어 (원본 vs 번역)

---

## 📋 우선순위별 작업 순서

### Phase 1: 스크립트 실행 가능 (1-2시간)
1. ✅ Translator.translate_text() 메서드 추가
2. ✅ ImageOverlay texts 파라미터 자동 변환
3. ⚠️ 테스트 실행 및 디버깅

### Phase 2: 안정성 개선 (2-3시간)
4. 환경변수 자동 설정
5. Translation Cache 활성화
6. 에러 처리 강화

### Phase 3: 성능 최적화 (선택)
7. Batch Translation
8. OCR 인스턴스 재사용
9. 병렬 처리

---

## 🛠️ 구체적인 작업 파일

### 즉시 수정 필요:
```
modules/translate_utils/services/translator.py
  ↓ translate_text() 메서드 추가

modules/image_utils/services/image_overlay.py
  ↓ _load_config()에서 texts Dict → Policy 자동 변환

scripts/xloto.py
  ↓ translate_text() 사용하도록 수정
  ↓ overlay texts 파라미터 간소화
```

### 선택적 개선:
```
modules/image_utils/adapter/overlay_adapter.py (새로 생성)
  ↓ create_overlay_from_ocr() 헬퍼 함수

scripts/setup_env.py (새로 생성)
  ↓ 환경변수 자동 설정

configs/translate.yaml (새로 생성)
  ↓ DeepL API 설정, Cache 설정
```

---

## 🔑 핵심 요약

**반드시 필요:**
1. `Translator.translate_text()` - 동적 텍스트 번역
2. `ImageOverlay` texts 파라미터 - Dict 자동 변환

**권장:**
3. 환경변수 자동 설정
4. Translation Cache
5. Batch Translation

**선택:**
6. 병렬 처리
7. 진행 상태 저장
8. 웹 UI
