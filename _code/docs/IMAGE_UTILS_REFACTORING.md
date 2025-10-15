# Image Utils 개선 방안

**일시**: 2025년 10월 15일
**목적**: ImageLoader, ImageOCR, ImageOverlay 파이프라인 설계 개선

---

## 1. 핵심 문제

### 현재 상태
```python
# ImageLoader만 사용 가능
loader = ImageLoader(policy)
result = loader.run()
img = result["image"]  # Dict 반환

# ImageOCR/Overlay는 이미지 객체 받을 수 없음
```

### 필요한 구조
```python
# 1. ImageLoader: FSO → 이미지 객체 + 메타데이터
loader = ImageLoader(policy)
img_data = loader.load("image.jpg")  # ImageData 반환

# 2. ImageOCR: 이미지 객체 또는 경로
ocr = ImageOCR(policy)
result = ocr.process(img_data.image)  # 메모리에서 처리
# 또는
result = ocr.process("image.jpg")  # 내부에서 ImageLoader 호출

# 3. ImageOverlay: 이미지 객체 또는 경로
overlay = ImageOverlay(policy)
final = overlay.process(img_data.image, text="Hello")
# 또는
final = overlay.process("image.jpg", text="Hello")
```

---

## 2. 필요한 모델 정의

### models.py 생성
```python
# pillow_utils/models.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any
from PIL import Image


@dataclass
class ImageData:
    """이미지 로드 결과"""
    image: Image.Image
    metadata: ImageMetadata
    source_path: Path
    
    @property
    def width(self) -> int:
        return self.image.width
    
    @property
    def height(self) -> int:
        return self.image.height
    
    @property
    def size(self) -> tuple[int, int]:
        return self.image.size
    
    @property
    def mode(self) -> str:
        return self.image.mode


@dataclass
class ImageMetadata:
    """이미지 메타데이터"""
    # Source info
    source_width: int
    source_height: int
    source_mode: str
    source_format: Optional[str]
    
    # Processed info
    processed_width: int
    processed_height: int
    processed_mode: str
    
    # Ratios
    width_ratio: float
    height_ratio: float
    
    # Saved paths
    saved_image_path: Optional[Path] = None
    saved_meta_path: Optional[Path] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Dict 변환"""
        return {
            "source": {
                "width": self.source_width,
                "height": self.source_height,
                "mode": self.source_mode,
                "format": self.source_format,
            },
            "processed": {
                "width": self.processed_width,
                "height": self.processed_height,
                "mode": self.processed_mode,
            },
            "ratios": {
                "width": self.width_ratio,
                "height": self.height_ratio,
            },
            "saved_image_path": str(self.saved_image_path) if self.saved_image_path else None,
            "saved_meta_path": str(self.saved_meta_path) if self.saved_meta_path else None,
        }


@dataclass
class OCRResult:
    """OCR 결과"""
    text: str
    confidence: float
    language: str
    metadata: Dict[str, Any]


@dataclass
class OverlayResult:
    """Overlay 결과"""
    image: Image.Image
    metadata: Dict[str, Any]
```

---

## 3. ImageLoader 개선

