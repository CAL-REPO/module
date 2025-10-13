# Code Analysis Overview

Generated on 2025-10-13 20:00 UTC.

Total Python files analyzed: 99.

## modules/__init__.py

- **Module docstring:** modules package
- **Imports:** (none)
- **Classes:** (none)
- **Functions:** (none)

## modules/base_utils/convert.py

- **Module docstring:** (none)
- **Imports:** (none)
- **Classes:**
- `BaseConvert` — 기본형(str ↔ bytes) 변환 전담 클래스
    - `to_bytes(text, encoding)`
    - `from_bytes(data, encoding)`
- **Functions:** (none)

## modules/cfg_utils/__init__.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `policy -> ConfigPolicy`, `normalizer -> ConfigNormalizer`, `loader -> ConfigLoader`, `unify_utils -> ReferenceResolver`
- **Classes:** (none)
- **Functions:** (none)

## modules/cfg_utils/loader.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `pathlib -> Path`, `typing -> Any, Sequence, Type, TypeVar, Union, Optional`, `pydantic -> BaseModel, ValidationError`, `yaml_utils.parser -> YamlParser`, `keypath_utils -> KeyPathDict`, `normalizer -> ConfigNormalizer`, `policy -> ConfigPolicy`
- **Classes:**
- `ConfigLoader` — 통합 설정 로더
    - `__init__(self, cfg_like, *, policy)`
    - `_load_and_merge(self)` — 입력 유형에 따라 로딩 및 병합
    - `merge_overrides(self, overrides)` — 런타임 override를 병합 (정책 기반 deep/shallow 반영)
    - `override_path(self, path, value)` — 단일 경로 기반 강제 override
    - `as_dict(self, **overrides)` — 최종 병합 dict 반환
    - `as_model(self, model, **overrides)` — 최종 모델 변환
- **Functions:** (none)

## modules/cfg_utils/normalizer.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `typing -> Any`, `unify_utils.normalizers.reference_resolver -> ReferenceResolver`
- **Classes:**
- `ConfigNormalizer` — Config 데이터 후처리기
    - `__init__(self, policy)`
    - `apply(self, data)`
- **Functions:** (none)

## modules/cfg_utils/policy.py

- **Module docstring:** Policy definitions for the :mod:`cfg_utils` package.
- **Imports:** `__future__ -> annotations`, `typing -> Literal`, `pydantic -> BaseModel, Field`, `structured_io.base.base_policy -> BaseParserPolicy`
- **Classes:**
- `ConfigPolicy` — Pydantic model specifying configuration loading behavior.
- **Functions:** (none)

## modules/color_utils/color_utils.py

- **Module docstring:** modules.color — color helpers (no Pillow dependency)
- **Imports:** `__future__ -> annotations`, `typing -> Any, Tuple, Iterable`
- **Classes:** (none)
- **Functions:**
- `_clamp255(x)`
- `_from_hex(s)`
- `to_rgba(v)` — 허용 입력:

## modules/crawl_refactor/__init__.py

- **Module docstring:** (none)
- **Imports:** `policy -> CrawlPolicy, NavigationPolicy, ScrollPolicy, ExtractorPolicy, WaitPolicy, NormalizationPolicy, NormalizationRule, StoragePolicy, StorageTargetPolicy, HttpSessionPolicy`, `pipeline -> CrawlPipeline`, `fetcher -> HTTPFetcher, DummyFetcher`, `saver -> StorageDispatcher`, `normalizer -> DataNormalizer`, `models -> NormalizedItem, SaveSummary, SavedArtifact`
- **Classes:** (none)
- **Functions:** (none)

## modules/crawl_refactor/extractor.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `typing -> Any, Dict, List, Optional`, `interfaces -> Navigator, ResourceFetcher`, `policy -> CrawlPolicy, ExtractorType`
- **Classes:**
- `DOMExtractor` — (no docstring)
    - `__init__(self, navigator, policy)`
- `JSExtractor` — (no docstring)
    - `__init__(self, navigator, policy)`
- `APIExtractor` — (no docstring)
    - `__init__(self, fetcher, policy)`
- `ExtractorFactory` — (no docstring)
    - `__init__(self, policy, navigator, fetcher)`
    - `create(self)`
- **Functions:** (none)

## modules/crawl_refactor/fetcher.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `typing -> Any, Dict, Optional`, `aiohttp`, `interfaces -> ResourceFetcher`
- **Classes:**
- `DummyFetcher` — (no docstring)
- `HTTPFetcher` — Reusable aiohttp-based fetcher.
    - `__init__(self, *, timeout, session, default_headers)`
- **Functions:** (none)

## modules/crawl_refactor/interfaces.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `typing -> Any, Dict, Optional, Protocol, Sequence, TYPE_CHECKING`
- **Classes:**
- `CrawlDriver` — (no docstring)
- `Navigator` — (no docstring)
- `ResourceFetcher` — (no docstring)
- `CrawlSaver` — (no docstring)
- `ExtractorBase` — (no docstring)
- **Functions:** (none)

## modules/crawl_refactor/models.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `dataclasses -> dataclass, field`, `pathlib -> Path`, `typing -> Any, Dict, Literal, Optional, List`
- **Classes:**
- `NormalizedItem` — (no docstring)
- `SavedArtifact` — (no docstring)
- `SaveSummary` — (no docstring)
    - `flatten(self)`
    - `__getitem__(self, kind)`
- **Functions:** (none)

## modules/crawl_refactor/navigator.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `asyncio`, `interfaces -> CrawlDriver`, `policy -> CrawlPolicy, ScrollStrategy, WaitHook, WaitCondition`
- **Classes:**
- `SeleniumNavigator` — (no docstring)
    - `__init__(self, driver, policy)`
    - `_build_url(self, page, query, extra)`
- **Functions:** (none)

## modules/crawl_refactor/normalizer.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `typing -> Any, Dict, Iterable, List, Sequence`, `models -> NormalizedItem`, `policy -> NormalizationPolicy, NormalizationRule`
- **Classes:**
- `DataNormalizer` — Rule-based normalizer that turns extractor output into NormalizedItem objects.
    - `__init__(self, policy)`
    - `normalize(self, records)`
- **Functions:**
- `_get_by_path(data, path)`

## modules/crawl_refactor/pipeline.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `asyncio`, `inspect`, `json`, `pathlib -> Path`, `typing -> Dict, List, Optional`, `extractor -> ExtractorFactory`, `fetcher -> HTTPFetcher`, `interfaces -> Navigator, ResourceFetcher`, `models -> NormalizedItem, SaveSummary`, `normalizer -> DataNormalizer`, `policy -> CrawlPolicy`, `saver -> StorageDispatcher`
- **Classes:**
- `CrawlPipeline` — Coordinates navigation, extraction, normalization, and persistence.
    - `__init__(self, policy, navigator, *, fetcher)`
    - `_create_fetcher(self)`
    - `_load_session_headers(self)`
- **Functions:** (none)

## modules/crawl_refactor/policy.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `enum -> Enum`, `pathlib -> Path`, `typing -> Dict, List, Optional`, `pydantic -> BaseModel, Field, HttpUrl, model_validator`, `models -> ItemKind`
- **Classes:**
- `ScrollStrategy` — (no docstring)
- `WaitHook` — (no docstring)
- `WaitCondition` — (no docstring)
- `ExtractorType` — (no docstring)
- `NavigationPolicy` — (no docstring)
- `ScrollPolicy` — (no docstring)
- `ExtractorPolicy` — (no docstring)
- `WaitPolicy` — (no docstring)
- `HttpSessionPolicy` — (no docstring)
- `NormalizationRule` — (no docstring)
- `NormalizationPolicy` — (no docstring)
- `StorageTargetPolicy` — (no docstring)
    - `ensure_exists(self)`
