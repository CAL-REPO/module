"""
modules.cfg_utils.services.helpers
=================================

Common helper functions for configuration loading and merging:
 - apply_overrides: apply dot-notation overrides to dicts
 - load_source: read from file path or raw YAML string into dict
 - merge_sequence: deep-merge a sequence of sources
 - model_to_dict: convert BaseModel to clean dict
"""
from pathlib import Path
from typing import Any, Dict, Iterable, Union, Optional

from pydantic import BaseModel

from modules.keypath_utils import KeyPathDict
from modules.data_utils.services.dict_ops import DictOps
from modules.structured_io.formats.yaml_io import YamlParser
from modules.unify_utils.normalizers.normalizer_keypath import KeyPathNormalizer
from modules.unify_utils.core.policy import KeyPathNormalizePolicy
from modules.cfg_utils.core.policy import ConfigPolicy


def apply_overrides(
    data: Dict[str, Any],
    overrides: Dict[str, Any],
    separator: str = ".",
    normalizer: Optional[KeyPathNormalizer] = None,
    policy: Optional[ConfigPolicy] = None
) -> Dict[str, Any]:
    """Apply overrides with KeyPath interpretation via normalizer.
    
    SRP 준수: KeyPath 해석은 normalizer로 위임, cfg_utils는 정책만 주입
    
    Args:
        data: Original dictionary to apply overrides to
        overrides: Dict of key-value pairs with dot-notation keys
        separator: Key path separator (default '.'), used to create default normalizer
        normalizer: Optional KeyPathNormalizer for custom interpretation policy
        policy: Optional ConfigPolicy to use policy.keypath for normalizer

    Returns:
        New dict with overrides applied
    
    Examples:
        >>> # 기본 구분자 "."
        >>> apply_overrides({"a": {"b": 1}}, {"a.b": 2})
        {'a': {'b': 2}}
        
        >>> # 커스텀 구분자 "__"
        >>> norm = KeyPathNormalizer(KeyPathNormalizePolicy(sep="__"))
        >>> apply_overrides({"a": {"b": 1}}, {"a__b": 2}, normalizer=norm)
        {'a': {'b': 2}}
        
        >>> # Policy 기반 normalizer
        >>> policy = ConfigPolicy()  # policy.keypath 사용
        >>> apply_overrides({"a": {"b": 1}}, {"a.b": 2}, policy=policy)
        {'a': {'b': 2}}
        
        >>> # 이스케이프 처리
        >>> norm = KeyPathNormalizer(KeyPathNormalizePolicy(sep=".", escape_char="\\"))
        >>> apply_overrides({}, {"a\\.b.c": 1}, normalizer=norm)
        {'a.b': {'c': 1}}
    """
    # normalizer 생성 우선순위: 1) 명시적 normalizer, 2) policy.keypath, 3) 기본값
    if normalizer is None:
        if policy is not None and hasattr(policy, 'keypath'):
            # ConfigPolicy.keypath를 사용
            normalizer = KeyPathNormalizer(policy.keypath)
        else:
            # 기본 정책 생성 (separator 기반)
            normalizer = KeyPathNormalizer(KeyPathNormalizePolicy(
                recursive=False,
                strict=False,
                sep=separator,
                collapse=True,
                accept_dot=True,
                escape_char="\\"
            ))
    
    kp = KeyPathDict(data.copy())
    kp.apply_overrides(overrides, normalizer=normalizer, accept_dot=True)
    return kp.data


def load_source(
    src: Union[Path, str],
    parser: YamlParser
) -> Dict[str, Any]:
    """Load YAML content from file path or raw YAML string into dict.

    Args:
        src: Path to YAML file or raw YAML string
        parser: Initialized YamlParser with policy

    Returns:
        Parsed dict (empty if content is not a dict)
    """
    p = Path(src)
    if p.exists():
        text = p.read_text(encoding=parser.policy.encoding)
        base = p.parent
    else:
        text = str(src)
        base = None
    parsed = parser.parse(text, base_path=base)
    return parsed if isinstance(parsed, dict) else {}


def merge_sequence(
    seq: Iterable[Union[Path, str]],
    parser: YamlParser,
    deep: bool,
    separator: str = "."
) -> Dict[str, Any]:
    """Deep-merge a sequence of YAML sources in order.

    Args:
        seq: Iterable of file paths or raw YAML strings
        parser: Initialized YamlParser with policy
        deep: Whether to use deep merge
        separator: Key path separator for overrides (if needed)

    Returns:
        Merged dict
    """
    merged: Dict[str, Any] = {}
    for item in seq:
        d = load_source(item, parser)
        temp = KeyPathDict(merged, key_separator=separator)
        temp.merge(d, deep=deep)
        merged = temp.data
    return merged


def model_to_dict(
    model: BaseModel,
    drop_none: bool = True
) -> Dict[str, Any]:
    """Convert Pydantic BaseModel to dict, optionally dropping None values.

    Args:
        model: Pydantic model instance
        drop_none: If True, remove None values deeply

    Returns:
        Cleaned dict representation of model
    """
    d: Dict[str, Any] = model.model_dump()
    return DictOps.drop_none(d, deep=True) if drop_none else d
