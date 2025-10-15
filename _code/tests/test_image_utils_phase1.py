# -*- coding: utf-8 -*-
"""Phase 1 검증: Policy 통합 테스트

이 스크립트는 통합된 policy.py가 정상 동작하는지 검증합니다.
"""

from pathlib import Path


def test_imports():
    """Import 테스트"""
    print("=" * 60)
    print("Test 1: Import 테스트")
    print("=" * 60)
    
    try:
        from image_utils.core import (
            # Common
            ImageSourcePolicy,
            ImageSavePolicy,
            ImageMetaPolicy,
            
            # ImageLoader
            ImageProcessPolicy,
            ImageLoaderPolicy,
            
            # ImageOCR
            OCRProviderPolicy,
            OCRPreprocessPolicy,
            OCRPostprocessPolicy,
            ImageOCRPolicy,
            
            # ImageOverlay
            OverlayTextPolicy,
            ImageOverlayPolicy,
            
            # Models
            OCRItem,
        )
        
        print("✅ 모든 Policy import 성공")
        print(f"   - ImageLoaderPolicy: {ImageLoaderPolicy}")
        print(f"   - ImageOCRPolicy: {ImageOCRPolicy}")
        print(f"   - ImageOverlayPolicy: {ImageOverlayPolicy}")
        print(f"   - OCRItem: {OCRItem}")
        print()
        return True
        
    except Exception as e:
        print(f"❌ Import 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_image_loader_policy():
    """ImageLoaderPolicy 생성 테스트"""
    print("=" * 60)
    print("Test 2: ImageLoaderPolicy 생성")
    print("=" * 60)
    
    try:
        from image_utils.core import ImageLoaderPolicy, ImageSourcePolicy
        
        # 기본 Policy 생성
        policy = ImageLoaderPolicy(
            source=ImageSourcePolicy(path=Path("test.jpg"))
        )
        
        print("✅ ImageLoaderPolicy 생성 성공")
        print(f"   - source.path: {policy.source.path}")
        print(f"   - save.save_copy: {policy.save.save_copy}")
        print(f"   - save.suffix: {policy.save.suffix}")
        print(f"   - meta.save_meta: {policy.meta.save_meta}")
        print(f"   - process.resize_to: {policy.process.resize_to}")
        print(f"   - log: {policy.log}")
        print()
        return True
        
    except Exception as e:
        print(f"❌ ImageLoaderPolicy 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_image_ocr_policy():
    """ImageOCRPolicy 생성 테스트"""
    print("=" * 60)
    print("Test 3: ImageOCRPolicy 생성")
    print("=" * 60)
    
    try:
        from image_utils.core import ImageOCRPolicy, ImageSourcePolicy
        
        # 기본 Policy 생성
        policy = ImageOCRPolicy(
            source=ImageSourcePolicy(path=Path("test.jpg"))
        )
        
        print("✅ ImageOCRPolicy 생성 성공")
        print(f"   - source.path: {policy.source.path}")
        print(f"   - provider.provider: {policy.provider.provider}")
        print(f"   - provider.langs: {policy.provider.langs}")
        print(f"   - preprocess.max_width: {policy.preprocess.max_width}")
        print(f"   - postprocess.strip_special_chars: {policy.postprocess.strip_special_chars}")
        print(f"   - save.save_copy: {policy.save.save_copy}")
        print(f"   - log: {policy.log}")
        print()
        return True
        
    except Exception as e:
        print(f"❌ ImageOCRPolicy 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_image_overlay_policy():
    """ImageOverlayPolicy 생성 테스트"""
    print("=" * 60)
    print("Test 4: ImageOverlayPolicy 생성")
    print("=" * 60)
    
    try:
        from image_utils.core import (
            ImageOverlayPolicy,
            ImageSourcePolicy,
            OverlayTextPolicy,
        )
        
        # 기본 Policy 생성
        policy = ImageOverlayPolicy(
            source=ImageSourcePolicy(path=Path("test.jpg")),
            texts=[
                OverlayTextPolicy(
                    text="Hello World",
                    polygon=[(10, 10), (100, 10), (100, 50), (10, 50)]
                )
            ]
        )
        
        print("✅ ImageOverlayPolicy 생성 성공")
        print(f"   - source.path: {policy.source.path}")
        print(f"   - texts: {len(policy.texts)}개")
        print(f"   - texts[0].text: {policy.texts[0].text}")
        print(f"   - texts[0].polygon: {policy.texts[0].polygon}")
        print(f"   - background_opacity: {policy.background_opacity}")
        print(f"   - save.save_copy: {policy.save.save_copy}")
        print(f"   - log: {policy.log}")
        print()
        return True
        
    except Exception as e:
        print(f"❌ ImageOverlayPolicy 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ocr_item():
    """OCRItem 생성 테스트"""
    print("=" * 60)
    print("Test 5: OCRItem 생성")
    print("=" * 60)
    
    try:
        from image_utils.core import OCRItem
        
        item = OCRItem(
            text="테스트",
            conf=0.95,
            quad=[[10, 10], [100, 10], [100, 50], [10, 50]],
            bbox={"x_min": 10, "y_min": 10, "x_max": 100, "y_max": 50},
            angle_deg=0.0,
            lang="ch",
            order=1
        )
        
        print("✅ OCRItem 생성 성공")
        print(f"   - text: {item.text}")
        print(f"   - conf: {item.conf}")
        print(f"   - bbox: {item.bbox}")
        print(f"   - lang: {item.lang}")
        print()
        return True
        
    except Exception as e:
        print(f"❌ OCRItem 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backward_compatibility():
    """하위 호환성 테스트"""
    print("=" * 60)
    print("Test 6: 하위 호환성 (Deprecated Aliases)")
    print("=" * 60)
    
    try:
        from image_utils.core import ImagePolicy, ImageProcessorPolicy
        
        print("✅ Deprecated aliases import 성공")
        print(f"   - ImagePolicy: {ImagePolicy}")
        print(f"   - ImageProcessorPolicy: {ImageProcessorPolicy}")
        print("   ⚠️ 이들은 향후 제거 예정입니다.")
        print()
        return True
        
    except Exception as e:
        print(f"❌ 하위 호환성 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """모든 테스트 실행"""
    print("\n" + "=" * 60)
    print("Phase 1: Policy 통합 검증")
    print("=" * 60 + "\n")
    
    results = []
    
    # Test 1: Imports
    results.append(test_imports())
    
    # Test 2: ImageLoaderPolicy
    results.append(test_image_loader_policy())
    
    # Test 3: ImageOCRPolicy
    results.append(test_image_ocr_policy())
    
    # Test 4: ImageOverlayPolicy
    results.append(test_image_overlay_policy())
    
    # Test 5: OCRItem
    results.append(test_ocr_item())
    
    # Test 6: Backward compatibility
    results.append(test_backward_compatibility())
    
    # 결과 요약
    print("=" * 60)
    print("Phase 1 검증 결과")
    print("=" * 60)
    total = len(results)
    passed = sum(results)
    
    print(f"✅ 통과: {passed}/{total}")
    print(f"❌ 실패: {total - passed}/{total}")
    
    if all(results):
        print("\n🎉 Phase 1 완료! 모든 테스트 통과!")
        print("\n다음 단계:")
        print("  - Phase 2: EntryPoint 분리 (entry_points/)")
        print("  - Phase 3: cfg_loader, logs_utils 통합")
    else:
        print("\n⚠️ 일부 테스트 실패")
    
    print()


if __name__ == "__main__":
    main()
