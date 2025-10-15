# -*- coding: utf-8 -*-
# Tests for cfg_utils module

import pytest
from cfg_utils import ConfigLoader, ConfigNormalizer, ConfigPolicy
from pydantic import BaseModel

class SampleModel(BaseModel):
    key: str
    value: int

def test_config_loader_with_single_file():
    """Test ConfigLoader with a single YAML file."""
    yaml_content = """
    section1:
      key: test
      value: 123
    """
    loader = ConfigLoader(yaml_content)
    result = loader.as_dict(section="section1")
    assert result == {"key": "test", "value": 123}

def test_config_loader_with_multiple_files():
    """Test ConfigLoader with multiple YAML files."""
    yaml_content1 = """
    section1:
      key: test1
      value: 123
    """
    yaml_content2 = """
    section2:
      key: test2
      value: 456
    """
    loader = ConfigLoader([yaml_content1, yaml_content2])
    result = loader.as_dict()
    assert result == {
        "section1": {"key": "test1", "value": 123},
        "section2": {"key": "test2", "value": 456},
    }

def test_config_normalizer():
    """Test ConfigNormalizer functionality."""
    data = {"key": "value", "extra": "remove"}
    policy = ConfigPolicy(resolve_reference=False, drop_blanks=True)
    normalizer = ConfigNormalizer(policy)
    result = normalizer.apply(data)
    assert result == {"key": "value", "extra": "remove"}

def test_config_loader_as_model():
    """Test ConfigLoader loading data as a Pydantic model."""
    yaml_content = """
    section1:
      key: test
      value: 123
    """
    loader = ConfigLoader(yaml_content)
    model = loader.as_model(SampleModel, section="section1")
    assert model.key == "test"
    assert model.value == 123

if __name__ == "__main__":
    pytest.main()
