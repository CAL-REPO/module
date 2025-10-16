# -*- coding: utf-8 -*-
"""cfg_utils.helpers 유틸리티 함수 테스트

helpers 모듈의 주요 함수:
- apply_overrides: KeyPath 기반 오버라이드
- load_source: Path/str → dict 로드
- merge_sequence: List[Path] → 순차 병합
- model_to_dict: BaseModel → dict 변환
"""

import pytest
from pathlib import Path
from pydantic import BaseModel

from modules.cfg_utils.services.helpers import (
    apply_overrides,
    load_source,
    merge_sequence,
    model_to_dict
)
from modules.cfg_utils import ConfigPolicy
from modules.structured_io.formats.yaml_io import YamlParser
from modules.structured_io.core.base_policy import BaseParserPolicy


class TestModel(BaseModel):
    """테스트용 Pydantic 모델"""
    name: str
    value: int
    optional: str | None = None


class TestApplyOverrides:
    """apply_overrides 함수 테스트"""
    
    def test_apply_overrides_basic(self):
        """기본 오버라이드 테스트"""
        data = {"a": 1, "b": 2}
        overrides = {"a": 10}
        
        result = apply_overrides(data, overrides)
        
        assert result["a"] == 10
        assert result["b"] == 2
    
    def test_apply_overrides_with_dot_notation(self):
        """dot notation 오버라이드 테스트"""
        data = {"section": {"key": "old"}}
        overrides = {"section.key": "new"}
        
        result = apply_overrides(data, overrides, separator=".")
        
        assert result["section"]["key"] == "new"
    
    def test_apply_overrides_with_double_underscore(self):
        """__ 구분자 오버라이드 테스트 (프로젝트 관례)"""
        data = {"section": {"subsection": {"key": "old"}}}
        overrides = {"section__subsection__key": "new"}
        
        from modules.unify_utils.normalizers.normalizer_keypath import KeyPathNormalizer
        from modules.unify_utils.core.policy import KeyPathNormalizePolicy
        
        normalizer = KeyPathNormalizer(
            KeyPathNormalizePolicy(sep="__", recursive=True, strict=False)
        )
        result = apply_overrides(data, overrides, normalizer=normalizer)
        
        assert result["section"]["subsection"]["key"] == "new"
    
    def test_apply_overrides_with_policy(self):
        """ConfigPolicy를 통한 오버라이드 테스트"""
        data = {"section": {"key": "old"}}
        overrides = {"section__key": "new"}
        
        policy = ConfigPolicy()  # keypath.sep="__" 기본값
        result = apply_overrides(data, overrides, policy=policy)
        
        assert result["section"]["key"] == "new"
    
    def test_apply_overrides_creates_nested_keys(self):
        """존재하지 않는 중첩 키 생성"""
        data = {}
        overrides = {"new__nested__key": "value"}
        
        policy = ConfigPolicy()
        result = apply_overrides(data, overrides, policy=policy)
        
        assert result["new"]["nested"]["key"] == "value"
    
    def test_apply_overrides_preserves_original(self):
        """원본 데이터는 변경하지 않음"""
        original = {"a": 1}
        overrides = {"a": 2}
        
        result = apply_overrides(original, overrides)
        
        assert original["a"] == 1  # 원본 유지
        assert result["a"] == 2