- `StoragePolicy` — (no docstring)
    - `target_for(self, kind)`
    - `validate_any(self)`
- `CrawlPolicy` — (no docstring)
- **Functions:**
- `_default_output_root()`

## modules/crawl_refactor/saver.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `asyncio`, `pathlib -> Path`, `typing -> Dict, List, Optional, Sequence`, `fso_utils.core.path_builder -> FSOPathBuilder`, `fso_utils.core.policy -> FSONamePolicy, FSOOpsPolicy, ExistencePolicy`, `fetcher -> HTTPFetcher`, `interfaces -> CrawlSaver, ResourceFetcher`, `models -> NormalizedItem, SavedArtifact, SaveSummary`, `policy -> StoragePolicy`
- **Classes:**
- `StorageDispatcher` — Persist normalized items using StoragePolicy rules.
    - `__init__(self, policy)`
    - `_create_builder(self, target_policy, item)`
    - `_default_extension(kind)`
- **Functions:** (none)

## modules/data_utils/__init__.py

- **Module docstring:** (none)
- **Imports:** `df_ops -> DataFramePolicy, DataFrameOps`, `dict_ops -> DictOps`, `list_ops -> ListOps`, `string_ops -> StringOps`, `types -> PathLike, KeyPath, JsonDict, SectionName, FieldName, GroupedPairDict, MultiValueGroupDict`
- **Classes:** (none)
- **Functions:** (none)

## modules/data_utils/df_ops/__init__.py

- **Module docstring:** (none)
- **Imports:** `df_ops -> DataFrameOps`, `base -> DataFramePolicy`
- **Classes:** (none)
- **Functions:** (none)

## modules/data_utils/df_ops/base.py

- **Module docstring:** (none)
- **Imports:** `typing -> Optional, Dict, Set`, `dataclasses -> dataclass, field`, `pandas`
- **Classes:**
- `DataFramePolicy` — Unified policy controlling DataFrame behaviors.
- `BaseDFMixin` — Base class for all DataFrame mixins.
    - `__init__(self, policy)`
- **Functions:** (none)

## modules/data_utils/df_ops/df_ops.py

- **Module docstring:** Composite DataFrame operations class.
- **Imports:** `typing -> Optional`, `base -> DataFramePolicy`, `mixin_create -> DataFrameCreateMixin`, `mixin_normalize -> DataFrameNormalizeMixin`, `mixin_filter -> DataFrameFilterMixin`, `mixin_update -> DataFrameUpdateMixin`, `mixin_clean -> DataFrameCleanMixin`
- **Classes:**
- `DataFrameOps` — High‑level composite for DataFrame operations.
    - `__init__(self, policy)` — Initialize the composite with an optional policy.
- **Functions:** (none)

## modules/data_utils/df_ops/mixin_clean.py

- **Module docstring:** (none)
- **Imports:** `base -> BaseDFMixin`
- **Classes:**
- `DataFrameCleanMixin` — Mixin for dropping empty rows or columns from a DataFrame.
    - `drop_empty(self, df, axis)` — Drop rows or columns from the DataFrame that contain only missing values.
- **Functions:** (none)

## modules/data_utils/df_ops/mixin_create.py

- **Module docstring:** (none)
- **Imports:** `pandas`, `typing -> Any, List`, `base -> BaseDFMixin`
- **Classes:**
- `DataFrameCreateMixin` — Mixin providing DataFrame creation functionality.
    - `to_dataframe(self, records, columns)` — Create a DataFrame from records, enforcing policy around emptiness.
- **Functions:** (none)

## modules/data_utils/df_ops/mixin_filter.py

- **Module docstring:** (none)
- **Imports:** `base -> BaseDFMixin`
- **Classes:**
- `DataFrameFilterMixin` — Mixin for conditional selection and filtering of DataFrame rows.
    - `select(self, df, condition)` — Select rows from a DataFrame using a query string or boolean mask.
- **Functions:** (none)

## modules/data_utils/df_ops/mixin_normalize.py

- **Module docstring:** (none)
- **Imports:** `base -> BaseDFMixin`
- **Classes:**
- `DataFrameNormalizeMixin` — Mixin for column normalization and alias handling.
    - `normalize_columns(self, df, aliases)` — Rename DataFrame columns using a simple alias mapping.
- **Functions:** (none)

## modules/data_utils/df_ops/mixin_update.py

- **Module docstring:** (none)
- **Imports:** `base -> BaseDFMixin`
- **Classes:**
- `DataFrameUpdateMixin` — Mixin for updating rows in a DataFrame.
    - `update_rows(self, df, where, updates)` — Update values in the DataFrame according to a condition.
- **Functions:** (none)

## modules/data_utils/dict_ops.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `typing -> Any, Callable, Dict, Mapping, Union, List`, `copy`, `boltons.iterutils -> remap`
- **Classes:**
- `DictOps` — Dictionary manipulation utilities based on :func:`boltons.iterutils.remap`.
    - `deep_update(base, patch, *, inplace)` — Recursively merge ``patch`` into ``base``.
    - `rekey(data, mapping_or_func, *, deep)` — Remap the keys of a dictionary using a mapping or callable.
- **Functions:** (none)

## modules/data_utils/format_ops.py

- **Module docstring:** Data format conversion utilities.
- **Imports:** `io -> BytesIO`, `typing -> Any`, `PIL -> Image`, `json`, `yaml`
- **Classes:**
- `FormatOps` — Utility class for converting between different data formats and types.
    - `bytes_to_image(data)` — Convert raw bytes to a Pillow Image object.
    - `image_to_bytes(img, format, **kwargs)` — Serialize a Pillow Image object to raw bytes.
    - `json_to_dict(text)` — Parse a JSON string into a Python dictionary.
    - `dict_to_json(data, **kwargs)` — Serialize a Python dictionary to a JSON-formatted string.
    - `dict_to_yaml(data, **kwargs)` — Serialize a Python dictionary to a YAML-formatted string.
    - `yaml_to_dict(text)` — Parse a YAML string into a Python dictionary.
- **Functions:** (none)

## modules/data_utils/list_ops.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `typing -> Any, List, Iterable`
- **Classes:**
- `ListOps` — Utility functions for list operations.
    - `dedupe_keep_order(seq)` — Remove duplicates from a sequence while preserving the original order.
- **Functions:** (none)

## modules/data_utils/string_ops.py

- **Module docstring:** (none)
- **Imports:** `typing -> List`
- **Classes:**
- `StringOps` — Utility functions for working with strings.
    - `split_str_path(path, sep)` — Split a string path into parts using the given separator.
- **Functions:** (none)

## modules/data_utils/structure_ops.py

- **Module docstring:** Data structure transformation utilities.
- **Imports:** `__future__ -> annotations`, `typing -> Any, Dict, List, Tuple`, `boltons.iterutils -> remap`
- **Classes:**
- `StructureOps` — Static utility class for transforming data structures.
    - `value_to_list(x)` — Normalize the input into a list.
    - `list_to_grouped_pairs(seq, group_size, *, section_index, key_index, value_index, skip_missing)` — Convert a flat list into a grouped pair dictionary.
    - `group_pairs_to_multivalue(grouped_pairs)` — Merge grouped pairs into a multi‑value dictionary.
    - `dict_to_keypath(data, sep)` — Flatten a nested dictionary into a keypath‑based dictionary.
    - `keypath_to_dict(data, sep)` — Restore a nested dictionary from a keypath‑based dictionary.
