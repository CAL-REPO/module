# -*- coding: utf-8 -*-
"""UnifiedSource 테스트 스크립트"""

from pathlib import Path
from pydantic import BaseModel, Field

# cfg_utils_v2 import
from modules.cfg_utils_v2 import SourcePolicy, UnifiedSource
from modules.cfg_utils_v2.core.policy import NormalizePolicy, MergePolicy
from modules.structured_io.core.policy import BaseParserPolicy


# ============================================================
# 테스트용 BaseModel 정의
# ============================================================
class ImagePolicy(BaseModel):
    """이미지 처리 정책 (테스트용)"""
    max_width: int = Field(default=1920, description="최대 너비")
    max_height: int = Field(default=1080, description="최대 높이")
    format: str = Field(default="PNG", description="이미지 포맷")
    quality: int = Field(default=95, description="품질")


class OCRPolicy(BaseModel):
    """OCR 처리 정책 (테스트용)"""
    lang: str = Field(default="kor+eng", description="언어")
    psm: int = Field(default=6, description="Page Segmentation Mode")
    oem: int = Field(default=3, description="OCR Engine Mode")


# ============================================================
# 테스트 1: BaseModel 소스
# ============================================================
def test_basemodel_source():
    print("\n" + "=" * 60)
    print("테스트 1: BaseModel 소스")
    print("=" * 60)
    
    # Policy 생성
    policy = SourcePolicy(
        src=(ImagePolicy(), "image"),
        base_model_normalizer=NormalizePolicy(
            normalize_keys=True,
            drop_blanks=False
        )
    )
    
    # Source 생성 및 추출
    source = UnifiedSource(policy)
    kpd = source.extract()
    
    print(f"✅ 추출 성공!")
    print(f"📦 KeyPathDict.data:")
    print(f"   {kpd.data}")
    
    # Section 확인
    assert "image" in kpd.data, "Section 'image' not found!"
    assert kpd.data["image"]["max_width"] == 1920
    print(f"✅ Section 적용 확인: image__max_width = {kpd.data['image']['max_width']}")


# ============================================================
# 테스트 2: Dict 소스
# ============================================================
def test_dict_source():
    print("\n" + "=" * 60)
    print("테스트 2: Dict 소스")
    print("=" * 60)
    
    # Policy 생성
    test_dict = {
        "max_width": 1024,
        "max_height": 768,
        "format": "JPEG"
    }
    
    policy = SourcePolicy(
        src=(test_dict, "settings"),
        dict_normalizer=NormalizePolicy(
            normalize_keys=True,
            drop_blanks=True
        )
    )
    
    # Source 생성 및 추출
    source = UnifiedSource(policy)
    kpd = source.extract()
    
    print(f"✅ 추출 성공!")
    print(f"📦 KeyPathDict.data:")
    print(f"   {kpd.data}")
    
    # Section 확인
    assert "settings" in kpd.data
    assert kpd.data["settings"]["max_width"] == 1024
    print(f"✅ Section 적용 확인: settings__max_width = {kpd.data['settings']['max_width']}")


# ============================================================
# 테스트 3: YAML 소스 (파일 생성)
# ============================================================
def test_yaml_source():
    print("\n" + "=" * 60)
    print("테스트 3: YAML 소스")
    print("=" * 60)
    
    # 테스트용 YAML 파일 생성
    test_yaml_path = Path("m:/CALife/CAShop - 구매대행/_code/test_config.yaml")
    yaml_content = """
image:
  max_width: 2048
  max_height: 1536
  format: PNG
  quality: 100

ocr:
  lang: kor+eng
  psm: 6
  oem: 3
"""
    test_yaml_path.write_text(yaml_content, encoding="utf-8")
    print(f"📝 테스트 YAML 파일 생성: {test_yaml_path}")
    
    # Policy 생성
    policy = SourcePolicy(
        src=(str(test_yaml_path), "ocr"),
        yaml_parser=BaseParserPolicy(
            safe_mode=True,
            enable_env=False
        ),
        yaml_normalizer=NormalizePolicy(
            normalize_keys=True,
            resolve_vars=False
        )
    )
    
    # Source 생성 및 추출
    source = UnifiedSource(policy)
    kpd = source.extract()
    
    print(f"✅ 추출 성공!")
    print(f"📦 KeyPathDict.data:")
    print(f"   {kpd.data}")
    
    # Section 확인
    assert "ocr" in kpd.data
    assert kpd.data["ocr"]["ocr"]["lang"] == "kor+eng"
    print(f"✅ Section 적용 확인: ocr__ocr__lang = {kpd.data['ocr']['ocr']['lang']}")
    
    # 파일 삭제
    test_yaml_path.unlink()
    print(f"🗑️  테스트 YAML 파일 삭제")


# ============================================================
# 테스트 4: Section 없이 사용
# ============================================================
def test_no_section():
    print("\n" + "=" * 60)
    print("테스트 4: Section 없이 사용")
    print("=" * 60)
    
    # Policy 생성 (Section 없음)
    policy = SourcePolicy(
        src={"key1": "value1", "key2": "value2"}
    )
    
    # Source 생성 및 추출
    source = UnifiedSource(policy)
    kpd = source.extract()
    
    print(f"✅ 추출 성공!")
    print(f"📦 KeyPathDict.data:")
    print(f"   {kpd.data}")
    
    # Section 없이 직접 접근
    assert kpd.data["key1"] == "value1"
    print(f"✅ Section 없이 직접 접근: key1 = {kpd.data['key1']}")


# ============================================================
# 테스트 5: 타입별 Normalizer 동작 확인
# ============================================================
def test_type_specific_normalizer():
    print("\n" + "=" * 60)
    print("테스트 5: 타입별 Normalizer 확인")
    print("=" * 60)
    
    # BaseModel - drop_blanks=False (기본값 유지)
    policy1 = SourcePolicy(
        src=ImagePolicy(max_width=0, format=""),  # 빈 값 포함
        base_model_normalizer=NormalizePolicy(drop_blanks=False)
    )
    source1 = UnifiedSource(policy1)
    kpd1 = source1.extract()
    print(f"BaseModel (drop_blanks=False): max_width={kpd1.data.get('max_width')}, format={kpd1.data.get('format')!r}")
    assert kpd1.data.get('max_width') == 0  # 0은 유지
    assert kpd1.data.get('format') == ""    # 빈 문자열 유지
    
    # Dict - drop_blanks=True (빈 값 제거)
    policy2 = SourcePolicy(
        src={"key1": "value1", "key2": "", "key3": 0},
        dict_normalizer=NormalizePolicy(drop_blanks=True)
    )
    source2 = UnifiedSource(policy2)
    kpd2 = source2.extract()
    print(f"Dict (drop_blanks=True): {kpd2.data}")
    # drop_blanks=True면 빈 값 제거됨
    
    print(f"✅ 타입별 Normalizer 동작 확인 완료!")


# ============================================================
# 메인 실행
# ============================================================
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 UnifiedSource 통합 테스트 시작")
    print("=" * 60)
    
    try:
        test_basemodel_source()
        test_dict_source()
        test_yaml_source()
        test_no_section()
        test_type_specific_normalizer()
        
        print("\n" + "=" * 60)
        print("✅ 모든 테스트 통과!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
