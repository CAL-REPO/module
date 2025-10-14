"""
ConfigLoader: YAML loader for logging pipeline configuration.
Moved from cfg_utils/loader.py and adapted for logging config.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any, Sequence, Type, TypeVar, Union, Optional
from pydantic import BaseModel, ValidationError
from modules.structured_io.formats.yaml_io import YamlParser
from keypath_utils import KeyPathDict
from .normalizer import ConfigNormalizer
from ..core.policy import ConfigPolicy
T = TypeVar("T", bound=BaseModel)
class ConfigLoader:
    """
    Unified config loader supporting BaseModel, YAML, dict, and runtime overrides.
    """
    def __init__(self, cfg_like: Union[str, Path, dict, BaseModel, Sequence[str | Path]], *, policy: Optional[ConfigPolicy] = None):
        self.policy = policy or ConfigPolicy()
        self.parser = YamlParser(policy=self.policy.yaml_policy)
        self.normalizer = ConfigNormalizer(self.policy)
        self.cfg_like = cfg_like
        self._data = KeyPathDict()
        self._load_and_merge()
    def _load_and_merge(self) -> None:
        deep = self.policy.merge_mode == "deep"
        if isinstance(self.cfg_like, BaseModel):
            self._data.merge(self.cfg_like.model_dump(), deep=deep)
        elif isinstance(self.cfg_like, (str, Path)):
            path = Path(self.cfg_like)
            text = path.read_text(encoding=self.parser.policy.encoding)
            yaml_data = self.parser.parse(text, base_path=path)
            self._data.merge(yaml_data, deep=deep)
        elif isinstance(self.cfg_like, Sequence):
            for p in self.cfg_like:
                path = Path(p)
                text = path.read_text(encoding=self.parser.policy.encoding)
                yaml_data = self.parser.parse(text, base_path=path)
                self._data.merge(yaml_data, deep=deep)
        elif isinstance(self.cfg_like, dict):
            self._data.merge(self.cfg_like, deep=deep)
        else:
            raise TypeError(f"Unsupported config input: {type(self.cfg_like)}")
        normalized = self.normalizer.apply(self._data.data)
        self._data = KeyPathDict(normalized)
    def merge_overrides(self, overrides: dict[str, Any]) -> None:
        deep = self.policy.merge_mode == "deep"
        self._data.merge(overrides, deep=deep)
    def override_path(self, path: str, value: Any) -> None:
        self._data.override(path, value)
    def as_dict(self, section: Optional[str] = None, **overrides: Any) -> dict[str, Any]:
        data = self._data.data.copy()
        if section:
            if section not in data:
                raise KeyError(f"[ConfigLoader] Section '{section}' not found in config")
            data = data[section]
        if overrides:
            deep = self.policy.merge_mode == "deep"
            temp = KeyPathDict(data)
            temp.merge(overrides, deep=deep)
            return temp.data
        return data
    def get_section(self, section: str) -> dict[str, Any]:
        return self.as_dict(section=section)
    def has_section(self, section: str) -> bool:
        return section in self._data.data and isinstance(self._data.data[section], dict)
    def get_root(self) -> dict[str, Any]:
        return self.as_dict(section=None)
    def as_model(self, model: Type[T], section: Optional[str] = None, **overrides: Any) -> T:
        data = self.as_dict(**overrides)
        if section:
            if section not in data:
                raise KeyError(f"[ConfigLoader] Section '{section}' not found in config")
            data = data[section]
        else:
            model_name = model.__name__.lower()
            candidates = []
            if model_name.endswith("policy"):
                base = model_name[:-6]
                candidates.append(base)
                if base.startswith("image"):
                    candidates.append(base[5:])
            if model_name.endswith("config"):
                candidates.append(model_name[:-6])
            candidates.append(model_name)
            section_found = False
            for key in candidates:
                if key and isinstance(data.get(key), dict):
                    data = data[key]
                    section_found = True
                    break
            if not section_found:
                pass
        data = {str(k): v for k, v in data.items()}
        try:
            return model(**data)
        except ValidationError as e:
            raise TypeError(f"[ConfigLoader] Failed to load config as model '{model.__name__}': {e}")
