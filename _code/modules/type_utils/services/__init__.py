# -*- coding: utf-8 -*-
# type_utils/services/__init__.py
# Services exports

from .inferencer import (
    TypeInferencer,
    get_default_inferencer,
    infer_type,
    infer_extension,
    is_url,
)

from .extension import (
    ExtensionDetector,
    get_default_detector,
    extract_extension,
    extract_all_extensions,
    normalize_extension,
)

__all__ = [
    # TypeInferencer
    "TypeInferencer",
    "get_default_inferencer",
    "infer_type",
    "infer_extension",
    "is_url",
    
    # ExtensionDetector
    "ExtensionDetector",
    "get_default_detector",
    "extract_extension",
    "extract_all_extensions",
    "normalize_extension",
]
