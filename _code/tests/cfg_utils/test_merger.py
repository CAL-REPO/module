# -*- coding: utf-8 -*-
"""cfg_utils.Merger Strategy Pattern 테스트

Merger는 타입별로 설정을 병합하는 Strategy Pattern 구현:
- DictMerger: dict → KeyPathDict
- ModelMerger: BaseModel → dict → KeyPathDict
- PathMerger: Path/str → YAML → dict → KeyPathDict
- SequenceMerger: List[Any] → 각 항목 재귀 병합
- MergerFactory: 타입 기반 Merger 선택
"""

import pytest
from pathlib import Path
from pydantic import BaseModel

from modules.cfg_utils.services.merger import (
    BaseMerger,
    DictMerger,
    ModelMerger,
    PathMerger,
    SequenceMerger,
    MergerFactory
)
from modules.keypath_utils import KeyPathDict
from modules.cfg_utils.services.config_loader import ConfigLoader


class TestModel(BaseModel):
    """테스트용 Pydantic 모델"""
    name: str
    value: int


@pytest.fixture
def mock_loader(tmp_path):
    """ConfigLoader 모의 객체 생성"""
    # 빈 dict로 ConfigLoader 생성
    loader = ConfigLoader({})
    return loader


class TestDictMerger:
    """DictMerger 테스트"""
    
    def test_dict_merger_basic(self, mock_loader):
        """기본 dict 병합 테스트"""
        merger = DictMerger(mock_loader)
        data = KeyPathDict({})
        source = {"a": 1, "b": 2}
        
        merger.merge(source, data, deep=True)
        assert data.data == {"a": 1, "b": 2}
    
    def test_dict_merger_deep_merge(self, mock_loader):
        """Deep merge 테스트"""
        merger = DictMerger(mock_loader)
        data = KeyPathDict({"a": {"b": 1}})
        source = {"a": {"c": 2}}
        
        merger.merge(source, data, deep=True)
        assert data.data == {"a": {"b": 1, "c": 2}}
    
    def test_dict_merger_shallow_merge(self, mock_loader):
        """Shallow merge 테스트"""
        merger = DictMerger(mock_loader)
        data = KeyPathDict({"a": {"b": 1}})
        source = {"a": {"c": 2}}
        
        merger.merge(source, data, deep=False)
        assert data.data == {"a": {"c": 2}}  # 덮어씀


class TestModelMerger:
    """ModelMerger 테스트"""
    
    def test_model_merger_basic(self, mock_loader):
        """기본 BaseModel 병합 테스트"""
        merger = ModelMerger(mock_loader)
        data = KeyPathDict({})
        source = TestModel(name="test", value=42)
        
        merger.merge(source, data, deep=True)
        assert data.data == {"name": "test", "value": 42}
    
    def test_model_merger_drops_none(self, mock_loader):
        """None 값 제거 테스트"""
        from pydantic import Field
        
        class TestModelWithNone(BaseModel):
            name: str
            value: int | None = None
        
        merger = ModelMerger(mock_loader)
        data = KeyPathDict({})
        source = TestModelWithNone(name="test", value=None)
        
        merger.merge(source, data, deep=True)
        # model_to_dict의 drop_none=True로 None 제거됨
        assert "value" not in data.data or data.data.get("value") is None