### image_loader.py 수정
```python
from .models import ImageData, ImageMetadata

class ImageLoader:
    """First entrypoint: Loads image with optional processing and persistence."""
    
    def __init__(self, cfg_like=None, **overrides):
        """간소화된 초기화"""
        default_file = Path(__file__).parent / "configs" / "image.yaml"
        self.policy = ConfigLoader.load(
            cfg_like,
            model=ImageLoaderPolicy,
            default_file=default_file,
            **overrides
        )
        
        log_policy = overrides.get('log_policy') or LogPolicy()
        self.logger = LogManager(name="ImageLoader", policy=log_policy).setup()
    
    def load(
        self,
        source: Union[str, Path, Image.Image],
        **overrides
    ) -> ImageData:
        """이미지 로드 (단순화된 API)
        
        Args:
            source: 파일 경로 또는 PIL.Image 객체
            **overrides: 런타임 정책 오버라이드
        
        Returns:
            ImageData (image + metadata)
        """
        # Runtime overrides 적용
        if overrides:
            self.policy = ConfigLoader.load(
                self.policy,
                **overrides
            )
        
        # 이미 Image 객체면 그대로 사용
        if isinstance(source, Image.Image):
            img = source
            source_path = Path("memory")
        else:
            source_path = Path(source)
            img = Image.open(source_path)
        
        # Processing
        processed_img, metadata = self._process_image(img, source_path)
        
        return ImageData(
            image=processed_img,
            metadata=metadata,
            source_path=source_path
        )
    
    def _process_image(
        self,
        img: Image.Image,
        source_path: Path
    ) -> tuple[Image.Image, ImageMetadata]:
        """이미지 처리 및 메타데이터 생성"""
        orig_width, orig_height = img.size
        orig_mode = img.mode
        orig_format = img.format
        
        # Processing
        processed_img = img
        width_ratio = height_ratio = 1.0
        
        # Resize
        if self.policy.processing.resize_to:
            new_width, new_height = self.policy.processing.resize_to
            processed_img = processed_img.resize(
                (new_width, new_height),
                Image.Resampling.LANCZOS
            )
            width_ratio = new_width / orig_width
            height_ratio = new_height / orig_height
        
        # Blur
        if self.policy.processing.blur_radius:
            from PIL import ImageFilter
            processed_img = processed_img.filter(
                ImageFilter.GaussianBlur(self.policy.processing.blur_radius)
            )
        
        # Convert
        if self.policy.processing.convert_mode:
            processed_img = processed_img.convert(
                self.policy.processing.convert_mode
            )
        
        new_width, new_height = processed_img.size
        
        # Save copy (optional)
        saved_image_path = None
        if self.policy.image.save_copy:
            saved_image_path = self._save_image(processed_img, source_path)
        
        # Create metadata
        metadata = ImageMetadata(
            source_width=orig_width,
            source_height=orig_height,
            source_mode=orig_mode,
            source_format=orig_format,
            processed_width=new_width,
            processed_height=new_height,
            processed_mode=processed_img.mode,
            width_ratio=width_ratio,
            height_ratio=height_ratio,
            saved_image_path=saved_image_path,
        )
        
        # Save metadata (optional)
        if self.policy.meta.save_meta:
            saved_meta_path = self._save_metadata(metadata, source_path)
            metadata.saved_meta_path = saved_meta_path
        
        return processed_img, metadata
```

---

## 4. ImageOCR 개선

### image_ocr.py 수정
```python
from .models import ImageData, OCRResult
from .image_loader import ImageLoader

class ImageOCR:
    """OCR 처리 (이미지 객체 또는 경로 지원)"""
    
    def __init__(self, cfg_like=None, **overrides):
        """간소화된 초기화"""
        default_file = Path(__file__).parent / "configs" / "ocr.yaml"
        self.policy = ConfigLoader.load(
            cfg_like,
            model=OCRPolicy,
            default_file=default_file,
            **overrides
        )
        
        self.logger = LogManager(name="ImageOCR").setup()
    
    def process(
        self,
        source: Union[str, Path, Image.Image, ImageData],
        **overrides
    ) -> OCRResult:
        """OCR 수행
        
        Args:
            source: 파일 경로, PIL.Image, 또는 ImageData
            **overrides: 런타임 정책 오버라이드
        
        Returns:
            OCRResult
        """
        # Runtime overrides
        if overrides:
            self.policy = ConfigLoader.load(self.policy, **overrides)
        
        # 1. 이미지 획득
        if isinstance(source, ImageData):
            img = source.image
        elif isinstance(source, Image.Image):
            img = source
        else:
            # 파일 경로 → ImageLoader 사용
            loader = ImageLoader(self.policy.loader_policy)
            img_data = loader.load(source)
            img = img_data.image
        
        # 2. OCR 수행
        text, confidence = self._perform_ocr(img)
        
        return OCRResult(
            text=text,
            confidence=confidence,
            language=self.policy.language,
            metadata={"source_type": type(source).__name__}
        )
    
    def _perform_ocr(self, img: Image.Image) -> tuple[str, float]:
        """실제 OCR 로직"""
        # ... existing OCR code ...
        pass
```

---

## 5. ImageOverlay 개선