- **Functions:** (none)

## modules/data_utils/types.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `pathlib -> Path`, `typing -> Any, Dict, List, Optional, Tuple, Union`
- **Classes:** (none)
- **Functions:** (none)

## modules/firefox/__init__.py

- **Module docstring:** (none)
- **Imports:** (none)
- **Classes:** (none)
- **Functions:** (none)

## modules/firefox/config.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `typing -> Optional, Tuple`, `pathlib -> Path`, `pydantic -> Field, BaseModel, field_validator, model_validator`, `log_utils -> LogPolicy, LogManager`, `fso_utils -> FSONamePolicy`
- **Classes:**
- `FirefoxConfig` — (no docstring)
    - `validate_window_size(cls, v)`
    - `validate_paths(self)`
    - `create_logger(self)` — 현재 설정 기반 LogManager 생성
- **Functions:**
- `_default_log_policy()` — Firefox 전용 기본 로그 정책.

## modules/firefox/driver.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `shutil`, `pathlib -> Path`, `typing -> Any, Optional, Union`, `selenium -> webdriver`, `selenium.webdriver.firefox.options -> Options`, `selenium.webdriver.firefox.service -> Service`, `firefox.config -> FirefoxConfig`, `cfg_utils -> ConfigLoader`, `fso_utils.core -> JsonFileIO, FSOOpsPolicy, ExistencePolicy`, `log_utils -> LogContextManager`
- **Classes:**
- `FirefoxDriver` — (no docstring)
    - `__init__(self, cfg_like, **overrides)`
    - `_load_config(cfg_like, **overrides)`
    - `driver(self)`
    - `create(self)`
    - `quit(self)`
    - `_get_driver_path(self)`
    - `_load_session_headers(self)`
    - `_save_session_headers(self)`
    - `__enter__(self)`
    - `__exit__(self, exc_type, exc_val, exc_tb)`
    - `_stop_logging(self, exc_type, exc_val, exc_tb)`
    - `__del__(self)`
- **Functions:** (none)

## modules/font_utils/font_utils.py

- **Module docstring:** modules.font — language-aware font helpers with caching
- **Imports:** `__future__ -> annotations`, `typing -> Dict, List, Optional, Tuple, Union`, `pathlib -> Path`, `functools -> lru_cache`, `yamlutil -> load_yaml`, `paths -> fonts_dir`
- **Classes:** (none)
- **Functions:**
- `is_lang_char(ch, lang)`
- `detect_char_lang(ch)`
- `segment_text_by_lang(text)`
- `_load_font_file_cached(path_str, size)` — 캐시된 폰트 로딩(ImageFont.truetype).
- `_resolve_base_dir(fonts_dir)`
- `_candidate_paths(names, base_dir)`
- `select_font_for_lang(lang, fonts_map, *, size, fonts_dir)` — 언어 코드에 매핑된 후보 리스트에서 로드 가능한 첫 폰트 반환(ImageFont).
- `extract_lang_font_map(cfg_like)`

## modules/fso_utils/__init__.py

- **Module docstring:** (none)
- **Imports:** `core.policy -> FSOOpsPolicy, FSOExplorerPolicy, ExistencePolicy, FileExtensionPolicy, FSOIOPolicy, FSONamePolicy`, `core.ops -> FSOOps`, `core.explorer -> FSOExplorer`, `core.path_builder -> FSOPathBuilder`, `core.interfaces -> IPathBuilderPort, IFileSaver`, `adapters.local_io -> LocalFileSaver, FSOPathBuilderAdapter`
- **Classes:** (none)
- **Functions:** (none)

## modules/fso_utils/adapters/__init__.py

- **Module docstring:** (none)
- **Imports:** `local_io -> LocalFileSaver, FSOPathBuilderAdapter`
- **Classes:** (none)
- **Functions:** (none)

## modules/fso_utils/adapters/local_io.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `pathlib -> Path`, `typing -> Optional`, `asyncio`, `core.interfaces -> IFileSaver, IPathBuilderPort`, `core.policy -> FSONamePolicy, FSOOpsPolicy, ExistencePolicy`, `core.path_builder -> FSOPathBuilder`
- **Classes:**
- `LocalFileSaver` — (no docstring)
- `FSOPathBuilderAdapter` — (no docstring)
    - `build_path(self, base_dir, sub_dir, name_template, ensure_unique, name, extension, kind)`
- **Functions:** (none)

## modules/fso_utils/core/__init__.py

- **Module docstring:** (none)
- **Imports:** `policy -> FSOOpsPolicy, FSOExplorerPolicy, ExistencePolicy, FileExtensionPolicy, FSOIOPolicy, FSONamePolicy`, `ops -> FSOOps`, `path_builder -> FSOPathBuilder`, `io -> JsonFileIO, BinaryFileIO, FileReader, FileWriter`
- **Classes:** (none)
- **Functions:** (none)

## modules/fso_utils/core/explorer.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `pathlib -> Path`, `typing -> List, Optional`, `datetime -> datetime`, `typing -> Union`, `data_utils.types -> PathLike`, `policy -> FSOExplorerPolicy`
- **Classes:**
- `FSOExplorer` — 디렉터리 내 파일/서브디렉터리 탐색기 (정책 기반 필터링 지원)
    - `__init__(self, root, policy)`
    - `_filter(self, paths)`
    - `files(self)` — 정책 기반 파일 목록 반환
    - `dirs(self)` — 정책 기반 디렉터리 목록 반환
    - `all(self)` — 정책 기반 전체 항목 반환 (파일 + 디렉터리)
    - `_scan(self)`
    - `__str__(self)`
- **Functions:** (none)

## modules/fso_utils/core/interfaces.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `typing -> Protocol, Optional`, `pathlib -> Path`
- **Classes:**
- `IPathBuilderPort` — (no docstring)
    - `build_path(self, base_dir, sub_dir, name_template, ensure_unique, name, extension, kind)`
- `IFileSaver` — (no docstring)
- **Functions:** (none)

## modules/fso_utils/core/io.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `json`, `os`, `pathlib -> Path`, `typing -> Any, Optional`, `data_utils.types -> PathLike`, `ops -> FSOOps`, `policy -> FSOOpsPolicy, FSOIOPolicy, ExistencePolicy`
- **Classes:**
- `BaseFileHandler` — (no docstring)
    - `__init__(self, path, policy, encoding, *, require_exists)`
    - `_validate(self)`
- `FileReader` — (no docstring)
    - `__init__(self, path, ops_policy, *, encoding, io_policy)`
    - `read_text(self)`
    - `read_bytes(self)`
- `FileWriter` — (no docstring)
    - `__init__(self, path, *, encoding, atomic, ops_policy, io_policy)`
    - `write_text(self, text)`
    - `write_bytes(self, data)`
- `JsonFileIO` — (no docstring)
    - `__init__(self, path, *, encoding, ops_policy, io_policy)`
    - `read(self)`
    - `write(self, data)`
- `BinaryFileIO` — (no docstring)
    - `__init__(self, path, *, ops_policy, io_policy)`
    - `read(self)`
    - `write(self, data)`
- **Functions:** (none)

## modules/fso_utils/core/name_builder.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `pathlib -> Path`, `datetime -> datetime`, `re`, `policy -> FSONamePolicy`
- **Classes:**
- `FSONameBuilder` — FSONamePolicy를 기반으로 파일 또는 디렉터리 이름을 생성하는 클래스
    - `__init__(self, policy)`
    - `_sanitize(self, s)`
    - `_apply_case(self, s)`
    - `_tail(self, counter)`
    - `build(self, counter)`
    - `build_unique(self, directory)` — 디렉터리 내 중복되지 않는 파일/폴더 경로 생성
