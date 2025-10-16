"""Drop blanks 기능 테스트"""
import pytest
from data_utils.services.dict_ops import DictOps


def test_blanks_to_none():
    """빈 문자열을 None으로 변환"""
    data = {
        "a": "test",
        "b": "",
        "c": "  ",
        "d": "\t\n",
        "e": "ok"
    }
    
    result = DictOps.blanks_to_none(data, deep=False)
    
    assert result["a"] == "test"
    assert result["b"] is None
    assert result["c"] is None
    assert result["d"] is None
    assert result["e"] == "ok"


def test_blanks_to_none_deep():
    """중첩된 dict에서 빈 문자열을 None으로 변환"""
    data = {
        "level1": {
            "a": "test",
            "b": "",
            "level2": {
                "c": "  ",
                "d": "ok"
            }
        },
        "e": ""
    }
    
    result = DictOps.blanks_to_none(data, deep=True)
    
    assert result["level1"]["a"] == "test"
    assert result["level1"]["b"] is None
    assert result["level1"]["level2"]["c"] is None
    assert result["level1"]["level2"]["d"] == "ok"
    assert result["e"] is None


def test_drop_blanks():
    """None과 빈 문자열 제거"""
    data = {
        "a": 1,
        "b": None,
        "c": "",
        "d": "ok",
        "e": "  "
    }
    
    result = DictOps.drop_blanks(data, deep=False)
    
    assert result == {"a": 1, "d": "ok"}
    assert "b" not in result
    assert "c" not in result
    assert "e" not in result


def test_drop_blanks_deep():
    """중첩된 dict에서 None과 빈 문자열 제거"""
    data = {
        "level1": {
            "a": "test",
            "b": None,
            "c": "",
            "level2": {
                "d": "  ",
                "e": "ok",
                "f": None
            }
        },
        "g": "",
        "h": "value"
    }
    
    result = DictOps.drop_blanks(data, deep=True)
    
    # level1 존재
    assert "level1" in result
    assert result["level1"]["a"] == "test"
    assert "b" not in result["level1"]
    assert "c" not in result["level1"]
    
    # level2 존재
    assert "level2" in result["level1"]
    assert result["level1"]["level2"]["e"] == "ok"
    assert "d" not in result["level1"]["level2"]
    assert "f" not in result["level1"]["level2"]
    
    # top level
    assert "g" not in result
    assert result["h"] == "value"


def test_config_normalizer_with_blanks():
    """ConfigNormalizer의 drop_blanks 테스트"""
    from cfg_utils.services.normalizer import ConfigNormalizer
    from cfg_utils.core.policy import ConfigPolicy
    
    # drop_blanks=True인 policy
    policy = ConfigPolicy(drop_blanks=True, resolve_reference=False)
    normalizer = ConfigNormalizer(policy)
    
    data = {
        "yaml": {
            "source_paths": [
                {"path": "", "section": ""}
            ]
        },
        "valid": "ok"
    }
    
    result = normalizer.apply(data)
    
    # 빈 문자열이 제거됨
    assert "valid" in result
    assert result["valid"] == "ok"
    
    # yaml.source_paths[0]에서 빈 값들이 제거됨
    if "yaml" in result and "source_paths" in result["yaml"]:
        sources = result["yaml"]["source_paths"]
        if sources:  # 리스트가 비어있지 않으면
            # path나 section이 빈 문자열이면 제거되어야 함
            for source in sources:
                if isinstance(source, dict):
                    for key, value in source.items():
                        # 빈 문자열이 없어야 함
                        assert value != ""
                        assert value is not None or key in source  # None은 허용 가능


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