### image_overlay.py 수정
```python
from .models import ImageData, OverlayResult
from .image_loader import ImageLoader

class ImageOverlay:
    """이미지 오버레이 (이미지 객체 또는 경로 지원)"""
    
    def __init__(self, cfg_like=None, **overrides):
        """간소화된 초기화"""
        default_file = Path(__file__).parent / "configs" / "overlay.yaml"
        self.policy = ConfigLoader.load(
            cfg_like,
            model=OverlayPolicy,
            default_file=default_file,
            **overrides
        )
        
        self.logger = LogManager(name="ImageOverlay").setup()
    
    def process(
        self,
        source: Union[str, Path, Image.Image, ImageData],
        text: str,
        **overrides
    ) -> OverlayResult:
        """오버레이 수행
        
        Args:
            source: 파일 경로, PIL.Image, 또는 ImageData
            text: 오버레이할 텍스트
            **overrides: 런타임 정책 오버라이드
        
        Returns:
            OverlayResult
        """
        # Runtime overrides
        if overrides:
            self.policy = ConfigLoader.load(self.policy, **overrides)
        
        # 1. 이미지 획득
        if isinstance(source, ImageData):
            img = source.image.copy()  # 복사본 사용
        elif isinstance(source, Image.Image):
            img = source.copy()
        else:
            # 파일 경로 → ImageLoader 사용
            loader = ImageLoader(self.policy.loader_policy)
            img_data = loader.load(source)
            img = img_data.image.copy()
        
        # 2. 오버레이 수행
        result_img = self._apply_overlay(img, text)
        
        return OverlayResult(
            image=result_img,
            metadata={"text": text, "source_type": type(source).__name__}
        )
    
    def _apply_overlay(self, img: Image.Image, text: str) -> Image.Image:
        """실제 오버레이 로직"""
        # ... existing overlay code ...
        pass
```

---

## 6. 파이프라인 사용 예시

### 패턴 1: 단일 작업
```python
# OCR만 필요
ocr = ImageOCR()
result = ocr.process("image.jpg")  # 내부에서 ImageLoader 호출
print(result.text)
```

### 패턴 2: 여러 작업 (효율적)
```python
# Load → OCR → Overlay
loader = ImageLoader()
img_data = loader.load("image.jpg")  # FSO 1회

ocr = ImageOCR()
ocr_result = ocr.process(img_data)  # 메모리에서

overlay = ImageOverlay()
final = overlay.process(img_data, text=ocr_result.text)  # 메모리에서

# FSO 접근 1회로 끝!
```

### 패턴 3: 정책 기반
```python
# 각 모듈에 정책 전달
loader = ImageLoader(resize_to=(800, 600), save_copy=True)
img_data = loader.load("image.jpg")

ocr = ImageOCR(language="kor", preprocess=True)
result = ocr.process(img_data.image)

overlay = ImageOverlay(font_size=20, color="red")
final = overlay.process(img_data.image, text=result.text)
```

### 패턴 4: 런타임 오버라이드
```python
# 기본 정책 + 런타임 조정
loader = ImageLoader("config.yaml")

# 이미지마다 다른 설정
img1 = loader.load("image1.jpg", resize_to=(800, 600))
img2 = loader.load("image2.jpg", resize_to=(1024, 768))
```

---

## 7. 개선 효과

### Before (현재)
```python
# ❌ Dict 반환, 타입 체크 없음
result = loader.run()
img = result["image"]

# ❌ OCR/Overlay가 이미지 객체 못받음
ocr = ImageOCR()
# ocr.process(img)  # 불가능!
```

### After (개선)
```python
# ✅ Typed 객체 반환
img_data: ImageData = loader.load("image.jpg")
img: Image.Image = img_data.image  # 타입 체크

# ✅ OCR/Overlay가 이미지 객체 받음
ocr = ImageOCR()
result: OCRResult = ocr.process(img_data)  # 가능!
result: OCRResult = ocr.process(img_data.image)  # 가능!
result: OCRResult = ocr.process("image.jpg")  # 가능!
```

---

## 8. 구현 순서

1. ✅ **models.py 생성** - ImageData, ImageMetadata 등
2. ✅ **ImageLoader 수정** - load() 메서드, ImageData 반환
3. ✅ **ImageOCR 수정** - process() 메서드, 다양한 입력 지원
4. ✅ **ImageOverlay 수정** - process() 메서드, 다양한 입력 지원
5. ✅ **테스트 작성** - 모든 패턴 테스트
6. ✅ **문서화** - 사용 예시, 파이프라인 패턴

---

## 9. 듀얼 라이선스 고려사항

### 오픈소스 (MIT/Apache 2.0)
- 핵심 ConfigLoader
- 기본 Image 모델
- ImageLoader 기본 기능

### 상용 라이선스
- 고급 OCR 기능
- 고급 Overlay 효과
- 파이프라인 최적화
- 캐싱 메커니즘
- 상용 지원

---

**작성자**: GitHub Copilot  
**날짜**: 2025년 10월 15일  
**버전**: Image Utils Refactoring Plan
