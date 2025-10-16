# -*- coding: utf-8 -*-
# Tests for cfg_utils module

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'modules'))

import pytest
from cfg_utils import ConfigLoader, ConfigNormalizer, ConfigPolicy
from pydantic import BaseModel

class SampleModel(BaseModel):
    key: str
    value: int

def test_config_loader_basic():
    """Test ConfigLoader 기본 동작 - dict 반환"""
    yaml_content = """
key: test
value: 123
    """
    # paths.local.yaml 로드 비활성화
    result = ConfigLoader.load(
        yaml_content,
        policy_overrides={"yaml.source_paths": None}
    )
    assert result == {"key": "test", "value": 123}

def test_config_loader_with_model():
    """Test ConfigLoader - Pydantic 모델 반환"""
    yaml_content = """
key: test
value: 123
    """
    model = ConfigLoader.load(yaml_content, model=SampleModel)
    assert isinstance(model, SampleModel)
    assert model.key == "test"
    assert model.value == 123

def test_config_loader_with_overrides():
    """Test ConfigLoader - 런타임 오버라이드"""
    yaml_content = """
key: test
value: 123
    """
    result = ConfigLoader.load(
        yaml_content,
        policy_overrides={"yaml.source_paths": None},
        value=999
    )
    assert result == {"key": "test", "value": 999}

def test_config_loader_multiple_files():
    """Test ConfigLoader - 여러 파일 병합"""
    yaml1 = """
section1:
  key: test1
  value: 123
    """
    yaml2 = """
section2:
  key: test2
  value: 456
    """
    result = ConfigLoader.load(
        [yaml1, yaml2],
        policy_overrides={"yaml.source_paths": None}
    )
    assert result == {
        "section1": {"key": "test1", "value": 123},
        "section2": {"key": "test2", "value": 456}
    }

def test_config_loader_deep_merge():
    """Test ConfigLoader - Deep merge"""
    yaml1 = """
config:
  database:
    host: localhost
    port: 5432
    """
    yaml2 = """
config:
  database:
    port: 3306
    user: admin
    """
    result = ConfigLoader.load([yaml1, yaml2])
    assert result["config"]["database"] == {
        "host": "localhost",
        "port": 3306,
        "user": "admin"
    }

def test_config_loader_reference():
    """Test ConfigLoader - Reference 해석"""
    yaml_content = """
base_name: myapp
config_file: ${base_name}.yaml
log_file: ${base_name}.log
    """
    result = ConfigLoader.load(
        yaml_content,
        policy_overrides={"yaml.source_paths": None}
    )
    assert result["base_name"] == "myapp"
    assert result["config_file"] == "myapp.yaml"
    assert result["log_file"] == "myapp.log"

def test_config_normalizer():
    """Test ConfigNormalizer - drop_blanks"""
    data = {
        "key": "value",
        "empty": "",
        "none": None,
        "keep": "data"
    }
    policy = ConfigPolicy(resolve_reference=False, drop_blanks=True)
    normalizer = ConfigNormalizer(policy)
    result = normalizer.apply(data)
    assert result == {"key": "value", "keep": "data"}

def test_config_loader_with_policy_overrides():
    """Test ConfigLoader - policy_overrides 사용"""
    yaml_content = """
key: value
    """
    # drop_blanks를 false로 오버라이드
    result = ConfigLoader.load(
        yaml_content,
        policy_overrides={"drop_blanks": False}
    )
    assert "key" in result

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