- **Functions:** (none)

## modules/fso_utils/core/ops.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `pathlib -> Path`, `typing -> Optional`, `typing -> Union`, `data_utils.types -> PathLike`, `policy -> FSOOpsPolicy`
- **Classes:**
- `FSOOps` — (no docstring)
    - `__init__(self, base, policy)`
    - `exists(self)`
    - `is_file(self)`
    - `is_dir(self)`
    - `__str__(self)`
    - `__fspath__(self)`
    - `__repr__(self)`
- **Functions:** (none)

## modules/fso_utils/core/path_builder.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `pathlib -> Path`, `typing -> Optional`, `copy -> deepcopy`, `name_builder -> FSONameBuilder`, `ops -> FSOOps`, `policy -> FSONamePolicy, FSOOpsPolicy`
- **Classes:**
- `FSOPathBuilder` — FSONameBuilder와 FSOOps를 통합한 고수준 경로 생성기
    - `__init__(self, base_dir, name_policy, ops_policy)`
    - `build(self, **override)` — 정책 기반 파일/디렉터리 경로 생성 (override 가능)
    - `__call__(self, **override)`
- **Functions:** (none)

## modules/fso_utils/core/policy.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `datetime -> datetime`, `pathlib -> Path`, `typing -> List, Optional, Sequence`, `pydantic -> BaseModel, Field`
- **Classes:**
- `FSONamePolicy` — (no docstring)
- `ExistencePolicy` — (no docstring)
- `FileExtensionPolicy` — (no docstring)
- `FSOOpsPolicy` — (no docstring)
    - `apply_to(self, raw)`
- `FSOIOPolicy` — (no docstring)
- `FSOExplorerPolicy` — (no docstring)
- **Functions:** (none)

## modules/fso_utils/utils/__init__.py

- **Module docstring:** (none)
- **Imports:** (none)
- **Classes:** (none)
- **Functions:** (none)

## modules/fso_utils/utils/convert.py

- **Module docstring:** (none)
- **Imports:** `pathlib -> Path`, `typing -> Union`, `json`, `yaml`
- **Classes:**
- `FileConvert` — 파일 단위 객체 저장 및 로드
    - `save_obj(path, data, mode)`
    - `load_obj(path)`
- **Functions:** (none)

## modules/keypath_utils/__init__.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `accessor -> KeyPathAccessor`, `model -> KeyPathDict, KeyPathState`, `policy -> KeyPathStatePolicy`
- **Classes:** (none)
- **Functions:** (none)

## modules/keypath_utils/accessor.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `typing -> Any, Callable, Dict`, `data_utils.types -> KeyPath`, `unify_utils.normalizers.keypath_normalizer -> KeyPathNormalizer, KeyPathNormalizePolicy`
- **Classes:**
- `KeyPathAccessor` — (no docstring)
    - `__init__(self, data)`
    - `get(self, path, default)`
    - `exists(self, path)`
    - `set(self, path, value)`
    - `delete(self, path, ignore_missing)`
    - `ensure(self, path, default_factory)`
- **Functions:** (none)

## modules/keypath_utils/model.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `dataclasses -> dataclass, field`, `typing -> Any, Callable, Mapping, Optional, Dict`, `data_utils.types -> KeyPath`, `policy -> KeyPathStatePolicy`, `accessor -> KeyPathAccessor`, `data_utils.dict_ops -> DictOps`
- **Classes:**
- `KeyPathDict` — (no docstring)
    - `override(self, path, value)`
    - `merge(self, patch, *, deep, inplace)`
    - `rekey(self, mapping_or_func, *, deep)`
- `KeyPathState` — (no docstring)
    - `rename(self, name)`
    - `get(self, path, default)`
    - `exists(self, path)`
    - `set(self, path, value)`
    - `delete(self, path, *, ignore_missing)`
    - `ensure(self, path, default_factory)`
    - `override(self, path, value)`
    - `merge(self, patch, *, path, deep)`
    - `to_dict(self, *, copy)`
- **Functions:** (none)

## modules/keypath_utils/policy.py

- **Module docstring:** (none)
- **Imports:** `pydantic -> BaseModel, Field`
- **Classes:**
- `KeyPathStatePolicy` — (no docstring)
- **Functions:** (none)

## modules/log_utils/__init__.py

- **Module docstring:** (none)
- **Imports:** `manager -> LogManager, DummyLogger`, `policy -> LogPolicy, NotifierPolicy`, `fso_builder -> LogFSOBuilder`, `context_manager -> LogContextManager`, `notifier -> LogNotifier`
- **Classes:** (none)
- **Functions:** (none)

## modules/log_utils/context_manager.py

- **Module docstring:** Context manager for automatic logger lifecycle management.
- **Imports:** `__future__ -> annotations`, `traceback`, `typing -> Optional, Type, Any`, `types -> TracebackType`, `manager -> LogManager, DummyLogger`, `policy -> LogPolicy`, `notifier -> LogNotifier`
- **Classes:**
- `LogContextManager` — A context manager that sets up and tears down logging automatically.
    - `__init__(self, name, policy)`
    - `__enter__(self)` — Set up logging and return a logger object.
    - `__exit__(self, exc_type, exc_val, exc_tb)` — Handle exceptions and emit a finish message upon context exit.
- **Functions:** (none)

## modules/log_utils/fso_builder.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `pathlib -> Path`, `fso_utils.core.path_builder -> FSOPathBuilder`, `policy -> LogPolicy`
- **Classes:**
- `LogFSOBuilder` — ✅ FSOPathBuilder 기반 로그 경로 생성기
    - `__init__(self, policy)`
    - `prepare(self, **override)` — ✅ 로그 파일 또는 디렉터리 경로 생성
- **Functions:** (none)

## modules/log_utils/manager.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `pathlib -> Path`, `typing -> Optional`, `loguru -> logger`, `policy -> LogPolicy`, `fso_builder -> LogFSOBuilder`
- **Classes:**
- `DummyLogger` — 로그 비활성화 시 사용하는 Null Object logger
    - `__getattr__(self, _)`
- `LogManager` — ✅ 정책 기반 Loguru 매니저
    - `__init__(self, name, *, policy)`
    - `setup(self)` — 로거 초기화 및 설정 적용
- **Functions:** (none)

## modules/log_utils/notifier.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `smtplib`, `email.mime.text -> MIMEText`, `types -> TracebackType`, `typing -> Type, Optional, Callable`, `traceback`
- **Classes:**
- `LogNotifier` — ✅ LogNotifier
    - `__init__(self, on_notify, *, email_host, email_port, email_sender, email_password, email_recipient, slack_webhook_url)`
    - `_send_email(self, subject, message)`
    - `_send_slack(self, message)`
    - `notify(self, title, exc_type, exc_val, exc_tb)`
- **Functions:** (none)

## modules/log_utils/policy.py

- **Module docstring:** Define policies for configuring the logging subsystem.
- **Imports:** `__future__ -> annotations`, `pathlib -> Path`, `typing -> Optional, Literal, Type, Any`, `pydantic -> BaseModel, Field, model_validator`, `fso_utils -> FSONamePolicy, FSOOpsPolicy, ExistencePolicy, FSOOps`, `path_utils`
- **Classes:**
- `NotifierPolicy` — External notification configuration.
- `LogPolicy` — Unified logging configuration.
    - `validate_dir(self)` — Ensure the log directory exists when logging is enabled.
    - `dir_path(self)` — Return the absolute path to the log directory.
    - `from_yaml(cls, path, *, parser_policy)` — Load a logging policy from a YAML configuration file.
    - `from_json(cls, path, *, parser_policy)` — Load a logging policy from a JSON configuration file.
    - `to_yaml(self, path, *, dumper_policy)` — Serialize this policy to a YAML file using ``structured_io``.
    - `to_json(self, path, *, dumper_policy)` — Serialize this policy to a JSON file using ``structured_io``.
    - `from_file(cls, path, *, parser_policy)` — Construct a :class:`LogPolicy` from a YAML or JSON file.
    - `to_file(self, path, *, dumper_policy)` — Write this policy to either a YAML or JSON file depending on extension.
