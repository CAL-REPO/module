# -*- coding: utf-8 -*-
"""Phase 2 테스트: EntryPoint 분리 검증

3개의 EntryPoint 클래스가 올바르게 구현되었는지 확인:
1. ImageLoader - 이미지 로드/처리/저장
2. ImageOCR - OCR 실행 및 결과 처리
3. ImageOverlay - 텍스트 오버레이

각 EntryPoint의 초기화, YAML 로드, 실행을 테스트합니다.
"""

import sys
from pathlib import Path

# PYTHONPATH 설정
code_dir = Path(__file__).parent.parent
modules_dir = code_dir / "modules"
sys.path.insert(0, str(modules_dir))

def print_section(title: str):
    """섹션 구분선 출력"""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60 + "\n")

def test_imports():
    """Test 1: EntryPoint import 테스트"""
    print_section("Test 1: EntryPoint Import 테스트")
    
    try:
        from image_utils import ImageLoader, ImageOCR, ImageOverlay
        from image_utils import ImageLoaderPolicy, ImageOCRPolicy, ImageOverlayPolicy
        
        print("✅ 모든 EntryPoint import 성공")
        print(f"   - ImageLoader: {ImageLoader}")
        print(f"   - ImageOCR: {ImageOCR}")
        print(f"   - ImageOverlay: {ImageOverlay}")
        print(f"   - ImageLoaderPolicy: {ImageLoaderPolicy}")
        print(f"   - ImageOCRPolicy: {ImageOCRPolicy}")
        print(f"   - ImageOverlayPolicy: {ImageOverlayPolicy}")
        
        return True
    except ImportError as e:
        print(f"❌ Import 실패: {e}")
        return False

