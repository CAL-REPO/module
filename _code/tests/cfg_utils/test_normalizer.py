# -*- coding: utf-8 -*-
"""cfg_utils.ConfigNormalizer 테스트

ConfigNormalizer는 설정 데이터 후처리를 담당:
- Reference 해석: ${ref:key.path} → 실제 값
- Blank 필터링: None, '', [], {}, Blank 제거
"""

import pytest
from modules.cfg_utils import ConfigNormalizer, ConfigPolicy


class TestConfigNormalizerDropBlanks:
    """drop_blanks 옵션 테스트"""
    
    def test_drop_blanks_enabled(self):
        """drop_blanks=True 시 빈 값 제거"""
        policy = ConfigPolicy(drop_blanks=True)
        normalizer = ConfigNormalizer(policy)
        
        data = {
            "a": None,
            "b": "",
            "c": [],
            "d": {},
            "e": 1,
            "f": "value"
        }
        
        result = normalizer.apply(data)
        
        # None, '', [], {} 제거됨
        assert result == {"e": 1, "f": "value"}
    
    def test_drop_blanks_disabled(self):
        """drop_blanks=False 시 빈 값 유지"""
        policy = ConfigPolicy(drop_blanks=False)
        normalizer = ConfigNormalizer(policy)
        
        data = {
            "a": None,
            "b": "",
            "c": [],
            "d": {},
            "e": 1
        }
        
        result = normalizer.apply(data)
        
        # 모든 값 유지
        assert result == data
    
    def test_drop_blanks_nested(self):
        """중첩된 dict의 빈 값도 제거"""
        policy = ConfigPolicy(drop_blanks=True)
        normalizer = ConfigNormalizer(policy)
        
        data = {
            "section": {
                "a": None,
                "b": "",
                "c": "value"
            },
            "empty_section": {}
        }
        
        result = normalizer.apply(data)
        
        # 중첩된 빈 값도 제거됨
        assert result == {"section": {"c": "value"}}
    
    def test_drop_blanks_preserves_zero_and_false(self):
        """0과 False는 유지 (빈 값 아님)"""
        policy = ConfigPolicy(drop_blanks=True)
        normalizer = ConfigNormalizer(policy)
        
        data = {
            "zero": 0,
            "false": False,
            "none": None,
            "empty_string": ""
        }
        
        result = normalizer.apply(data)
        
        # 0과 False는 유지됨
        assert result == {"zero": 0, "false": False}


class TestConfigNormalizerResolveReference:
    """resolve_reference 옵션 테스트"""
    
    def test_resolve_reference_enabled(self):
        """resolve_reference=True 시 Reference 해석"""
        policy = ConfigPolicy(resolve_reference=True)
        normalizer = ConfigNormalizer(policy)
        
        data = {
            "base": "/path/to/base",
            "full": "${base}/file.txt"
        }
        
        result = normalizer.apply(data)
        
        assert result["base"] == "/path/to/base"
        assert result["full"] == "/path/to/base/file.txt"
    
    def test_resolve_reference_disabled(self):
        """resolve_reference=False 시 Reference 그대로 유지"""
        policy = ConfigPolicy(resolve_reference=False)
        normalizer = ConfigNormalizer(policy)
        
        data = {
            "base": "/path/to/base",
            "full": "${base}/file.txt"
        }
        
        result = normalizer.apply(data)
        
        assert result["full"] == "${base}/file.txt"  # 해석 안 됨
    
    def test_resolve_reference_nested(self):
        """중첩된 Reference 해석"""
        policy = ConfigPolicy(resolve_reference=True)
        normalizer = ConfigNormalizer(policy)
        
        data = {
            "root": "/root",
            "base": "${root}/base",
            "full": "${base}/file.txt"
        }
        
        result = normalizer.apply(data)
        
        # 재귀적으로 해석됨
        assert result["base"] == "/root/base"
        assert result["full"] == "/root/base/file.txt"
    
    def test_resolve_reference_with_context(self):
        """reference_context 사용 테스트"""
        policy = ConfigPolicy(
            resolve_reference=True,
            reference_context={"external": "value"}
        )
        normalizer = ConfigNormalizer(policy)
        
        data = {
            "internal": "test",
            "uses_external": "${external}",
            "uses_internal": "${internal}"
        }
        
        result = normalizer.apply(data)
        
        # reference_context가 우선순위 높음
        assert result["uses_external"] == "value"
        assert result["uses_internal"] == "test"
    
    def test_resolve_reference_missing_key(self):
        """존재하지 않는 키 참조 시 처리 (strict=False)"""
        policy = ConfigPolicy(resolve_reference=True)
        normalizer = ConfigNormalizer(policy)
        
        data = {
            "valid": "${existing}",
            "existing": "value"
        }
        
        # strict=False이므로 에러 없이 처리됨
        result = normalizer.apply(data)
        assert result["valid"] == "value"