- **Functions:** (none)

## modules/ocr/ocr.py

- **Module docstring:** modules.ocr — OCR runner (dataclass defaults + provider selector)
- **Imports:** `__future__ -> annotations`, `dataclasses -> dataclass, field, asdict`, `typing -> Any, Dict, List, Optional, Tuple, Union, Iterable`, `pathlib -> Path`, `functools -> lru_cache`, `os`, `json`, `math`, `time`, `numpy`, `modules.datautil -> as_list, is_number_or_symbol_only, strip_specials_keep_alnum_space`, `modules.yamlutil -> section_or_root, load_yaml`, `modules.fileio -> ensure_dir, parent_dir_of`, `pillow.pillow -> load_image, save_image`
- **Classes:**
- `OcrFileDefaults` — (no docstring)
- `OcrProviderDefaults` — (no docstring)
- `OcrPreprocessDefaults` — (no docstring)
- `OcrDefaults` — (no docstring)
- `OCRItem` — (no docstring)
- **Functions:**
- `_ocr_section(cfg_like)` — YAML 경로나 dict 를 받아 ocr 섹션만 추출.
- `_defaults_from_cfg(ocr)`
- `normalize_ocr_cfg(cfg_like)` — 외부 입력을 프로젝트 내부에서 쓰기 좋게 dataclass 로 정규화
- `_bbox_from_quad(quad)`
- `_angle_from_quad(quad)`
- `_ensure_save_dir_for_file(path_like)`
- `_save_ocr_meta_json(meta, *, save_dir, file_name)`
- `_map_lang_to_paddle(code)` — 프로젝트 언어코드 → Paddle lang 코드 간단 매핑
- `_freeze_items(d)`
- `_get_paddle_cached(lang, use_angle_cls, device, extra_items)` — 단일 언어 PaddleOCR 인스턴스 캐시 — PaddleOCR 3.5 호환(device).
- `build_paddle_instances_from_cfg(cfg_like, existing_insts)` — cfg_like(= {"ocr": {...}} / dict / yaml path) 기반으로 언어셋 인스턴스 생성.
- `_run_with_paddle(img_for_ocr, ocr_cfg, insts)` — - poly → bbox/angle 계산
- `filter_ocr_items_drop_numeric_symbol_only(items)` — OCRItem 중 text가 숫자/기호만으로 이루어진 항목은 제거.
- `sanitize_ocr_items_strip_specials(items)` — 각 OCRItem.text에서 특수문자/구두점을 제거.
- `_iou_bbox(a, b)`
- `dedupe_ocr_items_by_overlap(items, *, iou_thresh, prefer_lang_order)` — 박스가 많이 겹치는 항목(같은 위치 다른 언어 인식)을 제거.
- `run_ocr(cfg_like)` — 메인 엔트리:

## modules/path_utils/__init__.py

- **Module docstring:** path_utils package
- **Imports:** `__future__ -> annotations`, `pathlib -> Path`, `os_paths -> OSPath`
- **Classes:** (none)
- **Functions:**
- `home()` — Return the current user's home directory as a ``Path``.
- `downloads()` — Return the default downloads directory as a ``Path``.

## modules/path_utils/os_paths.py

- **Module docstring:** (none)
- **Imports:** `pathlib -> Path`, `os`, `sys`
- **Classes:**
- `OSPath` — (no docstring)
    - `__init__(self)`
    - `home()`
    - `downloads()` — Return the current user's downloads directory as a ``Path``.
- **Functions:** (none)

## modules/pillow_utils/__init__.py

- **Module docstring:** pillow_refactor — SRP-friendly image toolkit.
- **Imports:** `models -> ImageMeta, ImagePipelineResult`, `policy -> ImageSourcePolicy, ImageTargetPolicy, ImageMetaPolicy, ImageProcessingPolicy, ImagePipelinePolicy, OverlayFontPolicy, OverlayTextPolicy, OverlayPolicy`, `io -> ImageReader, ImageWriter`, `processor -> ImageProcessor`, `pipeline -> ImagePipeline`, `overlay -> OverlayRenderer`, `image_loader -> ImageLoaderPolicy, ImageLoader`
- **Classes:** (none)
- **Functions:** (none)

## modules/pillow_utils/image_loader.py

- **Module docstring:** Standalone image loading and optional copy/resizing with metadata and logging.
- **Imports:** `__future__ -> annotations`, `json`, `pathlib -> Path`, `typing -> Optional, Tuple, Any`, `PIL -> Image`, `pydantic -> BaseModel, Field, model_validator`, `fso_utils -> FSONamePolicy, FSOOpsPolicy, ExistencePolicy, FSOPathBuilder`, `log_utils -> LogManager, LogPolicy`
- **Classes:**
- `ImageLoaderPolicy` — Configuration model for loading a single image with optional copy and resize.
    - `_validate_source(self)`
- `ImageLoader` — Loads a single image and optionally copies/resizes it.
    - `__init__(self, policy)`
    - `_build_dest_path(self)` — Construct a destination path for the processed image using fso_utils.
    - `_build_meta_path(self, image_path)` — Construct a path for the metadata JSON file based on the image path.
    - `run(self, image)` — Execute the image load, optional copy/resize, and metadata persistence.
- **Functions:** (none)

## modules/pillow_utils/io.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `json`, `dataclasses -> asdict`, `pathlib -> Path`, `typing -> Optional`, `PIL -> Image, ImageOps`, `fso_utils.core.ops -> FSOOps`, `fso_utils.core.policy -> FSOOpsPolicy, ExistencePolicy, FileExtensionPolicy, FSONamePolicy`, `fso_utils.core.path_builder -> FSOPathBuilder`, `models -> ImageMeta`, `policy -> ImageSourcePolicy, ImageTargetPolicy, ImageMetaPolicy`
- **Classes:**
- `ImageReader` — Load images from disk according to ImageSourcePolicy.
    - `__init__(self, policy)`
    - `load(self)`
    - `_collect_meta(image, path)`
- `ImageWriter` — Persist processed images and metadata using target policies.
    - `__init__(self, target_policy, meta_policy)`
    - `save_image(self, image, base_path)`
    - `save_meta(self, meta, base_path)`
    - `_build_target_path(self, base_path)`
- **Functions:** (none)

## modules/pillow_utils/models.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `dataclasses -> dataclass`, `pathlib -> Path`, `typing -> Optional`, `PIL -> Image`
- **Classes:**
- `ImageMeta` — (no docstring)
- `ImagePipelineResult` — (no docstring)
- **Functions:** (none)

## modules/pillow_utils/overlay.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `pathlib -> Path`, `typing -> Iterable, Tuple`, `PIL -> Image, ImageDraw, ImageFont`, `policy -> OverlayPolicy, OverlayTextPolicy, ImageMetaPolicy`, `io -> ImageReader, ImageWriter`
- **Classes:**
- `OverlayRenderer` — Draws text overlays described by OverlayPolicy.
    - `__init__(self, policy)`
    - `render(self)`
    - `_draw_text(self, draw, cfg)`
    - `_polygon_bbox(points)`
    - `_center_of_bbox(bbox)`
    - `_load_font(self, cfg, size)`
    - `_auto_size(text, bbox, ratio)`