class TestLoadSource:
    """load_source 함수 테스트"""
    
    def test_load_source_from_file(self, tmp_path):
        """파일에서 YAML 로드"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("name: test\nvalue: 42", encoding="utf-8")
        
        parser = YamlParser(policy=BaseParserPolicy())
        result = load_source(config_file, parser)
        
        assert result == {"name": "test", "value": 42}
    
    def test_load_source_from_string_path(self, tmp_path):
        """문자열 경로에서 YAML 로드"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("key: value", encoding="utf-8")
        
        parser = YamlParser(policy=BaseParserPolicy())
        result = load_source(str(config_file), parser)
        
        assert result == {"key": "value"}
    
    def test_load_source_from_yaml_string(self):
        """YAML 문자열에서 로드"""
        yaml_str = "name: test\nvalue: 42"
        
        parser = YamlParser(policy=BaseParserPolicy())
        result = load_source(yaml_str, parser)
        
        assert result == {"name": "test", "value": 42}
    
    def test_load_source_returns_empty_dict_for_non_dict(self):
        """dict가 아닌 결과는 빈 dict 반환"""
        yaml_str = "- item1\n- item2"  # list
        
        parser = YamlParser(policy=BaseParserPolicy())
        result = load_source(yaml_str, parser)
        
        assert result == {}  # 빈 dict 반환
    
    def test_load_source_with_base_path(self, tmp_path):
        """base_path가 parser에 전달됨"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("key: value", encoding="utf-8")
        
        parser = YamlParser(policy=BaseParserPolicy())
        result = load_source(config_file, parser)
        
        # base_path는 parser 내부에서 사용됨 (include 등)
        assert result == {"key": "value"}


class TestMergeSequence:
    """merge_sequence 함수 테스트"""
    
    def test_merge_sequence_basic(self, tmp_path):
        """여러 파일 순차 병합"""
        base = tmp_path / "base.yaml"
        base.write_text("a: 1\nb: 2", encoding="utf-8")
        
        prod = tmp_path / "prod.yaml"
        prod.write_text("b: 20\nc: 3", encoding="utf-8")
        
        parser = YamlParser(policy=BaseParserPolicy())
        result = merge_sequence([base, prod], parser, deep=True)
        
        assert result == {"a": 1, "b": 20, "c": 3}
    
    def test_merge_sequence_deep_merge(self, tmp_path):
        """Deep merge 테스트"""
        base = tmp_path / "base.yaml"
        base.write_text("section:\n  a: 1\n  b: 2", encoding="utf-8")
        
        prod = tmp_path / "prod.yaml"
        prod.write_text("section:\n  b: 20\n  c: 3", encoding="utf-8")
        
        parser = YamlParser(policy=BaseParserPolicy())
        result = merge_sequence([base, prod], parser, deep=True)
        
        assert result["section"] == {"a": 1, "b": 20, "c": 3}
    
    def test_merge_sequence_shallow_merge(self, tmp_path):
        """Shallow merge 테스트"""
        base = tmp_path / "base.yaml"
        base.write_text("section:\n  a: 1\n  b: 2", encoding="utf-8")
        
        prod = tmp_path / "prod.yaml"
        prod.write_text("section:\n  b: 20\n  c: 3", encoding="utf-8")
        
        parser = YamlParser(policy=BaseParserPolicy())
        result = merge_sequence([base, prod], parser, deep=False)
        
        # shallow merge는 section 전체를 덮어씀
        assert result["section"] == {"b": 20, "c": 3}
    
    def test_merge_sequence_order_matters(self, tmp_path):
        """병합 순서가 중요함"""
        first = tmp_path / "first.yaml"
        first.write_text("key: first", encoding="utf-8")
        
        second = tmp_path / "second.yaml"
        second.write_text("key: second", encoding="utf-8")
        
        third = tmp_path / "third.yaml"
        third.write_text("key: third", encoding="utf-8")
        
        parser = YamlParser(policy=BaseParserPolicy())
        result = merge_sequence([first, second, third], parser, deep=True)
        
        assert result["key"] == "third"  # 마지막이 우선
    
    def test_merge_sequence_empty_list(self):
        """빈 리스트는 빈 dict 반환"""
        parser = YamlParser(policy=BaseParserPolicy())
        result = merge_sequence([], parser, deep=True)
        
        assert result == {}


class TestModelToDict:
    """model_to_dict 함수 테스트"""
    
    def test_model_to_dict_basic(self):
        """기본 변환 테스트"""
        model = TestModel(name="test", value=42, optional="opt")
        result = model_to_dict(model)
        
        assert result == {"name": "test", "value": 42, "optional": "opt"}
    
    def test_model_to_dict_drops_none_by_default(self):
        """None 값 제거 (기본 동작)"""
        model = TestModel(name="test", value=42, optional=None)
        result = model_to_dict(model, drop_none=True)
        
        # None은 제거됨
        assert "optional" not in result or result["optional"] is None
    
    def test_model_to_dict_keeps_none_when_disabled(self):
        """drop_none=False 시 None 유지"""
        model = TestModel(name="test", value=42, optional=None)
        result = model_to_dict(model, drop_none=False)
        
        assert result["optional"] is None
    
    def test_model_to_dict_nested_model(self):
        """중첩된 모델 변환"""
        class NestedModel(BaseModel):
            inner: TestModel
        
        inner = TestModel(name="inner", value=1, optional=None)
        model = NestedModel(inner=inner)
        
        result = model_to_dict(model, drop_none=True)
        
        assert result["inner"]["name"] == "inner"
        assert result["inner"]["value"] == 1


class TestHelpersIntegration:
    """helpers 함수 통합 테스트"""
    
    def test_load_and_override_workflow(self, tmp_path):
        """실제 워크플로우: load → override"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("section:\n  key: original", encoding="utf-8")
        
        # 1. 로드
        parser = YamlParser(policy=BaseParserPolicy())
        data = load_source(config_file, parser)
        
        # 2. 오버라이드
        policy = ConfigPolicy()
        result = apply_overrides(data, {"section__key": "overridden"}, policy=policy)
        
        assert result["section"]["key"] == "overridden"
    
    def test_merge_multiple_then_override(self, tmp_path):
        """여러 파일 병합 후 오버라이드"""
        base = tmp_path / "base.yaml"
        base.write_text("a: 1\nb: 2", encoding="utf-8")
        
        prod = tmp_path / "prod.yaml"
        prod.write_text("b: 20", encoding="utf-8")
        
        # 1. 병합
        parser = YamlParser(policy=BaseParserPolicy())
        merged = merge_sequence([base, prod], parser, deep=True)
        
        # 2. 오버라이드
        policy = ConfigPolicy()
        result = apply_overrides(merged, {"c": 3}, policy=policy)
        
        assert result == {"a": 1, "b": 20, "c": 3}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