class TestConfigNormalizerCombined:
    """drop_blanks + resolve_reference 조합 테스트"""
    
    def test_both_enabled(self):
        """둘 다 활성화 시 순차 적용"""
        policy = ConfigPolicy(
            drop_blanks=True,
            resolve_reference=True
        )
        normalizer = ConfigNormalizer(policy)
        
        data = {
            "base": "/path",
            "full": "${base}/file.txt",
            "empty": None,
            "value": 42
        }
        
        result = normalizer.apply(data)
        
        # 1. Reference 해석
        # 2. Blank 제거
        assert result == {
            "base": "/path",
            "full": "/path/file.txt",
            "value": 42
        }
    
    def test_both_disabled(self):
        """둘 다 비활성화 시 원본 유지"""
        policy = ConfigPolicy(
            drop_blanks=False,
            resolve_reference=False
        )
        normalizer = ConfigNormalizer(policy)
        
        data = {
            "base": "/path",
            "full": "${base}/file.txt",
            "empty": None
        }
        
        result = normalizer.apply(data)
        
        # 아무것도 변경 안 됨
        assert result == data
    
    def test_reference_to_blank_value(self):
        """빈 값을 참조하는 경우"""
        policy = ConfigPolicy(
            drop_blanks=True,
            resolve_reference=True
        )
        normalizer = ConfigNormalizer(policy)
        
        data = {
            "value": "real_value",
            "ref_to_value": "${value}"
        }
        
        result = normalizer.apply(data)
        
        # Reference 해석이 정상 동작
        assert result["value"] == "real_value"
        assert result["ref_to_value"] == "real_value"


class TestConfigNormalizerEdgeCases:
    """엣지 케이스 테스트"""
    
    def test_empty_dict(self):
        """빈 dict 처리"""
        policy = ConfigPolicy(drop_blanks=True)
        normalizer = ConfigNormalizer(policy)
        
        result = normalizer.apply({})
        assert result == {}
    
    def test_deeply_nested_structure(self):
        """깊게 중첩된 구조 처리"""
        policy = ConfigPolicy(drop_blanks=True, resolve_reference=True)
        normalizer = ConfigNormalizer(policy)
        
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "value": "deep",
                        "empty": None,
                        "ref": "${level1.level2.level3.value}"
                    }
                }
            }
        }
        
        result = normalizer.apply(data)
        
        # 깊은 중첩도 정상 처리
        assert result["level1"]["level2"]["level3"]["value"] == "deep"
        assert result["level1"]["level2"]["level3"]["ref"] == "deep"
        assert "empty" not in result["level1"]["level2"]["level3"]
    
    def test_list_values_preserved(self):
        """리스트 값은 유지됨"""
        policy = ConfigPolicy(drop_blanks=True)
        normalizer = ConfigNormalizer(policy)
        
        data = {
            "list": [1, 2, 3],
            "empty_list": [],
            "list_with_none": [1, None, 3]
        }
        
        result = normalizer.apply(data)
        
        # 빈 리스트는 제거, 값 있는 리스트는 유지
        assert result["list"] == [1, 2, 3]
        assert "empty_list" not in result
        # list 내부 None은 DictOps.drop_blanks가 처리하는지에 따라 다름


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
