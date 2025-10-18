"""Policy definitions for the :mod:`cfg_utils` package.

This module defines :class:`ConfigPolicy`, a Pydantic model that
encapsulates all configuration options for :class:`cfg_utils.loader.ConfigLoader` and
:class:`cfg_utils.normalizer.ConfigNormalizer`.  The policy
controls how YAML input is parsed, how configuration values are
merged, and whether blank values and reference placeholders are
processed.
"""

from __future__ import annotations

from typing import Any, Literal, Optional, Union, List
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

# Import the base parser policy from structured_io.  This replaces the
# older YamlParserPolicy used in previous versions of cfg_utils.
from structured_io.core.policy import BaseParserPolicy
from unify_utils.core.policy import KeyPathNormalizePolicy


# ==============================================================================
# SourcePathPolicy - ConfigLoader용 소스 경로 정책
# ==============================================================================



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
    config_loader_path: Optional[Union[str, Path]] = Field(
        default=None,
        description=(
            "Optional path to a YAML configuration file for the ConfigLoader. "
            "If provided, this file will be loaded and merged according to the "
            "specified merge order and mode."
        )
    )
    source_paths: Optional[Union[
        SourcePathPolicy,
        List[SourcePathPolicy]
    ]] = Field(
        default=None,
        description=(
            "ConfigLoader용 소스 파일 경로. 단일 SourcePathPolicy 또는 리스트. "
            "이 필드는 BaseParserPolicy가 아닌 ConfigPolicy에 속합니다."
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

    keypath: KeyPathNormalizePolicy = Field(
        default_factory=lambda: KeyPathNormalizePolicy(
            sep="__",  # ✅ FIX: 프로젝트 관례에 맞춰 "__"로 변경 (source__path → source.path)
            collapse=True,
            accept_dot=True,
            escape_char="\\",
            enable_list_index=False,
            recursive=False,
            strict=False
        ),
        description="KeyPath 해석 정책 (구분자, 이스케이프, 배열 인덱스 등)"
    )

    reference_context: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Reference 해석 시 사용할 추가 context. "
            "PathsLoader.load()로 paths.local.yaml을 로드하여 주입 가능. "
            "예: reference_context=PathsLoader.load()"
        )
    )

    auto_load_paths: bool = Field(
        default=False,
        description=(
            "True이면 CASHOP_PATHS 환경변수에서 paths.local.yaml을 자동 로드하여 "
            "reference_context에 주입합니다. "
            "기본값은 False (명시적 로드 권장)."
        )
    )

    @model_validator(mode='after')
    def _load_paths_if_enabled(self):
        """auto_load_paths=True이면 PathsLoader 실행하여 reference_context 자동 주입."""
        if self.auto_load_paths and not self.reference_context:
            from modules.cfg_utils.services.paths_loader import PathsLoader
            try:
                self.reference_context = PathsLoader.load()
            except FileNotFoundError as e:
                # 경고만 출력하고 계속 진행 (필수 아님)
                print(f"[경고] paths.local.yaml 자동 로드 실패: {e}")
            except Exception as e:
                print(f"[경고] PathsLoader 실행 중 오류: {e}")
        return self

    class Config:
        validate_assignment = True