class TestPathMerger:
    """PathMerger 테스트"""
    
    def test_path_merger_from_file(self, mock_loader, tmp_path):
        """파일에서 YAML 로드 테스트"""
        # YAML 파일 생성
        config_file = tmp_path / "config.yaml"
        config_file.write_text("name: test\nvalue: 42", encoding="utf-8")
        
        merger = PathMerger(mock_loader)
        data = KeyPathDict({})
        
        merger.merge(str(config_file), data, deep=True)
        assert data.data == {"name": "test", "value": 42}
    
    def test_path_merger_from_path_object(self, mock_loader, tmp_path):
        """Path 객체에서 로드 테스트"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("key: value", encoding="utf-8")
        
        merger = PathMerger(mock_loader)
        data = KeyPathDict({})
        
        merger.merge(config_file, data, deep=True)
        assert data.data == {"key": "value"}
    
    def test_path_merger_from_yaml_string(self, mock_loader):
        """YAML 문자열에서 로드 테스트"""
        merger = PathMerger(mock_loader)
        data = KeyPathDict({})
        yaml_str = "name: test\nvalue: 42"
        
        merger.merge(yaml_str, data, deep=True)
        assert data.data == {"name": "test", "value": 42}
    
    def test_path_merger_empty_dict(self, mock_loader, tmp_path):
        """빈 dict 반환 시 병합 안 함"""
        # 빈 YAML 파일
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("", encoding="utf-8")
        
        merger = PathMerger(mock_loader)
        data = KeyPathDict({"existing": "data"})
        
        merger.merge(str(config_file), data, deep=True)
        # 빈 dict는 병합 안 됨
        assert data.data == {"existing": "data"}


class TestSequenceMerger:
    """SequenceMerger 테스트"""
    
    def test_sequence_merger_multiple_dicts(self, mock_loader):
        """여러 dict 순차 병합 테스트"""
        merger = SequenceMerger(mock_loader)
        data = KeyPathDict({})
        sources = [
            {"a": 1},
            {"b": 2},
            {"c": 3}
        ]
        
        merger.merge(sources, data, deep=True)
        assert data.data == {"a": 1, "b": 2, "c": 3}
    
    def test_sequence_merger_override_order(self, mock_loader):
        """병합 순서에 따른 오버라이드 테스트"""
        merger = SequenceMerger(mock_loader)
        data = KeyPathDict({})
        sources = [
            {"key": "first"},
            {"key": "second"},
            {"key": "third"}
        ]
        
        merger.merge(sources, data, deep=True)
        assert data.data["key"] == "third"  # 마지막 것이 우선
    
    def test_sequence_merger_mixed_types(self, mock_loader, tmp_path):
        """다양한 타입 혼합 병합 테스트"""
        # YAML 파일 생성
        config_file = tmp_path / "config.yaml"
        config_file.write_text("from_file: true", encoding="utf-8")
        
        merger = SequenceMerger(mock_loader)
        data = KeyPathDict({})
        sources = [
            {"from_dict": 1},
            TestModel(name="test", value=42),
            str(config_file)
        ]
        
        merger.merge(sources, data, deep=True)
        assert data.data["from_dict"] == 1
        assert data.data["name"] == "test"
        assert data.data["value"] == 42
        assert data.data["from_file"] is True


class TestMergerFactory:
    """MergerFactory 테스트"""
    
    def test_factory_returns_dict_merger(self, mock_loader):
        """dict → DictMerger 반환"""
        merger = MergerFactory.get({"key": "value"}, mock_loader)
        assert isinstance(merger, DictMerger)
    
    def test_factory_returns_model_merger(self, mock_loader):
        """BaseModel → ModelMerger 반환"""
        model = TestModel(name="test", value=42)
        merger = MergerFactory.get(model, mock_loader)
        assert isinstance(merger, ModelMerger)
    
    def test_factory_returns_path_merger_for_string(self, mock_loader):
        """str → PathMerger 반환"""
        merger = MergerFactory.get("config.yaml", mock_loader)
        assert isinstance(merger, PathMerger)
    
    def test_factory_returns_path_merger_for_path(self, mock_loader):
        """Path → PathMerger 반환"""
        merger = MergerFactory.get(Path("config.yaml"), mock_loader)
        assert isinstance(merger, PathMerger)
    
    def test_factory_returns_sequence_merger(self, mock_loader):
        """List → SequenceMerger 반환"""
        merger = MergerFactory.get([{"a": 1}, {"b": 2}], mock_loader)
        assert isinstance(merger, SequenceMerger)
    
    def test_factory_raises_for_unsupported_type(self, mock_loader):
        """지원하지 않는 타입 → TypeError"""
        with pytest.raises(TypeError, match="Unsupported config input"):
            MergerFactory.get(123, mock_loader)
    
    def test_factory_string_not_sequence(self, mock_loader):
        """문자열은 Sequence지만 PathMerger로 처리"""
        merger = MergerFactory.get("test string", mock_loader)
        # 문자열은 Sequence이지만 PathMerger로 처리됨
        assert isinstance(merger, PathMerger)


class TestMergerIntegration:
    """Merger 통합 테스트"""
    
    def test_merger_with_config_loader(self, tmp_path):
        """ConfigLoader와 Merger 통합 테스트"""
        # 여러 파일 생성
        base = tmp_path / "base.yaml"
        base.write_text("base: true\nvalue: 1", encoding="utf-8")
        
        prod = tmp_path / "prod.yaml"
        prod.write_text("prod: true\nvalue: 2", encoding="utf-8")
        
        # ConfigLoader.load()로 병합
        from modules.cfg_utils import ConfigLoader
        config = ConfigLoader.load([base, prod])
        
        assert config["base"] is True
        assert config["prod"] is True
        assert config["value"] == 2  # prod가 덮어씀


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