- **Functions:** (none)

## modules/pillow_utils/pipeline.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `pathlib -> Path`, `typing -> Optional`, `io -> ImageReader, ImageWriter`, `models -> ImagePipelineResult`, `policy -> ImagePipelinePolicy`, `processor -> ImageProcessor`
- **Classes:**
- `ImagePipeline` — High level helper that loads → processes → saves an image.
    - `__init__(self, policy)`
    - `run(self)`
- **Functions:** (none)

## modules/pillow_utils/policy.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `pathlib -> Path`, `typing -> List, Optional, Tuple`, `pydantic -> BaseModel, Field, model_validator`
- **Classes:**
- `ImageSourcePolicy` — (no docstring)
- `ImageTargetPolicy` — (no docstring)
- `ImageMetaPolicy` — (no docstring)
- `ImageProcessingPolicy` — (no docstring)
- `ImagePipelinePolicy` — (no docstring)
- `OverlayFontPolicy` — (no docstring)
- `OverlayTextPolicy` — (no docstring)
- `OverlayPolicy` — (no docstring)
    - `validate_texts(self)`
- **Functions:** (none)

## modules/pillow_utils/processor.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `typing -> Tuple`, `PIL -> Image, ImageFilter`, `policy -> ImageProcessingPolicy`
- **Classes:**
- `ImageProcessor` — Applies lightweight processing steps defined in ImageProcessingPolicy.
    - `__init__(self, policy)`
    - `apply(self, image)`
    - `_resize(image, size)`
    - `_blur(image, radius)`
- **Functions:** (none)

## modules/structured_io/__init__.py

- **Module docstring:** (none)
- **Imports:** `formats.yaml_io -> YamlParser, YamlDumper`, `formats.json_io -> JsonParser, JsonDumper`, `fileio.structured_fileio -> StructuredFileIO`, `base.base_policy -> BaseParserPolicy, BaseDumperPolicy`
- **Classes:** (none)
- **Functions:**
- `yaml_parser(*, enable_env, enable_include, enable_placeholder, enable_reference, safe_mode, encoding, on_error, sort_keys, default_flow_style, indent)`
- `yaml_dumper(*, encoding, sort_keys, indent, default_flow_style, allow_unicode, safe_mode)`
- `yaml_fileio(path, *, parser_policy, dumper_policy)`
- `json_parser(*, enable_env, enable_placeholder, enable_reference, safe_mode, encoding, on_error)`
- `json_dumper(*, encoding, sort_keys, indent, allow_unicode)`
- `json_fileio(path, *, parser_policy, dumper_policy)`

## modules/structured_io/base/base_dumper.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `abc -> ABC, abstractmethod`, `typing -> Any`
- **Classes:**
- `BaseDumper` — (no docstring)
    - `__init__(self, policy)`
    - `dump(self, data)`
- **Functions:** (none)

## modules/structured_io/base/base_parser.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `abc -> ABC, abstractmethod`, `typing -> Any`, `pathlib -> Path`
- **Classes:**
- `BaseParser` — (no docstring)
    - `__init__(self, policy, context)`
    - `parse(self, text, base_path)`
- **Functions:** (none)

## modules/structured_io/base/base_policy.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `pydantic -> BaseModel, Field`
- **Classes:**
- `BaseParserPolicy` — (no docstring)
    - `is_safe_loader(self)`
- `BaseDumperPolicy` — (no docstring)
- **Functions:** (none)

## modules/structured_io/fileio/structured_fileio.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `pathlib -> Path`, `typing -> Any`, `fso_utils.ops -> FSOOps`, `fso_utils.policy -> FSOOpsPolicy`
- **Classes:**
- `StructuredFileIO` — 포맷 무관한 파일 단위 입출력 어댑터 (fso_utils 연동)
    - `__init__(self, path, parser, dumper, fso_policy)`
    - `read(self)`
    - `write(self, data)`
- **Functions:** (none)

## modules/structured_io/formats/json_io.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `json`, `typing -> Any`, `structured_io.base.base_parser -> BaseParser`, `structured_io.base.base_dumper -> BaseDumper`, `structured_io.utils.placeholder_resolver -> PlaceholderResolver`, `structured_io.utils.reference_resolver -> ReferenceResolver`
- **Classes:**
- `JsonParser` — JSON은 include가 없으므로 enable_include는 무시.
    - `parse(self, text, base_path)`
- `JsonDumper` — (no docstring)
    - `dump(self, data)`
- **Functions:** (none)

## modules/structured_io/formats/yaml_io.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `io`, `yaml`, `pathlib -> Path`, `typing -> Any`, `yaml -> SafeLoader, FullLoader, ScalarNode, Loader, SafeDumper, Dumper`, `structured_io.base.base_parser -> BaseParser`, `structured_io.base.base_dumper -> BaseDumper`, `structured_io.utils.placeholder_resolver -> PlaceholderResolver`, `structured_io.utils.reference_resolver -> ReferenceResolver`
- **Classes:**
- `YamlParser` — - SafeLoader/FullLoader 선택(safe_mode)
    - `__init__(self, policy, context)`
    - `_register_include_tag(self)`
    - `_include_constructor(self, loader, node)`
    - `parse(self, text, base_path)`
- `YamlDumper` — (no docstring)
    - `dump(self, data)`
- **Functions:** (none)

## modules/translater/translate.py

- **Module docstring:** modules.translate — Translation runner (dataclass defaults, YAML-aware)
- **Imports:** `__future__ -> annotations`, `dataclasses -> dataclass, field, asdict`, `typing -> Any, Dict, List, Optional, Tuple, Union, Iterable`, `pathlib -> Path`, `hashlib`, `sqlite3`, `json`, `os`, `re`, `deepl`, `modules.yamlutil -> section_or_root, load_yaml`, `modules.datautil -> as_list`, `modules.fileio -> ensure_dir, parent_dir_of`
- **Classes:**
- `TranslateSourceDefaults` — (no docstring)
- `TranslateProviderDefaults` — (no docstring)
- `TranslateZhChunkingDefaults` — (no docstring)
- `TranslateStoreDefaults` — (no docstring)
- `TranslateDefaults` — (no docstring)
- `DeepLTranslator` — (no docstring)
    - `__post_init__(self)`
    - `_ensure_schema(self)`
    - `close(self)`
    - `_get_cache(self, text)`
    - `_put_cache(self, text, out_text)`
    - `_apply_phrase_map(self, s)`
    - `_translate_one(self, text)`
    - `_translate_one_atomic(self, text)`
    - `translate(self, texts)`
- **Functions:**
- `_translate_section(cfg_like)` — YAML 경로/DICT에서 translate 섹션만 추출. 섹션이 없으면 루트를 사용.
- `_model_type_alias(s)`
- `_as_bool(val)`
- `normalize_translate_cfg(cfg_like)` — 외부 입력(cfg_like)을 TranslateDefaults dataclass로 정규화.
- `_mostly_zh(text, thresh)`
- `_chunk_clauses(text, max_len)` — 중국어 문장을 절/문장 단위로 잘라 max_len을 넘지 않게 분할.
- `_md5(s)`
- `run_translate(cfg_like)` — cfg_like (YAML 경로/DICT) → 번역 실행 → (translated_texts, saved_json_path, meta)
- `translate_cfg(texts, cfg_like)`
- `translate_cfg_one(text, cfg_like)`

