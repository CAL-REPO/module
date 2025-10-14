# structured_io/__init__.py
from .formats.yaml_io import YamlParser, YamlDumper
from .formats.json_io import JsonParser, JsonDumper
from .fileio.structured_fileio import StructuredFileIO
from structured_io.core.base_policy import BaseParserPolicy, BaseDumperPolicy

__all__ = [
    # Policies
    "BaseParserPolicy", "BaseDumperPolicy",
    # Parsers & Dumpers
    "YamlParser", "YamlDumper",
    "JsonParser", "JsonDumper",
    # File I/O
    "StructuredFileIO",
    # Factories
    "yaml_parser", "yaml_dumper", "yaml_fileio",
    "json_parser", "json_dumper", "json_fileio",
]

# --------------------------
# Factory helpers (YAML)
# --------------------------
def yaml_parser(
    *,
    enable_env: bool = True,
    enable_include: bool = True,
    enable_placeholder: bool = True,
    enable_reference: bool = False,
    safe_mode: bool = True,
    encoding: str = "utf-8",
    on_error: str = "raise",
    # dumper-related kept for compatibility (ignored here)
    sort_keys: bool = False,
    default_flow_style: bool = False,
    indent: int = 2,
):
    policy = BaseParserPolicy(
        enable_env=enable_env,
        enable_include=enable_include,
        enable_placeholder=enable_placeholder,
        enable_reference=enable_reference,
        safe_mode=safe_mode,
        encoding=encoding,
        on_error=on_error,
        # kept for compat with old YamlParserPolicy signature
        sort_keys=sort_keys,
        default_flow_style=default_flow_style,
        indent=indent,
    )
    return YamlParser(policy)

def yaml_dumper(
    *,
    encoding: str = "utf-8",
    sort_keys: bool = False,
    indent: int = 2,
    default_flow_style: bool = False,
    allow_unicode: bool = True,
    safe_mode: bool = True,
):
    policy = BaseDumperPolicy(
        encoding=encoding,
        sort_keys=sort_keys,
        indent=indent,
        default_flow_style=default_flow_style,
        allow_unicode=allow_unicode,
        safe_mode=safe_mode,
    )
    return YamlDumper(policy)

def yaml_fileio(
    path: str,
    *,
    parser_policy: BaseParserPolicy | None = None,
    dumper_policy: BaseDumperPolicy | None = None,
):
    parser = YamlParser(parser_policy or BaseParserPolicy()) # pyright: ignore[reportCallIssue]
    dumper = YamlDumper(dumper_policy or BaseDumperPolicy()) # pyright: ignore[reportCallIssue]
    return StructuredFileIO(path, parser, dumper)

# --------------------------
# Factory helpers (JSON)
# --------------------------
def json_parser(
    *,
    enable_env: bool = True,
    enable_placeholder: bool = True,
    enable_reference: bool = False,
    safe_mode: bool = True,  # kept for API parity (json is inherently “safe”)
    encoding: str = "utf-8",
    on_error: str = "raise",
):
    policy = BaseParserPolicy(
        enable_env=enable_env,
        enable_include=False,  # JSON에는 include 비활성화
        enable_placeholder=enable_placeholder,
        enable_reference=enable_reference,
        safe_mode=safe_mode,
        encoding=encoding,
        on_error=on_error,
    ) # pyright: ignore[reportCallIssue]
    return JsonParser(policy)

def json_dumper(
    *,
    encoding: str = "utf-8",
    sort_keys: bool = False,
    indent: int = 2,
    allow_unicode: bool = True,
):
    policy = BaseDumperPolicy(
        encoding=encoding,
        sort_keys=sort_keys,
        indent=indent,
        allow_unicode=allow_unicode,
        default_flow_style=False,
        safe_mode=True,
    )
    return JsonDumper(policy)

def json_fileio(
    path: str,
    *,
    parser_policy: BaseParserPolicy | None = None,
    dumper_policy: BaseDumperPolicy | None = None,
):
    parser = JsonParser(parser_policy or BaseParserPolicy(enable_include=False)) # pyright: ignore[reportCallIssue]
    dumper = JsonDumper(dumper_policy or BaseDumperPolicy()) # pyright: ignore[reportCallIssue]
    return StructuredFileIO(path, parser, dumper)
