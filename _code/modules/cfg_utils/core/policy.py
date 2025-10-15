"""Policy definitions for the :mod:`cfg_utils` package.

This module defines :class:`ConfigPolicy`, a Pydantic model that
encapsulates all configuration options for :class:`cfg_utils.loader.ConfigLoader` and
:class:`cfg_utils.normalizer.ConfigNormalizer`.  The policy
controls how YAML input is parsed, how configuration values are
merged, and whether blank values and reference placeholders are
processed.
"""

from __future__ import annotations

from typing import Literal, Optional, Union
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

# Import the base parser policy from structured_io.  This replaces the
# older YamlParserPolicy used in previous versions of cfg_utils.
from structured_io.core.base_policy import BaseParserPolicy


class ConfigPolicy(BaseModel):
    """Pydantic model specifying configuration loading behavior.

    A ``ConfigPolicy`` aggregates several related options:

    * **YAML parsing policy** – delegated to :class:`structured_io.base.base_policy.BaseParserPolicy`.
      Use :attr:`yaml` to customize encoding, environment variable expansion,
      include directives and other YAML parsing rules.

    * **Normalizer options** – :attr:`drop_blanks` toggles removal of
      keys with blank values (``None``, the empty string or the literal
      string ``"None"``) from the resulting configuration; and
      :attr:`resolve_reference` enables resolving reference placeholders
      such as ``${key.path:default}`` via
      :class:`unify_utils.normalizers.reference_resolver.ReferenceResolver`.

    * **Merge options** – :attr:`merge_order` controls the order in
      which data from ``BaseModel`` instances, YAML files and runtime
      overrides are combined; :attr:`merge_mode` selects between deep
      (recursive) and shallow dictionary merges.

    The default policy performs deep merges, resolves references and
    drops blank entries.
    """

    # ------------------------------------------------------------------
    # ConfigLoader 자신의 설정 파일 경로
    # ------------------------------------------------------------------
    config_loader_path: Optional[Union[str, Path]] = Field(
        default=None,
        description="ConfigLoader 정책 파일 경로 (None이면 cfg_utils/configs/config_loader.yaml 사용)"
    )

    # ------------------------------------------------------------------
    # YAML parsing options (delegated)
    # ------------------------------------------------------------------
    loader_config_path: Optional[Union[str, Path]] = Field(
        default=None,
        description=(
            "ConfigLoader 자신의 정책 파일 경로. "
            "None이면 cfg_utils/configs/config_loader.yaml 사용"
        )
    )
    
    yaml: Optional[BaseParserPolicy] = Field(
        default=None,
        description=(
            "Policy governing YAML parsing behavior.  This includes encoding, "
            "environment variable expansion, include directives and other lower‑level rules."
        )
    )
    
    @model_validator(mode='after')
    def _set_yaml_default(self):
        """yaml이 None이면 기본 BaseParserPolicy 할당"""
        if self.yaml is None:
            self.yaml = BaseParserPolicy()
        return self

    # ------------------------------------------------------------------
    # Normalizer options
    # ------------------------------------------------------------------
    drop_blanks: bool = Field(
        default=True,
        description="Whether to drop keys whose values are considered blank (None, empty string or the literal 'None')."
    )
    resolve_reference: bool = Field(
        default=True,
        description="Whether to resolve ${key.path:default} style placeholders using unify_utils.ReferenceResolver."
    )

    # ------------------------------------------------------------------
    # Merge options
    # ------------------------------------------------------------------
    merge_order: Literal["base→yaml→arg"] = Field(
        default="base→yaml→arg",
        description="Order in which BaseModel, YAML files and runtime overrides are merged (default: base→yaml→arg)."
    )
    merge_mode: Literal["deep", "shallow"] = Field(
        default="deep",
        description="Dictionary merge strategy: 'deep' for recursive merging, 'shallow' for one‑level merges."
    )

    class Config:
        validate_assignment = True