## modules/unify_utils/__init__.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `core.normalizer_base -> NormalizerBase`, `core.resolver_base -> ResolverBase`, `core.base -> NormalizePolicyBase, RuleNormalizePolicy, ValueNormalizePolicy, ListNormalizePolicy, KeyPathNormalizePolicy`, `presets.rules -> NormalizeRule, RuleType, LetterCase, RegexFlag, RulePresets`, `normalizers.rule_normalizer -> RuleBasedNormalizer`, `normalizers.value_normalizer -> ValueNormalizer`, `normalizers.list_normalizer -> ListNormalizer`, `normalizers.keypath_normalizer -> KeyPathNormalizer`, `normalizers.placeholder_resolver -> PlaceholderResolver`, `normalizers.reference_resolver -> ReferenceResolver`, `typing -> Sequence`
- **Classes:** (none)
- **Functions:**
- `rule_normalizer(*, rules, recursive, strict)`
- `value_normalizer(*, date_fmt, bool_strict, recursive, strict)`
- `list_normalizer(*, sep, item_cast, keep_empty, min_len, max_len, recursive, strict)`
- `reference_resolver(data, *, recursive, strict)` — ReferenceResolver 팩토리
- `placeholder_resolver(context, *, recursive, strict)` — PlaceholderResolver 팩토리

## modules/unify_utils/core/base.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `typing -> Any, Callable, Optional, Sequence`, `pydantic -> BaseModel, Field`, `presets.rules -> NormalizeRule, RuleType, LetterCase, RegexFlag`
- **Classes:**
- `NormalizePolicyBase` — 모든 Normalizer 정책 클래스의 기반.
- `RuleNormalizePolicy` — 정규식 기반 정규화 정책.
- `ValueNormalizePolicy` — 단일 값 정규화 정책.
- `ListNormalizePolicy` — 리스트 및 시퀀스 정규화 정책.
- `KeyPathNormalizePolicy` — KeyPathNormalizer 전용 정책
- **Functions:** (none)

## modules/unify_utils/core/normalizer_base.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `abc -> ABC, abstractmethod`, `typing -> Any, Callable, Mapping, MutableMapping, cast`
- **Classes:**
- `NormalizerBase` — 정규화기들의 공통 기반 클래스.
    - `__init__(self, *, recursive, strict)`
    - `apply(self, value)` — 값을 정규화하여 반환합니다.
    - `compose(self, *others)` — 여러 Normalizer를 순서대로 적용하는 합성 정규화기 생성.
    - `_apply_single(self, value)` — 비-컨테이너 단일 값에 대한 정규화 로직을 구현합니다.
    - `_recursive_apply(self, value, fn)` — 컨테이너 타입에 대해 재귀적으로 정규화를 적용합니다.
- **Functions:** (none)

## modules/unify_utils/core/resolver_base.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `abc -> ABC, abstractmethod`, `typing -> Any, Callable, Mapping, MutableMapping, cast`
- **Classes:**
- `ResolverBase` — 데이터 구조 내 참조(Reference, Placeholder 등)를 해석하기 위한 추상 기반 클래스.
    - `__init__(self, *, recursive, strict)`
    - `apply(self, value)` — 입력 데이터 전체에 대해 해석 수행.
    - `_resolve_single(self, value)` — 단일 값(문자열 등)에 대한 실제 해석 로직 구현.
    - `_recursive_resolve(self, value, fn)` — 컨테이너 타입에 대해 재귀적으로 해석을 적용.
- **Functions:** (none)

## modules/unify_utils/normalizers/keypath_normalizer.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `typing -> List`, `data_utils.types -> KeyPath`, `data_utils.string_ops -> StringOps`, `unify_utils.core.normalizer_base -> NormalizerBase`, `unify_utils.core.base -> KeyPathNormalizePolicy`
- **Classes:**
- `KeyPathNormalizer` — KeyPath 문자열 또는 리스트를 정규화하여 List[str] 형태로 변환합니다.
    - `__init__(self, policy)`
    - `_apply_single(self, value)`
- **Functions:** (none)

## modules/unify_utils/normalizers/list_normalizer.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `re`, `typing -> Any, List`, `core.normalizer_base -> NormalizerBase`, `core.base -> ListNormalizePolicy`
- **Classes:**
- `ListNormalizer` — 리스트 및 시퀀스형 데이터 정규화기.
    - `__init__(self, policy)`
    - `_apply_single(self, value)`
- **Functions:** (none)

## modules/unify_utils/normalizers/placeholder_resolver.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `os`, `re`, `typing -> Any, Mapping`, `unify_utils.core.resolver_base -> ResolverBase`
- **Classes:**
- `PlaceholderResolver` — ✅ PlaceholderResolver
    - `__init__(self, context, *, recursive, strict)`
    - `_resolve_single(self, value)`
    - `_resolve_env(cls, text)`
    - `_resolve_context(self, text)`
- **Functions:** (none)

## modules/unify_utils/normalizers/reference_resolver.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `re`, `typing -> Any`, `unify_utils.core.resolver_base -> ResolverBase`, `unify_utils.core.base -> KeyPathNormalizePolicy`, `unify_utils.normalizers.keypath_normalizer -> KeyPathNormalizer`
- **Classes:**
- `ReferenceResolver` — 데이터 내부 참조를 해석하는 Resolver.
    - `__init__(self, data, *, keypath_policy, recursive, strict)`
    - `_resolve_single(self, value)`
    - `_resolve_placeholders(self, value)`
    - `_resolve_keypath(self, path)`
- **Functions:** (none)

## modules/unify_utils/normalizers/rule_normalizer.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `re`, `typing -> Any`, `core.normalizer_base -> NormalizerBase`, `core.base -> RuleType, RegexFlag, LetterCase, RuleNormalizePolicy`
- **Classes:**
- `RuleBasedNormalizer` — 정규식 및 문자열 클린 룰 기반 정규화기
    - `__init__(self, policy)`
    - `_apply_single(self, value)`
- **Functions:** (none)

## modules/unify_utils/normalizers/value_normalizer.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `re`, `datetime -> datetime`, `typing -> Any, Optional`, `core.normalizer_base -> NormalizerBase`, `core.base -> ValueNormalizePolicy`
- **Classes:**
- `ValueNormalizer` — 단일 값 기반 정규화기.
    - `__init__(self, policy)`
    - `_apply_single(self, value)`
    - `normalize_bool(self, v)`
    - `normalize_int(self, v, default)`
    - `normalize_date(self, v)`
    - `normalize_filename(self, name, *, mode)`
- **Functions:** (none)

## modules/unify_utils/presets/rules.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `enum -> Enum`, `typing -> List, Optional`, `pydantic -> BaseModel, model_validator`
- **Classes:**
- `RuleType` — 정규화 룰의 적용 방식
- `LetterCase` — 문자열 대소문자 처리 방식
- `RegexFlag` — 정규표현식 플래그 옵션
- `NormalizeRule` — 입력 문자열에 적용할 정규화 규칙 정의.
    - `validate_fields(cls, values)`
- `RulePresets` — 자주 사용하는 NormalizeRule 프리셋 모음
- **Functions:** (none)

## modules/xl_utils/policy.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `pydantic -> BaseModel, Field`
- **Classes:**
- `XwAppPolicy` — (no docstring)
- `XwWbPolicy` — (no docstring)
- **Functions:** (none)

## modules/xl_utils/test.py

