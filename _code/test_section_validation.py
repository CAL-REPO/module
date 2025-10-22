# -*- coding: utf-8 -*-
"""Section Validation 구현 테스트

요구사항 검증:
1. YAML 최상위 == Section → 정상 추출
2. YAML 최상위 != Section (1개 키) → Raise
3. YAML 최상위 여러 개 + Section 없음 → Raise
4. YAML Flat 구조 → Wrap
"""

import os
import tempfile
from pathlib import Path
from cfg_utils import ConfigLoader

print("=" * 80)
print("Section Validation 구현 테스트")
print("=" * 80)

# 테스트용 임시 YAML 파일 생성
temp_dir = Path(tempfile.gettempdir()) / "cfg_test"
temp_dir.mkdir(exist_ok=True)

# =============================================================================
# Case 1: YAML 최상위 == Section → 정상 추출
# =============================================================================
print("\n[Case 1] YAML 최상위 == Section → 정상 추출")
print("-" * 80)

yaml1_path = temp_dir / "test1.yaml"
yaml1_path.write_text("""
image:
  max_width: 1024
  format: "JPEG"
""", encoding="utf-8")

try:
    loader = ConfigLoader(src=(str(yaml1_path), "image"))
    config = loader.to_dict(section="image")
    print(f"✅ 성공: {list(config.keys())}")
    print(f"   max_width: {config.get('max_width')}")
except Exception as e:
    print(f"❌ 실패: {e}")

# =============================================================================
# Case 2: YAML 최상위 != Section (1개 키) → Raise
# =============================================================================
print("\n[Case 2] YAML 최상위 != Section (1개 키) → Raise")
print("-" * 80)

yaml2_path = temp_dir / "test2.yaml"
yaml2_path.write_text("""
image_policy:
  max_width: 1024
  format: "JPEG"
""", encoding="utf-8")

try:
    loader = ConfigLoader(src=(str(yaml2_path), "image"))
    config = loader.to_dict(section="image")
    print(f"❌ 실패: Raise되지 않음! {list(config.keys())}")
except ValueError as e:
    print(f"✅ 정상 Raise!")
    print(f"   에러 메시지: {str(e)[:100]}...")
except Exception as e:
    print(f"⚠️  예상과 다른 에러: {type(e).__name__}: {e}")

# =============================================================================
# Case 3: YAML 최상위 여러 개 + Section 없음 → Raise
# =============================================================================
print("\n[Case 3] YAML 최상위 여러 개 + Section 없음 → Raise")
print("-" * 80)

yaml3_path = temp_dir / "test3.yaml"
yaml3_path.write_text("""
section1:
  key: value1
section2:
  key: value2
""", encoding="utf-8")

try:
    loader = ConfigLoader(src=(str(yaml3_path), "image"))
    config = loader.to_dict(section="image")
    print(f"❌ 실패: Raise되지 않음! {list(config.keys())}")
except ValueError as e:
    print(f"✅ 정상 Raise!")
    print(f"   에러 메시지: {str(e)[:100]}...")
except Exception as e:
    print(f"⚠️  예상과 다른 에러: {type(e).__name__}: {e}")

# =============================================================================
# Case 4: YAML Flat 구조 → Wrap
# =============================================================================
print("\n[Case 4] YAML Flat 구조 → Wrap")
print("-" * 80)

yaml4_path = temp_dir / "test4.yaml"
yaml4_path.write_text("""
max_width: 1024
format: "JPEG"
quality: 90
""", encoding="utf-8")

try:
    loader = ConfigLoader(src=(str(yaml4_path), "image"))
    config = loader.to_dict(section="image")
    print(f"✅ 성공 (Wrap됨): {list(config.keys())}")
    print(f"   max_width: {config.get('max_width')}")
    print(f"   format: {config.get('format')}")
except Exception as e:
    print(f"❌ 실패: {e}")

# =============================================================================
# Case 5: webdriver 실제 파일 테스트
# =============================================================================
print("\n[Case 5] webdriver_china.yaml 실제 파일 테스트")
print("-" * 80)

webdriver_china_path = "m:/CALife/CAShop - 구매대행/_code/modules/crawl_utils/configs/webdriver_china.yaml"
if Path(webdriver_china_path).exists():
    try:
        # 올바른 사용 (일치)
        loader = ConfigLoader(src=(webdriver_china_path, "webdriver_china"))
        config = loader.to_dict(section="webdriver_china")
        print(f"✅ 올바른 section 사용 성공: region={config.get('region')}")
    except Exception as e:
        print(f"❌ 실패: {e}")
    
    try:
        # 잘못된 사용 (불일치)
        print("\n   잘못된 section 'webdriver' 사용 시도:")
        loader = ConfigLoader(src=(webdriver_china_path, "webdriver"))
        config = loader.to_dict(section="webdriver")
        print(f"   ❌ 실패: Raise되지 않음!")
    except ValueError as e:
        print(f"   ✅ 정상 Raise!")
        print(f"   에러 메시지: {str(e)[:150]}...")
    except Exception as e:
        print(f"   ⚠️  예상과 다른 에러: {type(e).__name__}: {e}")
else:
    print("⚠️  파일 없음")

# =============================================================================
# Case 6: Mixed 구조 (dict와 primitive 혼합)
# =============================================================================
print("\n[Case 6] Mixed 구조 테스트 (dict와 primitive 혼합)")
print("-" * 80)

yaml6_path = temp_dir / "test6.yaml"
yaml6_path.write_text("""
max_width: 1024
nested:
  key: value
format: "JPEG"
""", encoding="utf-8")

try:
    loader = ConfigLoader(src=(str(yaml6_path), "image"))
    config = loader.to_dict(section="image")
    print(f"✅ 성공 (Flat으로 판단되어 Wrap됨): {list(config.keys())}")
    print(f"   max_width: {config.get('max_width')}")
    print(f"   nested: {config.get('nested')}")
except Exception as e:
    print(f"❌ 실패: {e}")

print("\n" + "=" * 80)
print("테스트 완료")
print("=" * 80)

print("""
✅ 구현 완료 내용:

1. YAML 최상위 == Section → 정상 추출
2. YAML 최상위 != Section (1개 키) → ValueError Raise
3. YAML 최상위 여러 개 + Section 없음 → ValueError Raise
4. YAML Flat 구조 → section으로 Wrap

에러 메시지:
- Section mismatch: 명확한 수정 방법 3가지 제시
- Section not found: 사용 가능한 section 목록 제공

Flat 구조 판단:
- any(not isinstance(data[k], dict) for k in yaml_keys)
- primitive 값이 하나라도 있으면 Flat으로 판단
""")

# 정리
import shutil
shutil.rmtree(temp_dir, ignore_errors=True)