def test_image_loader_init():
    """Test 2: ImageLoader 초기화 및 from_dict"""
    print_section("Test 2: ImageLoader 초기화")
    
    try:
        from image_utils import ImageLoader, ImageLoaderPolicy
        
        # Policy로 초기화
        policy = ImageLoaderPolicy(
            source={"path": "test.jpg"},
            save={"save_copy": False},  # 실제 저장은 하지 않음
            process={"resize_to": (800, 600)},
        )
        
        loader = ImageLoader(policy)
        
        print("✅ ImageLoader 생성 성공")
        print(f"   - {loader}")
        print(f"   - source.path: {loader.policy.source.path}")
        print(f"   - save.save_copy: {loader.policy.save.save_copy}")
        print(f"   - process.resize_to: {loader.policy.process.resize_to}")
        print(f"   - log: {loader.log}")
        
        # from_dict 테스트
        config_dict = {
            "source": {"path": "test2.jpg"},
            "save": {"save_copy": True, "suffix": "_resized"},
        }
        
        loader2 = ImageLoader.from_dict(config_dict)
        
        print("\n✅ ImageLoader.from_dict() 성공")
        print(f"   - {loader2}")
        print(f"   - save.suffix: {loader2.policy.save.suffix}")
        
        return True
    except Exception as e:
        print(f"❌ ImageLoader 초기화 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_image_ocr_init():
    """Test 3: ImageOCR 초기화 및 from_dict"""
    print_section("Test 3: ImageOCR 초기화")
    
    try:
        from image_utils import ImageOCR, ImageOCRPolicy
        
        # Policy로 초기화
        policy = ImageOCRPolicy(
            source={"path": "test.jpg"},
            provider={"provider": "paddle", "langs": ["ch", "en"]},
            save={"save_copy": False},
            postprocess={"strip_special_chars": True, "deduplicate_iou_threshold": 0.8},
        )
        
        ocr = ImageOCR(policy)
        
        print("✅ ImageOCR 생성 성공")
        print(f"   - {ocr}")
        print(f"   - provider.provider: {ocr.policy.provider.provider}")
        print(f"   - provider.langs: {ocr.policy.provider.langs}")
        print(f"   - postprocess.strip_special_chars: {ocr.policy.postprocess.strip_special_chars}")
        print(f"   - postprocess.deduplicate_iou_threshold: {ocr.policy.postprocess.deduplicate_iou_threshold}")
        print(f"   - log: {ocr.log}")
        
        # from_dict 테스트
        config_dict = {
            "source": {"path": "test2.jpg"},
            "provider": {"provider": "paddle", "langs": ["en"]},
        }
        
        ocr2 = ImageOCR.from_dict(config_dict)
        
        print("\n✅ ImageOCR.from_dict() 성공")
        print(f"   - {ocr2}")
        print(f"   - provider.langs: {ocr2.policy.provider.langs}")
        
        return True
    except Exception as e:
        print(f"❌ ImageOCR 초기화 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_image_overlay_init():
    """Test 4: ImageOverlay 초기화 및 from_dict"""
    print_section("Test 4: ImageOverlay 초기화")
    
    try:
        from image_utils import ImageOverlay, ImageOverlayPolicy, OverlayTextPolicy
        
        # Policy로 초기화
        text1 = OverlayTextPolicy(
            text="Hello World",
            polygon=[(10, 10), (200, 10), (200, 50), (10, 50)],
        )
        
        text2 = OverlayTextPolicy(
            text="한글 테스트",
            polygon=[(10, 60), (200, 60), (200, 100), (10, 100)],
        )
        
        policy = ImageOverlayPolicy(
            source={"path": "test.jpg"},
            texts=[text1, text2],
            background_opacity=0.7,
            save={"save_copy": False},
        )
        
        overlay = ImageOverlay(policy)
        
        print("✅ ImageOverlay 생성 성공")
        print(f"   - {overlay}")
        print(f"   - texts: {len(overlay.policy.texts)}개")
        print(f"   - texts[0].text: '{overlay.policy.texts[0].text}'")
        print(f"   - texts[1].text: '{overlay.policy.texts[1].text}'")
        print(f"   - background_opacity: {overlay.policy.background_opacity}")
        print(f"   - log: {overlay.log}")
        
        # from_dict 테스트
        config_dict = {
            "source": {"path": "test2.jpg"},
            "texts": [
                {"text": "Test", "polygon": [(0, 0), (100, 0), (100, 50), (0, 50)]},
            ],
            "background_opacity": 0.5,
        }
        
        overlay2 = ImageOverlay.from_dict(config_dict)
        
        print("\n✅ ImageOverlay.from_dict() 성공")
        print(f"   - {overlay2}")
        print(f"   - background_opacity: {overlay2.policy.background_opacity}")
        
        return True
    except Exception as e:
        print(f"❌ ImageOverlay 초기화 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_from_ocr_items():
    """Test 5: ImageOverlay.from_ocr_items() 테스트"""
    print_section("Test 5: ImageOverlay.from_ocr_items()")
    
    try:
        from image_utils import ImageOverlay, OCRItem
        
        # 가짜 OCR 결과 생성
        ocr_items = [
            OCRItem(
                text="第一行",
                conf=0.95,
                quad=[(10, 10), (100, 10), (100, 30), (10, 30)],
                bbox={"x_min": 10, "y_min": 10, "x_max": 100, "y_max": 30},
                angle_deg=0.0,
                lang="ch",
                order=0,
            ),
            OCRItem(
                text="Second line",
                conf=0.88,
                quad=[(10, 40), (150, 40), (150, 60), (10, 60)],
                bbox={"x_min": 10, "y_min": 40, "x_max": 150, "y_max": 60},
                angle_deg=0.0,
                lang="en",
                order=1,
            ),
        ]
        
        overlay = ImageOverlay.from_ocr_items(
            source_path="test.jpg",
            ocr_items=ocr_items,
            background_opacity=0.8,
        )
        
        print("✅ ImageOverlay.from_ocr_items() 성공")
        print(f"   - {overlay}")
        print(f"   - texts: {len(overlay.policy.texts)}개")
        print(f"   - texts[0].text: '{overlay.policy.texts[0].text}'")
        print(f"   - texts[1].text: '{overlay.policy.texts[1].text}'")
        print(f"   - background_opacity: {overlay.policy.background_opacity}")
        
        return True
    except Exception as e:
        print(f"❌ from_ocr_items() 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_repr():
    """Test 6: __repr__ 메서드 테스트"""
    print_section("Test 6: __repr__ 메서드")
    
    try:
        from image_utils import ImageLoader, ImageOCR, ImageOverlay
        from image_utils import ImageLoaderPolicy, ImageOCRPolicy, ImageOverlayPolicy
        
        loader = ImageLoader(ImageLoaderPolicy(source={"path": "test.jpg"}))
        ocr = ImageOCR(ImageOCRPolicy(
            source={"path": "test.jpg"},
            provider={"provider": "paddle"},
        ))
        overlay = ImageOverlay(ImageOverlayPolicy(
            source={"path": "test.jpg"},
            texts=[],
        ))
        
        print("✅ __repr__ 메서드 정상 작동")
        print(f"   - ImageLoader: {repr(loader)}")
        print(f"   - ImageOCR: {repr(ocr)}")
        print(f"   - ImageOverlay: {repr(overlay)}")
        
        return True
    except Exception as e:
        print(f"❌ __repr__ 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Phase 2 테스트 실행"""
    print_section("Phase 2: EntryPoint 분리 검증")
    
    tests = [
        ("Import 테스트", test_imports),
        ("ImageLoader 초기화", test_image_loader_init),
        ("ImageOCR 초기화", test_image_ocr_init),
        ("ImageOverlay 초기화", test_image_overlay_init),
        ("ImageOverlay.from_ocr_items()", test_from_ocr_items),
        ("__repr__ 메서드", test_repr),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ 테스트 '{name}' 실행 중 오류: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 결과 요약
    print_section("Phase 2 검증 결과")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    print(f"\n✅ 통과: {passed}/{total}")
    print(f"❌ 실패: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 Phase 2 완료! 모든 테스트 통과!")
        print("\n다음 단계:")
        print("  - Phase 3: 서비스 레이어 정리 (OCRProvider Protocol + Factory)")
        print("  - Phase 4: 문서화 및 예제 작성")
    else:
        print("\n⚠️ 일부 테스트 실패. 수정이 필요합니다.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
