# PaddleOCR 버전 호환성 문제 해결

## 문제 진단

### 현재 상태
- **paddleocr**: 3.0.3
- **paddle**: 3.0.0  
- **에러**: `PaddlePredictorOption.__init__() takes 1 positional argument but 2 were given`

### 원인
PaddleOCR 3.0.3과 PaddlePaddle 3.0.0 간의 **내부 API 불일치** 문제입니다.
`PaddlePredictorOption` 클래스의 초기화 시그니처가 버전 간 변경되었습니다.

## 해결 방법

### 권장: PaddleOCR 3.2.0으로 업그레이드

PaddleOCR 공식 GitHub (2025.08.21 릴리스)에 따르면:

```bash
# 기존 버전 제거
python -m pip uninstall paddleocr -y

# 최신 버전 설치 (PaddleOCR 3.2.0)
python -m pip install paddleocr

# 또는 모든 기능 포함
python -m pip install "paddleocr[all]"
```

### PaddleOCR 3.2.0 주요 개선사항
- ✅ PaddlePaddle 3.0.0, 3.1.0, 3.1.1 완전 지원
- ✅ `PaddlePredictorOption` 초기화 버그 수정
- ✅ PP-OCRv5 모델 추가 (영어, 태국어, 그리스어)
- ✅ CUDA 12 지원
- ✅ 의존성 분리 (core vs optional)

### PaddleOCR 3.x API 변경사항

**기존 2.x API (deprecated):**
```python
from paddleocr import PaddleOCR
ocr = PaddleOCR(lang='ch', use_angle_cls=True, use_gpu=True)
result = ocr.ocr(img_path)  # ❌ 구버전 메서드
```

**새로운 3.x API:**
```python
from paddleocr import PaddleOCR

# 초기화 - 최소한의 파라미터만 사용
ocr = PaddleOCR(
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False
)

# predict() 메서드 사용 (ocr() 대신)
result = ocr.predict(input="image_path")  # ✅ 신규 API
```

### 코드 수정

**modules/ocr_utils/providers/paddle.py:**
```python
from functools import lru_cache
from paddleocr import PaddleOCR

@lru_cache(maxsize=64)
def _get_paddle_cached(lang: str):
    """PaddleOCR 3.2.0 호환 초기화"""
    # lang 파라미터만 전달 (device, use_angle_cls 제거)
    return PaddleOCR(lang=lang)

def build_paddle_instances(langs, device=None, use_angle_cls=True, existing=None):
    """인스턴스 생성 - device/use_angle_cls는 무시됨"""
    insts = dict(existing or {})
    
    for lang in set(map_lang_to_paddle(l) for l in langs):
        if lang not in insts:
            try:
                insts[lang] = _get_paddle_cached(lang)
                logger.info(f"✅ Initialized PaddleOCR 3.2+ for lang={lang}")
            except Exception as e:
                logger.exception(f"❌ Failed: {e}")
    
    return insts

def predict_with_paddle(img, langs, insts, min_conf=0.5):
    """OCR 실행 - predict() 메서드 사용"""
    arr_bgr = np.array(img)[:, :, ::-1]  # RGB to BGR
    results = []
    
    for lang in langs:
        ocr = insts.get(lang)
        if ocr is None:
            continue
        
        # predict() 메서드 사용 (3.x API)
        output = ocr.predict(arr_bgr)
        
        # 결과 파싱 (rec_boxes, rec_texts, rec_scores)
        for item in output:
            boxes = item.get("rec_boxes")
            texts = item.get("rec_texts")
            scores = item.get("rec_scores")
            # ... 처리 로직
    
    return results
```

## 설치 명령어

```powershell
# 현재 환경에서 실행
cd "M:\CALife\CAShop - 구매대행\_code"

# 기존 paddleocr 제거
python -m pip uninstall paddleocr -y

# 최신 버전 설치
python -m pip install --upgrade paddleocr

# 또는 전체 기능 설치
python -m pip install --upgrade "paddleocr[all]"

# 설치 확인
python -c "import paddleocr; print(f'PaddleOCR: {paddleocr.__version__}')"
```

## 참고 자료

- [PaddleOCR GitHub](https://github.com/PaddlePaddle/PaddleOCR)
- [PaddleOCR 3.2.0 Release Notes](https://github.com/PaddlePaddle/PaddleOCR/releases/tag/v3.2.0)
- [Upgrade Notes (2.x → 3.x)](https://paddlepaddle.github.io/PaddleOCR/latest/en/update/upgrade_notes.html)

## 추가 정보

PaddleOCR 3.0.3은 **버그가 있는 버전**입니다. 
공식 릴리스 노트에 따르면 3.2.0에서 수정되었습니다:
- "Full support for PaddlePaddle framework versions 3.1.0 and 3.1.1"
- "Bug Fixes: Resolved internal initialization issues"
