"""
translate_utils
---------------
Translation utilities and pipeline components for text and structured data.

구조:
- entry_point/: 외부 진입점 (Translator)
- adapter/: 비즈니스 로직 (Translate)
- services/: 내부 서비스 (Pipeline, Cache, Storage)
- providers/: 외부 통합 (DeepL, Google)
- core/: 공통 정책/모델

Main entrypoint:
    Translator - YAML/dict-based translation service (follows FirefoxWebDriver pattern)
    Translate - Pure translation logic adapter

Example:
    >>> from translate_utils import Translator
    >>> 
    >>> # From YAML config
    >>> translator = Translator("config/translate.yaml")
    >>> result = translator.run()
    >>> print(result)  # {"Hello": "안녕하세요", ...}
    >>> 
    >>> # Direct usage
    >>> from translate_utils import Translate
    >>> translate = Translate(policy)
    >>> result = translate.run(["Hello", "World"])
"""

from .entry_point import Translator
from .adapter import Translate
from .core.policy import TranslatePolicy

__all__ = [
    "Translator",
    "Translate",
    "TranslatePolicy",
]