- **Module docstring:** YAML 설정 기반 xl_utils 제어 테스트
- **Imports:** `xl_utils.xw_app -> XwApp`, `xl_utils.xw_wb -> XwWb`, `xl_utils.xw_ws -> XwWs`, `xl_utils.policy -> XwAppPolicy, XwWbPolicy`, `datetime -> datetime`, `pandas`, `yaml`, `pathlib -> Path`
- **Classes:** (none)
- **Functions:**
- `load_yaml_config(path)` — YAML 파일을 읽어 dict로 반환
- `test_xlwings_from_yaml(cfg_path)` — YAML 기반 Excel 제어 테스트

## modules/xl_utils/xw_app.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `xlwings`, `pathlib -> Path`, `typing -> Optional, Union`, `fso_utils -> FSOOpsPolicy, ExistencePolicy, FSOOps`, `xl_utils.policy -> XwAppPolicy`
- **Classes:**
- `XwApp` — Excel Application 수명주기 제어 (정책 + FSO 기반)
    - `__init__(self, path, *, policy)`
    - `start(self)` — Excel Application 실행 (필요 시 새로 띄움)
    - `open_book(self, path)` — 워크북 열기 (정책 기반 FSO 확인)
    - `quit(self, save_all)` — 직접 실행한 경우만 종료 (종료 전 자동 저장 지원)
    - `__enter__(self)`
    - `__exit__(self, exc_type, exc, tb)` — Context 종료 시 정책 기반 저장 및 종료
- **Functions:** (none)

## modules/xl_utils/xw_wb.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `xlwings`, `pathlib -> Path`, `typing -> Optional, Union`, `fso_utils -> FSOOpsPolicy, ExistencePolicy, FSOOps`, `policy -> XwWbPolicy`
- **Classes:**
- `XwWb` — 워크북 단위 제어
    - `__init__(self, app, path, *, policy)`
    - `open(self)` — 워크북 열기 (정책 기반 경로 확인)
    - `save(self)`
    - `close(self, save)` — 워크북 닫기 (정책 기반 자동 저장 지원)
    - `sheet(self, name_or_index)`
- **Functions:** (none)

## modules/xl_utils/xw_ws.py

- **Module docstring:** (none)
- **Imports:** `__future__ -> annotations`, `xlwings`, `pathlib -> Path`, `typing -> Any, Optional, Union`, `pandas`
- **Classes:**
- `XwWs` — 워크시트 단위 제어
    - `__init__(self, book, sheet, *, create_if_missing)` — 워크시트 컨트롤러 초기화
    - `_ensure_sheet(self, book, sheet, create_if_missing)` — 시트 확보 (없으면 생성)
    - `read_cell(self, cell)`
    - `write_cell(self, row, col, value, *, number_format, save)` — 행/열 좌표 기반 셀 쓰기 (xw_set_cell_value 대체)
    - `to_dataframe(self, anchor, *, header, index, expand, drop_empty)` — 시트 데이터를 DataFrame으로 변환
    - `from_dataframe(self, df, anchor, *, index, header, clear)` — DataFrame을 시트에 기록
    - `clear(self, cell)`
    - `autofit(self, axis)`
    - `used_range(self)`
- **Functions:** (none)

## scripts/0.TEST.py

- **Module docstring:** (none)
- **Imports:** `firefox.driver -> FirefoxDriver`
- **Classes:** (none)
- **Functions:** (none)

## scripts/generate_code_analysis.py

- **Module docstring:** (none)
- **Imports:** `ast`, `datetime`, `pathlib -> Path`, `typing -> List`
- **Classes:** (none)
- **Functions:**
- `summarize_docstring(doc)`
- `collect_imports(tree)`
- `format_args(args)`
- `main()`

## scripts/ocr_translate_overlay.py

- **Module docstring:** scripts/run_translate_overlay.py
- **Imports:** `__future__ -> annotations`, `pathlib -> Path`, `typing -> Any, Dict, List, Optional, Tuple, Union`, `json`, `os`, `modules.yamlutil -> load_yaml`, `modules.fileio -> resolve_file_path, must_abs, default_log_dir_for, ensure_log_file, append_log`, `modules.datautil -> dedupe_keep_order, is_blank, is_number_or_symbol_only, norm_text_key`, `ocr.ocr -> run_ocr`, `translate.translate -> run_translate`, `pillow_utils.overlay -> render_overlay`
- **Classes:** (none)
- **Functions:**
- `_as_dict(cfg_like)`
- `_get_secs(cfg)` — 루트에서 image/ocr/translate/overlay/oto 섹션만 추출(없으면 빈 dict).
- `_ensure_file_paths_inherit(secs, src_path)` — image.file_path, ocr.file_path 가 비었으면 oto.file_path(src_path) 상속.
- `_find_src_path(secs)` — 파일 경로 우선순위: oto > overlay > ocr > image
- `_bbox_to_poly(bbox)`
- `_pick_triple_from_translate(res)` — run_translate 반환값을 (out_texts, saved_tr_json, meta_tr)로 정규화.
- `_extract_ocr_triplets(meta_ocr)` — OCR items에서 (원문, 키, poly) 배출.
- `_build_translation_map(texts_key, texts_src, outs)` — 정규화 키 기준 dedupe 후 번역 결과를 키에 매핑.
- `_compose_overlay_items(texts_src, texts_key, item_polys, tr_map)` — OCR 순서 그대로 overlay 'ol' 리스트 생성 + 통계 반환.
- `run_oto(cfg_like)` — OCR → TRANSLATE → OVERLAY → SAVE

## scripts/run_oto_from_excel.py

- **Module docstring:** Excel 기반 OTO 배치 실행기 — run_xloto
- **Imports:** `__future__ -> annotations`, `sys`, `pathlib -> Path`, `typing -> Any, Dict, List`, `datetime -> date`, `modules.yamlutil -> load_yaml, normalize_with_placeholders`, `modules.paths -> P, _PathsProxy`, `modules.fileio -> list_image_files, ensure_dir, must_abs`, `modules.excel -> xw_load_excel, eligible_rows, xw_set_cell_value`, `modules.datautil -> is_blank`, `scripts.ocr_translate_overlay -> run_oto`
- **Classes:** (none)
- **Functions:**
- `_paths_ctx(paths_yaml)` — 주어진 paths.yaml 로 읽는 컨텍스트(없으면 ENV CASHOP_PATHS 사용).
- `_load_and_resolve_yaml(yaml_path, vars_map)` — YAML 로드 → ${}/{} 치환 → *_dir 절대경로화.
- `_build_overlay_dirs(paths_cfg, cas)` — public_img_dir/<CAS>/<translated|removed|final> 폴더 생성
- `_build_cfg_for_image(base_cfg, *, img_path, log_dir, ov_save_dir, db_dir)` — 한 장의 이미지에 사용할 통합 cfg_like 생성.
- `run_xloto(*, paths_yaml, oto_yaml, cas_col, download_col, translation_col)` — Excel 기반 일괄 OTO 파이프라인 실행.
- `_cli()`

## scripts/test_crawl_refactor.py

- **Module docstring:** Lightweight pipeline test using dummy driver/fetcher.
- **Imports:** `__future__ -> annotations`, `asyncio`, `pathlib -> Path`, `yaml`, `crawl_refactor -> CrawlPolicy, CrawlPipeline, NavigationPolicy, ScrollPolicy, ExtractorPolicy, WaitPolicy, NormalizationPolicy, NormalizationRule, StoragePolicy, StorageTargetPolicy`, `crawl_refactor.fetcher -> DummyFetcher`, `crawl_refactor.navigator -> SeleniumNavigator`, `crawl_refactor.policy -> WaitCondition, WaitHook, ScrollStrategy, ExtractorType`
- **Classes:**
- `DummyDriver` — (no docstring)
- **Functions:** (none)
