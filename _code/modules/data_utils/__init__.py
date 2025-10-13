# -*- coding: utf-8 -*-
# data_utils/__init__.py

"""Top‑level package for data utilities.

This package aggregates a variety of helpers for working with common data
structures such as pandas DataFrames, Python dictionaries and lists, and
key‑path representations.  It also provides utilities for converting
between common data formats (e.g. JSON, YAML, images) and for flattening
or expanding nested data structures.

The following primary classes are available:

* :class:`FormatOps` – static methods for converting between different
  serialized data formats (bytes, images, JSON, YAML).
* :class:`StructureOps` – static methods for transforming nested data
  structures and key‑path representations.
* :class:`DataFramePolicy` – a dataclass defining configuration options
  for DataFrame operations.
* :class:`DataFrameOps` – a composite class composed of several mixins
  providing DataFrame creation, normalization, filtering, updating and
  cleaning functionality.

Legacy aliases :class:`Convert` and :class:`DataTransOps` are retained
for backward compatibility.  They derive from :class:`FormatOps` and
``StructureOps`` respectively.  New code should prefer the newer
class names.
"""

from .format_ops import FormatOps
from .structure_ops import StructureOps
from .convert import Convert  # deprecated alias of FormatOps
from .trans_ops import DataTransOps, TransOps  # deprecated aliases of StructureOps
from .df_ops import DataFramePolicy, DataFrameOps
from .dict_ops import DictOps
from .list_ops import ListOps
from .string_ops import StringOps
from .types import (
    PathLike,
    KeyPath,
    JsonDict,
    SectionName,
    FieldName,
    GroupedPairDict,
    MultiValueGroupDict,
)

__all__ = [
    "FormatOps",
    "StructureOps",
    "Convert",
    "DataTransOps",
    "TransOps",
    "DataFramePolicy",
    "DataFrameOps",
    "DictOps",
    "ListOps",
    "StringOps",
    "PathLike",
    "KeyPath",
    "JsonDict",
    "SectionName",
    "FieldName",
    "GroupedPairDict",
    "MultiValueGroupDict",
]
