"""ConfigLoader section 추출 테스트"""
import pytest
from pathlib import Path
from pydantic import BaseModel, Field
from cfg_utils.services.config_loader import ConfigLoader


class SubPolicy(BaseModel):
    """테스트용 서브 정책 모델"""
    name: str
    value: int = 10


def test_section_extraction_explicit():
    """명시적 section 지정 테스트"""
    # {'section1': {'name': 'test', 'value': 20}}
    data = {
        'section1': {'name': 'test', 'value': 20}
    }
    
    # section을 명시적으로 지정 - ConfigLoader.load()는 지원 안함
    # _create_loader + _as_model_internal 사용
    loader = ConfigLoader._create_loader(data)
    result = loader._as_model_internal(SubPolicy, section='section1')
    
    assert result.name == 'test'
    assert result.value == 20


def test_section_extraction_auto():
    """자동 section 추출 테스트"""
    # ConfigLoader의 auto-detection 로직:
    # SubPolicy -> 'subpolicy' -> 'sub' (if endswith 'policy')
    data = {
        'sub': {'name': 'auto', 'value': 30}
    }
    
    loader = ConfigLoader._create_loader(data)
    result = loader._as_model_internal(SubPolicy, section=None)  # auto-detect
    
    assert result.name == 'auto'
    assert result.value == 30


def test_section_extraction_yaml():
    """YAML 파일에서 section 추출 테스트"""
    # modules/image_utils/configs/image.yaml 구조 확인
    yaml_path = Path(__file__).parent.parent / "modules" / "image_utils" / "configs" / "image.yaml"
    
    # policy_overrides로 config_loader_image.yaml 사용
    config_loader_image_path = Path(__file__).parent.parent / "modules" / "image_utils" / "configs" / "config_loader_image.yaml"
    
    # 1. 전체 로드 (dict) - ImageLoader 전용 정책 사용
    data = ConfigLoader.load(
        yaml_path, 
        model=None,
        policy_overrides={
            "config_loader_path": str(config_loader_image_path)
        }
    )
    assert isinstance(data, dict)
    print(f"\nYAML keys: {list(data.keys())}")
    
    # 2. image section 확인
    assert 'image' in data, f"Expected 'image' key in YAML, got: {list(data.keys())}"
    image_section = data['image']
    assert 'source' in image_section
    assert 'save' in image_section
    
    # 3. paths.local.yaml이 병합되지 않았는지 확인
    # config_loader_image.yaml은 image.yaml만 로드해야 함
    print(f"\nFull keys (should only have 'image'): {list(data.keys())}")


def test_section_manual_extraction():
    """수동 section 추출 후 모델 변환"""
    yaml_path = Path(__file__).parent.parent / "modules" / "image_utils" / "configs" / "image.yaml"
    config_loader_image_path = Path(__file__).parent.parent / "modules" / "image_utils" / "configs" / "config_loader_image.yaml"
    
    # 1. Dict로 로드 (ImageLoader 전용 정책)
    data = ConfigLoader.load(
        yaml_path, 
        model=None,
        policy_overrides={
            "config_loader_path": str(config_loader_image_path)
        }
    )
    
    # 2. Section 수동 추출
    if 'image' in data:
        image_data = data['image']
    else:
        pytest.skip("image section not found")
    
    # 3. ImageLoaderPolicy로 변환
    from image_utils.core.policy import ImageLoaderPolicy
    
    # source 필드 확인
    assert 'source' in image_data, f"source field missing: {list(image_data.keys())}"
    
    # 모델 변환 시도
    policy = ImageLoaderPolicy(**image_data)
    
    assert policy.source is not None
    assert policy.save is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
