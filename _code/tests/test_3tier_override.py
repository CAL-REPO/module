# -*- coding: utf-8 -*-
"""3단 Override 테스트 - EntryPoint에서 YAML + Section + Runtime Override 테스트

3단 Override 패턴:
1. Base YAML config
2. Section extraction
3. Runtime overrides (kwargs)

Note: 테스트 중 무관한 모듈에서 import 오류 발생 시 10초 대기 후 재시도 (최대 5분)
"""

import sys
import time
from pathlib import Path

# PYTHONPATH 설정
code_dir = Path(__file__).parent.parent
modules_dir = code_dir / "modules"
sys.path.insert(0, str(modules_dir))

# Retry 설정
MAX_RETRIES = 30  # 5분 = 30 * 10초
RETRY_DELAY = 10  # 10초

def print_section(title: str):
    """섹션 구분선 출력"""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60 + "\n")

def test_3tier_override():
    """Test 1: 3단 Override 패턴 검증"""
    print_section("Test 1: 3단 Override 패턴 검증")
    
    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            from image_utils import ImageLoader, ImageLoaderPolicy
            break  # Import 성공
        except ImportError as e:
            if "structured_data" in str(e) or "data_utils" in str(e):
                retry_count += 1
                print(f"⚠️ 무관한 모듈 import 오류 발생 (시도 {retry_count}/{MAX_RETRIES}): {e}")
                if retry_count < MAX_RETRIES:
                    print(f"   {RETRY_DELAY}초 후 재시도...")
                    time.sleep(RETRY_DELAY)
                else:
                    print("❌ 최대 재시도 횟수 초과. 테스트 중단.")
                    return False
            else:
                raise  # 다른 import 오류는 즉시 실패
    
    try:
        
        # 1. from_dict with overrides
        print("1-1. from_dict with runtime overrides:")
        base_config = {
            "source": {"path": "base.jpg"},
            "save": {
                "save_copy": True,
                "suffix": "_base",
                "directory": "output/base"
            }
        }
        
        loader = ImageLoader(
            base_config,
            # Runtime overrides (3rd tier)
            save={"suffix": "_override", "directory": "output/override"}
        )
        
        print(f"   - Base suffix: '_base' → Override suffix: '{loader.policy.save.suffix}'")
        print(f"   - Base dir: 'output/base' → Override dir: '{loader.policy.save.directory}'")
        print(f"   - save_copy preserved: {loader.policy.save.save_copy}")
        
        # 디버깅: 실제 값 출력
        print(f"   [DEBUG] Expected directory: 'output/override' or 'output\\override'")
        print(f"   [DEBUG] Actual directory type: {type(loader.policy.save.directory)}")
        print(f"   [DEBUG] Directory comparison: '{loader.policy.save.directory}' == 'output/override': {loader.policy.save.directory == 'output/override'}")
        
        # Path 정규화하여 비교
        import os
        expected_dir = os.path.normpath("output/override")
        actual_dir = os.path.normpath(str(loader.policy.save.directory))
        
        if loader.policy.save.suffix == "_override" and actual_dir == expected_dir:
            print("   ✅ Runtime override 성공!")
        else:
            print(f"   ❌ Runtime override 실패!")
            print(f"      Expected: suffix='_override', dir='{expected_dir}'")
            print(f"      Actual: suffix='{loader.policy.save.suffix}', dir='{actual_dir}'")
            return False
        
        # 2. Nested override test
        print("\n1-2. Nested override test:")
        loader2 = ImageLoader(
            base_config,
            source={"path": "override.jpg"},  # Override nested value
            save={"quality": 95}  # Add new field
        )
        
        print(f"   - Base path: 'base.jpg' → Override path: '{loader2.policy.source.path}'")
        print(f"   - New field quality: {loader2.policy.save.quality}")
        print(f"   - Other fields preserved: suffix='{loader2.policy.save.suffix}'")
        
        # 디버깅: 실제 값 확인
        print(f"   [DEBUG] source.path check: '{loader2.policy.source.path}' == 'override.jpg': {loader2.policy.source.path == 'override.jpg'}")
        print(f"   [DEBUG] save.quality check: {loader2.policy.save.quality} == 95: {loader2.policy.save.quality == 95}")
        print(f"   [DEBUG] save.suffix check: '{loader2.policy.save.suffix}' == '_base': {loader2.policy.save.suffix == '_base'}")
        
        if (str(loader2.policy.source.path) == "override.jpg" and 
            loader2.policy.save.quality == 95 and 
            loader2.policy.save.suffix == "_base"):
            print("   ✅ Nested override with preservation 성공!")
        else:
            print(f"   ❌ Nested override 실패!")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 3단 Override 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_imageocr_override():
    """Test 2: ImageOCR 3단 Override"""
    print_section("Test 2: ImageOCR 3단 Override")
    
    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            from image_utils import ImageOCR, ImageOCRPolicy
            break
        except ImportError as e:
            if "structured_data" in str(e) or "data_utils" in str(e):
                retry_count += 1
                print(f"⚠️ 무관한 모듈 import 오류 (시도 {retry_count}/{MAX_RETRIES}): {e}")
                if retry_count < MAX_RETRIES:
                    print(f"   {RETRY_DELAY}초 후 재시도...")
                    time.sleep(RETRY_DELAY)
                else:
                    print("❌ 최대 재시도 횟수 초과. 테스트 중단.")
                    return False
            else:
                raise
    
    try:
        
        base_config = {
            "source": {"path": "test.jpg"},
            "provider": {
                "provider": "paddle",
                "langs": ["ch", "en"],
                "min_conf": 0.5
            },
            "postprocess": {
                "strip_special_chars": False,
                "deduplicate_iou_threshold": 0.5
            }
        }
        
        # Runtime override
        ocr = ImageOCR(
            base_config,
            provider={"min_conf": 0.9},  # Override min_conf
            postprocess={"strip_special_chars": True}  # Override strip_special_chars
        )
        
        print(f"   - Base min_conf: 0.5 → Override: {ocr.policy.provider.min_conf}")
        print(f"   - Base strip_special_chars: False → Override: {ocr.policy.postprocess.strip_special_chars}")
        print(f"   - Preserved langs: {ocr.policy.provider.langs}")
        print(f"   - Preserved deduplicate: {ocr.policy.postprocess.deduplicate_iou_threshold}")
        
        if (ocr.policy.provider.min_conf == 0.9 and 
            ocr.policy.postprocess.strip_special_chars is True and
            ocr.policy.provider.langs == ["ch", "en"] and
            ocr.policy.postprocess.deduplicate_iou_threshold == 0.5):
            print("   ✅ ImageOCR override 성공!")
            return True
        else:
            print("   ❌ ImageOCR override 실패!")
            return False
            
    except Exception as e:
        print(f"❌ ImageOCR Override 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_imageoverlay_override():
    """Test 3: ImageOverlay 3단 Override"""
    print_section("Test 3: ImageOverlay 3단 Override")
    
    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            from image_utils import ImageOverlay, ImageOverlayPolicy
            break
        except ImportError as e:
            if "structured_data" in str(e) or "data_utils" in str(e):
                retry_count += 1
                print(f"⚠️ 무관한 모듈 import 오류 (시도 {retry_count}/{MAX_RETRIES}): {e}")
                if retry_count < MAX_RETRIES:
                    print(f"   {RETRY_DELAY}초 후 재시도...")
                    time.sleep(RETRY_DELAY)
                else:
                    print("❌ 최대 재시도 횟수 초과. 테스트 중단.")
                    return False
            else:
                raise
    
    try:
        
        base_config = {
            "source": {"path": "test.jpg"},
            "texts": [],
            "background_opacity": 0.5
        }
        
        # Runtime override
        overlay = ImageOverlay(
            base_config,
            background_opacity=0.9,  # Override opacity
            source={"path": "new.jpg"}  # Override path
        )
        
        print(f"   - Base opacity: 0.5 → Override: {overlay.policy.background_opacity}")
        print(f"   - Base path: 'test.jpg' → Override: '{overlay.policy.source.path}'")
        print(f"   - Preserved texts: {len(overlay.policy.texts)} items")
        
        # 디버깅: 실제 값 확인
        print(f"   [DEBUG] opacity check: {overlay.policy.background_opacity} == 0.9: {overlay.policy.background_opacity == 0.9}")
        print(f"   [DEBUG] path check: '{overlay.policy.source.path}' == 'new.jpg': {overlay.policy.source.path == 'new.jpg'}")
        print(f"   [DEBUG] path type: {type(overlay.policy.source.path)}")
        print(f"   [DEBUG] texts check: {len(overlay.policy.texts)} == 0: {len(overlay.policy.texts) == 0}")
        
        if (overlay.policy.background_opacity == 0.9 and 
            str(overlay.policy.source.path) == "new.jpg" and
            len(overlay.policy.texts) == 0):
            print("   ✅ ImageOverlay override 성공!")
            return True
        else:
            print("   ❌ ImageOverlay override 실패!")
            return False
            
    except Exception as e:
        print(f"❌ ImageOverlay Override 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_deep_merge():
    """Test 4: Deep merge 동작 확인"""
    print_section("Test 4: Deep Merge 동작 확인")
    
    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            from image_utils import ImageLoader
            break
        except ImportError as e:
            if "structured_data" in str(e) or "data_utils" in str(e):
                retry_count += 1
                print(f"⚠️ 무관한 모듈 import 오류 (시도 {retry_count}/{MAX_RETRIES}): {e}")
                if retry_count < MAX_RETRIES:
                    print(f"   {RETRY_DELAY}초 후 재시도...")
                    time.sleep(RETRY_DELAY)
                else:
                    print("❌ 최대 재시도 횟수 초과. 테스트 중단.")
                    return False
            else:
                raise
    
    try:
        
        base_config = {
            "source": {"path": "base.jpg", "must_exist": True, "convert_mode": "RGB"},
            "save": {"save_copy": True, "suffix": "_base", "quality": 90}
        }
        
        # Partial override - deep merge should preserve other fields
        loader = ImageLoader(
            base_config,
            source={"path": "override.jpg"}  # Only override path
        )
        
        print(f"   - Overridden: source.path = '{loader.policy.source.path}'")
        print(f"   - Preserved: source.must_exist = {loader.policy.source.must_exist}")
        print(f"   - Preserved: source.convert_mode = '{loader.policy.source.convert_mode}'")
        print(f"   - Preserved: save.quality = {loader.policy.save.quality}")
        
        # 디버깅: 실제 값 확인
        print(f"   [DEBUG] path check: '{loader.policy.source.path}' == 'override.jpg': {loader.policy.source.path == 'override.jpg'}")
        print(f"   [DEBUG] path type: {type(loader.policy.source.path)}")
        print(f"   [DEBUG] must_exist check: {loader.policy.source.must_exist} is True: {loader.policy.source.must_exist is True}")
        print(f"   [DEBUG] convert_mode check: '{loader.policy.source.convert_mode}' == 'RGB': {loader.policy.source.convert_mode == 'RGB'}")
        print(f"   [DEBUG] quality check: {loader.policy.save.quality} == 90: {loader.policy.save.quality == 90}")
        
        if (str(loader.policy.source.path) == "override.jpg" and
            loader.policy.source.must_exist is True and
            loader.policy.source.convert_mode == "RGB" and
            loader.policy.save.quality == 90):
            print("   ✅ Deep merge 정상 작동!")
            return True
        else:
            print("   ❌ Deep merge 실패!")
            return False
            
    except Exception as e:
        print(f"❌ Deep merge 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """3단 Override 테스트 실행"""
    print_section("3단 Override 테스트 시작")
    
    tests = [
        ("3단 Override 패턴", test_3tier_override),
        ("ImageOCR Override", test_imageocr_override),
        ("ImageOverlay Override", test_imageoverlay_override),
        ("Deep Merge", test_deep_merge),
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
    print_section("3단 Override 테스트 결과")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    print(f"\n✅ 통과: {passed}/{total}")
    print(f"❌ 실패: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 3단 Override 완벽 구현!")
        print("\n사용 예제:")
        print("""
    # 1. YAML + Runtime override
    loader = ImageLoader(
        "config.yaml",
        section="image_loader",
        save={"suffix": "_custom"}  # Runtime override
    )
    
    # 2. Dict + Runtime override
    loader = ImageLoader(
        {"source": {"path": "base.jpg"}},
        source={"path": "override.jpg"}  # Partial override
    )
    
    # 3. Nested override with preservation
    ocr = ImageOCR(
        base_config,
        provider={"min_conf": 0.9},  # Only override min_conf
        # Other provider fields are preserved!
    )
        """)
    else:
        print("\n⚠️ 일부 테스트 실패. 수정이 필요합니다.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
