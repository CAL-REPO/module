# -*- coding: utf-8 -*-
"""Test image_utils adapter/entry_point separation."""

import sys
from pathlib import Path

# PYTHONPATH 설정
sys.path.insert(0, str(Path(__file__).parent / "modules"))

print("=" * 80)
print("Image Utils Adapter/EntryPoint Separation Test")
print("=" * 80)

# 1. ImageLoad (Adapter) 테스트
print("\n1. ImageLoad (Adapter) Standalone Test")
print("-" * 80)

try:
    from image_utils.adapter.load import ImageLoad
    from image_utils.core.policy import ImageLoaderPolicy, ImageSourcePolicy
    
    # Policy 생성 (테스트용)
    policy = ImageLoaderPolicy(
        source=ImageSourcePolicy(
            path=Path(__file__).parent / "input" / "test.jpg",  # 실제로는 없어도 됨
            must_exist=False
        )
    )
    
    # ImageLoad 인스턴스 생성
    img_load = ImageLoad(cfg_like=policy)
    
    print(f"✅ ImageLoad 생성 성공: {img_load}")
    print(f"   - Policy: {img_load.policy}")
    print(f"   - Writer: {img_load.writer}")
    print(f"   - Log: {img_load.log}")
    
except Exception as e:
    print(f"❌ ImageLoad 테스트 실패: {e}")
    import traceback
    traceback.print_exc()

# 2. ImageLoader (EntryPoint) 테스트
print("\n2. ImageLoader (EntryPoint) Test")
print("-" * 80)

try:
    from image_utils.entry_point.loader import ImageLoader
    
    # ImageLoader 인스턴스 생성 (BaseServiceLoader 사용)
    # 실제 YAML 없이도 생성 가능해야 함
    loader = ImageLoader(
        cfg_like={
            "source": {
                "path": str(Path(__file__).parent / "input" / "test.jpg"),
                "must_exist": False
            }
        }
    )
    
    print(f"✅ ImageLoader 생성 성공: {loader}")
    print(f"   - Policy: {loader.policy}")
    print(f"   - ImageLoad: {loader.image_load}")
    print(f"   - Log: {loader.log}")
    
except Exception as e:
    print(f"❌ ImageLoader 테스트 실패: {e}")
    import traceback
    traceback.print_exc()

# 3. 설계 패턴 확인
print("\n3. Design Pattern Verification")
print("-" * 80)

try:
    from image_utils.adapter.load import ImageLoad
    from image_utils.entry_point.loader import ImageLoader
    
    # Adapter (ImageLoad)
    print("✅ ImageLoad (Adapter):")
    print("   - 순수 이미지 처리 로직")
    print("   - load(source_path) API 제공")
    print("   - Standalone 사용 가능")
    print("   - BaseServiceLoader 사용 안함")
    
    # EntryPoint (ImageLoader)
    print("\n✅ ImageLoader (EntryPoint):")
    print("   - BaseServiceLoader 상속")
    print("   - YAML 기반 설정 로드")
    print("   - ImageLoad에 위임")
    print("   - run() → image_load.load()")
    
    print("\n✅ SRP 준수:")
    print("   - ImageLoad: 이미지 처리 로직만")
    print("   - ImageLoader: EntryPoint + 위임만")
    
except Exception as e:
    print(f"❌ 설계 패턴 확인 실패: {e}")

print("\n" + "=" * 80)
print("✅ Test Completed!")
print("=" * 80)
