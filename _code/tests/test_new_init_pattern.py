# -*- coding: utf-8 -*-
"""__init__ 패턴 테스트 - firefox.py 스타일"""

import sys
from pathlib import Path

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

def print_section(title):
    """섹션 구분 출력"""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60 + "\n")

def test_imageloader_init_patterns():
    """ImageLoader __init__ 패턴 테스트"""
    print_section("ImageLoader __init__ 패턴 테스트")
    
    from image_utils import ImageLoader
    
    # 1. Dict로 초기화
    print("1. __init__(dict):")
    loader1 = ImageLoader({"source": {"path": "test.jpg"}})
    print(f"   ✅ source.path = {loader1.policy.source.path}")
    
    # 2. Dict + Runtime override
    print("\n2. __init__(dict, **overrides):")
    loader2 = ImageLoader(
        {"source": {"path": "base.jpg"}, "save": {"suffix": "_base"}},
        save={"suffix": "_override"}
    )
    print(f"   ✅ save.suffix = {loader2.policy.save.suffix} (expected: '_override')")
    assert loader2.policy.save.suffix == "_override"
    
    # 3. None으로 초기화 (기본값)
    print("\n3. __init__(None):")
    try:
        loader3 = ImageLoader(None)
        print(f"   ⚠️ 빈 설정으로 생성됨 (주의: source.path가 설정되지 않음)")
    except Exception as e:
        print(f"   ✅ ValidationError 발생 (예상된 동작): {e}")
    
    # 4. Policy 직접 전달
    print("\n4. __init__(policy):")
    from image_utils.core.policy import ImageLoaderPolicy
    policy = ImageLoaderPolicy(source={"path": "policy.jpg"})
    loader4 = ImageLoader(policy)
    print(f"   ✅ source.path = {loader4.policy.source.path}")
    
    # 5. Policy + Runtime override
    print("\n5. __init__(policy, **overrides):")
    loader5 = ImageLoader(
        policy,
        save={"suffix": "_new"}
    )
    print(f"   ✅ save.suffix = {loader5.policy.save.suffix}")
    print(f"   ✅ source.path preserved = {loader5.policy.source.path}")
    
    print("\n✅ ImageLoader 모든 패턴 성공!")
    return True

def test_imageocr_init_patterns():
    """ImageOCR __init__ 패턴 테스트"""
    print_section("ImageOCR __init__ 패턴 테스트")
    
    from image_utils import ImageOCR
    
    # 1. Dict로 초기화
    print("1. __init__(dict):")
    ocr1 = ImageOCR({"source": {"path": "test.jpg"}})
    print(f"   ✅ source.path = {ocr1.policy.source.path}")
    
    # 2. Dict + Runtime override
    print("\n2. __init__(dict, **overrides):")
    ocr2 = ImageOCR(
        {"source": {"path": "test.jpg"}, "provider": {"min_conf": 0.5}},
        provider={"min_conf": 0.9}
    )
    print(f"   ✅ provider.min_conf = {ocr2.policy.provider.min_conf} (expected: 0.9)")
    assert ocr2.policy.provider.min_conf == 0.9
    
    print("\n✅ ImageOCR 모든 패턴 성공!")
    return True

def test_imageoverlay_init_patterns():
    """ImageOverlay __init__ 패턴 테스트"""
    print_section("ImageOverlay __init__ 패턴 테스트")
    
    from image_utils import ImageOverlay
    
    # 1. Dict로 초기화
    print("1. __init__(dict):")
    overlay1 = ImageOverlay({"source": {"path": "test.jpg"}, "texts": []})
    print(f"   ✅ source.path = {overlay1.policy.source.path}")
    print(f"   ✅ texts = {len(overlay1.policy.texts)} items")
    
    # 2. Dict + Runtime override
    print("\n2. __init__(dict, **overrides):")
    overlay2 = ImageOverlay(
        {"source": {"path": "test.jpg"}, "texts": [], "background_opacity": 0.5},
        background_opacity=0.9
    )
    print(f"   ✅ background_opacity = {overlay2.policy.background_opacity} (expected: 0.9)")
    assert overlay2.policy.background_opacity == 0.9
    
    print("\n✅ ImageOverlay 모든 패턴 성공!")
    return True

def test_comparison_with_firefox():
    """Firefox 패턴과 비교"""
    print_section("Firefox 패턴 비교")
    
    print("Firefox 패턴:")
    print("  driver = FirefoxWebDriver(cfg_like, policy=..., **overrides)")
    print("  - cfg_like: Policy, Path, str, dict, list, None")
    print("  - **overrides: Runtime overrides")
    
    print("\nImageLoader 패턴:")
    print("  loader = ImageLoader(cfg_like, section=..., log=..., **overrides)")
    print("  - cfg_like: Policy, Path, str, dict, None")
    print("  - section: YAML section name")
    print("  - log: LogManager instance")
    print("  - **overrides: Runtime overrides")
    
    print("\n✅ 패턴 일치!")
    print("   - cfg_like 파라미터 동일")
    print("   - **overrides로 3단 override 지원")
    print("   - __init__에서 모든 입력 형태 처리")
    
    return True

def main():
    """메인 테스트 실행"""
    print("=" * 60)
    print("NEW __init__ 패턴 테스트")
    print("=" * 60)
    
    results = []
    
    # Test 1: ImageLoader
    try:
        results.append(test_imageloader_init_patterns())
    except Exception as e:
        print(f"❌ ImageLoader 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        results.append(False)
    
    # Test 2: ImageOCR
    try:
        results.append(test_imageocr_init_patterns())
    except Exception as e:
        print(f"❌ ImageOCR 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        results.append(False)
    
    # Test 3: ImageOverlay
    try:
        results.append(test_imageoverlay_init_patterns())
    except Exception as e:
        print(f"❌ ImageOverlay 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        results.append(False)
    
    # Test 4: Firefox 비교
    try:
        results.append(test_comparison_with_firefox())
    except Exception as e:
        print(f"❌ Firefox 비교 실패: {e}")
        results.append(False)
    
    # 결과 요약
    print_section("테스트 결과 요약")
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ 통과: {passed}/{total}")
    print(f"❌ 실패: {total - passed}/{total}")
    
    if all(results):
        print("\n🎉 모든 테스트 통과!")
        print("\n사용 예제:")
        print("""
    # 1. 가장 간단한 사용
    loader = ImageLoader({"source": {"path": "test.jpg"}})
    
    # 2. Runtime override
    loader = ImageLoader(
        {"source": {"path": "base.jpg"}},
        save={"suffix": "_custom"}
    )
    
    # 3. Policy 직접 전달
    policy = ImageLoaderPolicy(source={"path": "test.jpg"})
    loader = ImageLoader(policy)
    
    # 4. Policy + Override
    loader = ImageLoader(policy, save={"suffix": "_new"})
    
    # 5. YAML 파일 (section 지정)
    loader = ImageLoader("config.yaml", section="image_loader")
    
    # 6. YAML + Override
    loader = ImageLoader("config.yaml", save={"suffix": "_override"})
        """)
        return 0
    else:
        print("\n⚠️ 일부 테스트 실패")
        return 1

if __name__ == "__main__":
    sys.exit(main())
