"""
Define policies for configuring the logging subsystem.

The :class:`LogPolicy` encapsulates all configuration required for the
``LogManager`` to set up file handling, rotation, retention and optional
notifications.  Policies are defined as Pydantic models which allows
validation and default values.  The :class:`LogPolicy` also exposes helper
properties for computing the directory path for logs and integrates with the
refactored ``fso_utils`` package for filesystem operations.

Additionally this module includes helper class methods to load a policy
definition from YAML or JSON files via the ``structured_io`` package.  This
allows configuration to be maintained in external files rather than hard
coding values in code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Literal, Type, Any

from pydantic import BaseModel, Field, model_validator

# Import FSO classes from the top‑level fso_utils package.  The refactor
# consolidates the exports in ``fso_utils.__all__`` for backwards
# compatibility so consumers no longer need to know the internal module
# structure.
from fso_utils import (
    FSONamePolicy,
    FSOOpsPolicy,
    ExistencePolicy,
    FSOOps,
)

import path_utils

# Optionally import structured_io for config loading/saving.  These imports
# are inside a try/except to avoid raising ImportError when the module is
# unavailable (e.g. when consumers do not use the file loading helpers).
try:
    from structured_io import (
        yaml_fileio,
        json_fileio,
        BaseParserPolicy,
        BaseDumperPolicy,
    )
except Exception:
    # structured_io is optional; file loading helpers will raise if used
    yaml_fileio = json_fileio = BaseParserPolicy = BaseDumperPolicy = None  # type: ignore


class NotifierPolicy(BaseModel):
    """External notification configuration.

    When enabled a :class:`~log_utils.notifier.LogNotifier` will be created
    automatically to send alerts via email or Slack when errors occur within
    a managed context.
    """

    enabled: bool = Field(False, description="외부 알림 기능 활성화 여부")
    email_host: Optional[str] = None
    email_port: int = 587
    email_sender: Optional[str] = None
    email_password: Optional[str] = None
    email_recipient: Optional[str] = None
    slack_webhook_url: Optional[str] = None


class LogPolicy(BaseModel):
    """Unified logging configuration.

    This policy defines how and where log files are stored and how they are
    rotated and retained.  It also optionally enables the built–in
    :class:`~log_utils.notifier.LogNotifier` by setting ``use_notifier`` and
    providing a nested :class:`NotifierPolicy`.
    """

    # -----------------------------
    # ⚙️ Basic logging settings
    # -----------------------------
    enabled: bool = Field(True, description="로그 활성화 여부")
    level: str = Field("INFO", description="로그 레벨")
    encoding: str = Field("utf-8", description="로그 파일 인코딩")
    diagnose: bool = Field(True, description="예외 발생 시 진단 출력 여부")
    backtrace: bool = Field(True, description="traceback 상세 출력 여부")
    enqueue: bool = Field(True, description="멀티프로세스 안전 큐 사용 여부")

    # -----------------------------
    #  File/directory settings
    # -----------------------------
    base_dir: Path = Field(
        default_factory=path_utils.downloads,
        description="로그 기본 디렉터리"
    )
    dir_name: str = Field("Default", description="로그 디렉터리 이름")

    # -----------------------------
    #  FSO settings
    # -----------------------------
    file_name_policy: FSONamePolicy = Field(
        default_factory=lambda: FSONamePolicy(
            as_type="file",
            name="log",
            extension="log",
            tail_mode="datetime_counter",
            ensure_unique=True,
        ), # pyright: ignore[reportCallIssue]
        description="파일명 생성 정책"
    )

    fso_policy: FSOOpsPolicy = Field(
        default_factory=lambda: FSOOpsPolicy(
            as_type="file",
            exist=ExistencePolicy(create_if_missing=True), # pyright: ignore[reportCallIssue]
        ),
        description="파일/디렉터리 생성 및 존재 정책"
    )

    # -----------------------------
    # ♻️ Rotation / retention / compression settings
    # -----------------------------
    rotation: str = Field("1 day", description="로그 회전 주기")
    retention: Optional[str | int] = Field(None, description="로그 보존 기간 또는 개수")
    compression: Optional[Literal["zip", "tar", "gz", "bz2", "xz", "lzma", None]] = Field(
        None, description="로그 파일 회전 시 적용할 압축 형식"
    )

    # -----------------------------
    #  Notification settings
    # -----------------------------
    use_notifier: bool = Field(False, description="LogNotifier 자동 활성화 여부")
    notifier_policy: NotifierPolicy = Field(
        default_factory=lambda: NotifierPolicy(enabled=False),
        description="외부 알림 설정"
    )

    # -----------------------------
    # ✅ Post validation
    # -----------------------------
    @model_validator(mode="after")
    def validate_dir(self) -> "LogPolicy":
        """Ensure the log directory exists when logging is enabled."""
        if self.enabled:
            dir_path = self.dir_path
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
        return self

    # -----------------------------
    #  Utility properties
    # -----------------------------
    @property
    def dir_path(self) -> Path:
        """Return the absolute path to the log directory.

        The path is derived by combining ``base_dir`` and ``dir_name`` and then
        passing it through :class:`FSOOps` to honour the configured
        :class:`FSOOpsPolicy`.  Missing directories will be created when
        ``create_if_missing`` is set in the policy.
        """
        ops = FSOOps(
            self.base_dir / self.dir_name,
            policy=FSOOpsPolicy(as_type="dir", exist=ExistencePolicy(create_if_missing=True)), # pyright: ignore[reportCallIssue]
        )
        return ops.path

    # -----------------------------
    #  File loading helpers
    # -----------------------------
    @classmethod
    def from_yaml(
        cls: Type["LogPolicy"],
        path: str | Path,
        *,
        parser_policy: BaseParserPolicy | None = None, # pyright: ignore[reportInvalidTypeForm]
    ) -> "LogPolicy":
        """Load a logging policy from a YAML configuration file.

        This method leverages the ``structured_io`` package to parse a YAML
        document from disk.  Environment variables, ``!include`` directives and
        placeholder interpolation are supported through the parser policy.

        Parameters
        ----------
        path: str | Path
            The path to the YAML file containing the policy definition.
        parser_policy: BaseParserPolicy | None
            Optional parser policy to control include/placeholder behaviour.

        Returns
        -------
        LogPolicy
            A new LogPolicy instance constructed from the contents of the
            configuration file.
        """
        if yaml_fileio is None:
            raise ImportError("structured_io is required to use from_yaml")
        fileio = yaml_fileio(str(path), parser_policy=parser_policy)
        data: Any = fileio.read()
        return cls.model_validate(data)  # type: ignore[call-arg]

    @classmethod
    def from_json(
        cls: Type["LogPolicy"],
        path: str | Path,
        *,
        parser_policy: BaseParserPolicy | None = None, # pyright: ignore[reportInvalidTypeForm]
    ) -> "LogPolicy":
        """Load a logging policy from a JSON configuration file.

        Like :meth:`from_yaml` but for JSON documents.  Note that JSON files
        do not support ``!include`` directives.  Placeholder interpolation and
        environment variable substitution can still be controlled via the
        parser policy.
        """
        if json_fileio is None:
            raise ImportError("structured_io is required to use from_json")
        fileio = json_fileio(str(path), parser_policy=parser_policy)
        data: Any = fileio.read()
        return cls.model_validate(data)  # type: ignore[call-arg]

    # -----------------------------
    #  File saving helpers
    # -----------------------------
    def to_yaml(
        self,
        path: str | Path,
        *,
        dumper_policy: BaseDumperPolicy | None = None, # pyright: ignore[reportInvalidTypeForm]
    ) -> Path:
        """Serialize this policy to a YAML file using ``structured_io``.

        Parameters
        ----------
        path: str | Path
            Destination file path where the YAML should be written.
        dumper_policy: BaseDumperPolicy | None
            Optional dumper policy to control formatting and encoding.

        Returns
        -------
        Path
            The path of the written file.
        """
        if yaml_fileio is None:
            raise ImportError("structured_io is required to use to_yaml")
        # Convert the model to a plain dictionary (not JSON) preserving nested
        # structures.  ``model_dump`` returns built‑in types that are safe to
        # dump directly to YAML.
        # Use Pydantic's JSON mode to ensure all values (e.g. Path objects)
        # are serialisable by the YAML dumper.  Without this conversion
        # PyYAML may fail to represent objects like Path.
        data = self.model_dump(mode="json")
        # Pass the dumper policy through to the file adapter when provided
        fileio = yaml_fileio(str(path), dumper_policy=dumper_policy)  # type: ignore[misc]
        return fileio.write(data)

    def to_json(
        self,
        path: str | Path,
        *,
        dumper_policy: BaseDumperPolicy | None = None, # pyright: ignore[reportInvalidTypeForm]
    ) -> Path:
        """Serialize this policy to a JSON file using ``structured_io``.

        See :meth:`to_yaml` for argument descriptions.
        """
        if json_fileio is None:
            raise ImportError("structured_io is required to use to_json")
        # Convert values to JSON serialisable primitives.  See above.
        data = self.model_dump(mode="json")
        fileio = json_fileio(str(path), dumper_policy=dumper_policy)  # type: ignore[misc]
        return fileio.write(data)

    # -----------------------------
    #  Generic file helpers
    # -----------------------------
    @classmethod
    def from_file(
        cls: Type["LogPolicy"],
        path: str | Path,
        *,
        parser_policy: BaseParserPolicy | None = None, # pyright: ignore[reportInvalidTypeForm]
    ) -> "LogPolicy":
        """
        Construct a :class:`LogPolicy` from a YAML or JSON file.

        This convenience method inspects the file extension of ``path`` to
        determine whether to parse the document as YAML or JSON.  It then
        delegates to :meth:`from_yaml` or :meth:`from_json` accordingly.  A
        parser policy may be supplied to customise placeholder resolution,
        environment variable expansion and include/reference handling when
        supported by the underlying :mod:`structured_io` implementation.

        Parameters
        ----------
        path: str | Path
            Path to the configuration file.  Files ending with ``.yaml`` or
            ``.yml`` are treated as YAML; ``.json`` files are treated as
            JSON.  Any other extension will result in a :class:`ValueError`.
        parser_policy: BaseParserPolicy | None
            Optional parser policy passed through to the specific loader.

        Returns
        -------
        LogPolicy
            A new instance initialised from the file contents.

        Raises
        ------
        ImportError
            If :mod:`structured_io` is not available.
        ValueError
            If the file extension is not recognised as YAML or JSON.
        """
        if yaml_fileio is None or json_fileio is None:
            raise ImportError("structured_io is required to use from_file")
        ext = str(path).lower().split('.')[-1]
        if ext in {"yaml", "yml"}:
            return cls.from_yaml(path, parser_policy=parser_policy)
        if ext == "json":
            return cls.from_json(path, parser_policy=parser_policy)
        raise ValueError(f"Unsupported configuration file extension: .{ext}")

    def to_file(
        self,
        path: str | Path,
        *,
        dumper_policy: BaseDumperPolicy | None = None, # pyright: ignore[reportInvalidTypeForm]
    ) -> Path:
        """
        Write this policy to either a YAML or JSON file depending on extension.

        The destination path's suffix determines the serialisation format.  If
        the suffix is ``.yaml`` or ``.yml`` the policy is written as YAML via
        :meth:`to_yaml`.  When the suffix is ``.json`` the policy is written
        as JSON via :meth:`to_json`.  Any other extension will raise a
        :class:`ValueError`.

        Parameters
        ----------
        path: str | Path
            Destination file path.  The extension dictates the output format.
        dumper_policy: BaseDumperPolicy | None
            Optional dumper policy controlling output formatting.

        Returns
        -------
        Path
            The path of the written file.

        Raises
        ------
        ImportError
            If :mod:`structured_io` is not available.
        ValueError
            If the file extension is not recognised as YAML or JSON.
        """
        if yaml_fileio is None or json_fileio is None:
            raise ImportError("structured_io is required to use to_file")
        ext = str(path).lower().split('.')[-1]
        if ext in {"yaml", "yml"}:
            return self.to_yaml(path, dumper_policy=dumper_policy)
        if ext == "json":
            return self.to_json(path, dumper_policy=dumper_policy)
        raise ValueError(f"Unsupported configuration file extension: .{ext}")