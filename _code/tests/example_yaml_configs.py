# -*- coding: utf-8 -*-
"""YAML 설정 파일 사용 예제.

이 스크립트는 3가지 image_utils EntryPoint의 YAML 설정 사용법을 보여줍니다.
"""

import sys
from pathlib import Path

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

from image_utils import ImageLoader, ImageOCR, ImageOverlay


def example_image_loader():
    """ImageLoader YAML 설정 예제."""
    print("=" * 70)
    print("1. ImageLoader - 간단한 설정")
    print("=" * 70)
    
    # 간단한 설정 사용
    loader = ImageLoader("configs/image_loader_simple.yaml")
    print(f"✅ ImageLoader 초기화 완료")
    print(f"   Source: {loader.policy.source.path}")
    print(f"   Save suffix: {loader.policy.save.name.suffix}")
    print(f"   Resize to: {loader.policy.process.resize_to}")
    
    print("\n" + "=" * 70)
    print("2. ImageLoader - 전체 설정")
    print("=" * 70)
    
    # 전체 설정 사용
    loader_full = ImageLoader("configs/image_loader_full.yaml")
    print(f"✅ ImageLoader (full) 초기화 완료")
    print(f"   FSO tail_mode: {loader_full.policy.save.name.tail_mode}")
    print(f"   FSO ensure_unique: {loader_full.policy.save.name.ensure_unique}")
    print(f"   FSO sanitize: {loader_full.policy.save.name.sanitize}")
    print(f"   Log sinks: {len(loader_full.policy.log.sinks)}")


def example_image_ocr():
    """ImageOCR YAML 설정 예제."""
    print("\n" + "=" * 70)
    print("3. ImageOCR - 간단한 설정")
    print("=" * 70)
    
    # 간단한 설정 사용
    ocr = ImageOCR("configs/image_ocr_simple.yaml")
    print(f"✅ ImageOCR 초기화 완료")
    print(f"   Source: {ocr.policy.source.path}")
    print(f"   Provider: {ocr.policy.provider.provider}")
    print(f"   Languages: {ocr.policy.provider.langs}")
    print(f"   Min confidence: {ocr.policy.provider.min_conf}")
    
    print("\n" + "=" * 70)
    print("4. ImageOCR - 전체 설정")
    print("=" * 70)
    
    # 전체 설정 사용
    ocr_full = ImageOCR("configs/image_ocr_full.yaml")
    print(f"✅ ImageOCR (full) 초기화 완료")
    print(f"   Preprocess max_width: {ocr_full.policy.preprocess.max_width}")
    print(f"   Postprocess IoU threshold: {ocr_full.policy.postprocess.deduplicate_iou_threshold}")
    print(f"   Meta tail_mode: {ocr_full.policy.meta.name.tail_mode}")


def example_image_overlay():
    """ImageOverlay YAML 설정 예제."""
    print("\n" + "=" * 70)
    print("5. ImageOverlay - 간단한 설정")
    print("=" * 70)
    
    # 간단한 설정 사용
    overlay = ImageOverlay("configs/image_overlay_simple.yaml")
    print(f"✅ ImageOverlay 초기화 완료")
    print(f"   Source: {overlay.policy.source.path}")
    print(f"   Texts count: {len(overlay.policy.texts)}")
    print(f"   Background opacity: {overlay.policy.background_opacity}")
    if overlay.policy.texts:
        first_text = overlay.policy.texts[0]
        print(f"   First text: '{first_text.text}'")
        print(f"   Font size: {first_text.font.size}")
    
    print("\n" + "=" * 70)
    print("6. ImageOverlay - 전체 설정")
    print("=" * 70)
    
    # 전체 설정 사용
    overlay_full = ImageOverlay("configs/image_overlay_full.yaml")
    print(f"✅ ImageOverlay (full) 초기화 완료")
    print(f"   Texts count: {len(overlay_full.policy.texts)}")
    for idx, text in enumerate(overlay_full.policy.texts, 1):
        print(f"   Text {idx}: '{text.text}' (size={text.font.size}, anchor={text.anchor})")


def example_runtime_override():
    """런타임 오버라이드 예제."""
    print("\n" + "=" * 70)
    print("7. 런타임 오버라이드 예제")
    print("=" * 70)
    
    # YAML 로드 + 런타임 오버라이드
    loader = ImageLoader(
        "configs/image_loader_simple.yaml",
        source={"path": "different/path.jpg"},
        save={"name": {"suffix": "_custom"}},
        process={"resize_to": [1024, 768]}
    )
    
    print(f"✅ 런타임 오버라이드 적용")
    print(f"   Overridden source: {loader.policy.source.path}")
    print(f"   Overridden suffix: {loader.policy.save.name.suffix}")
    print(f"   Overridden resize: {loader.policy.process.resize_to}")


def main():
    """메인 실행 함수."""
    print("\n" + "=" * 70)
    print("image_utils YAML 설정 사용 예제")
    print("=" * 70)
    
    try:
        example_image_loader()
        example_image_ocr()
        example_image_overlay()
        example_runtime_override()
        
        print("\n" + "=" * 70)
        print("✅ 모든 예제 완료!")
        print("=" * 70)
        
    except FileNotFoundError as e:
        print(f"\n⚠️  설정 파일을 찾을 수 없습니다: {e}")
        print("configs/ 디렉토리에 YAML 파일이 있는지 확인하세요.")
    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
