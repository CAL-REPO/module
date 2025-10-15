"""
translate_utils
---------------
Translation utilities and pipeline components for text and structured data.

Main entrypoint:
    Translator - YAML/dict-based translation service (follows FirefoxWebDriver pattern)

Example:
    >>> from translate_utils import Translator
    >>> 
    >>> # From YAML config
    >>> translator = Translator("config/translate.yaml")
    >>> result = translator.run()
    >>> print(result)  # {"Hello": "안녕하세요", ...}
    >>> 
    >>> # Runtime override
    >>> translator = Translator("config.yaml", provider__target_lang="EN")
    >>> 
    >>> # Context manager
    >>> with Translator("config.yaml") as t:
    ...     result = t.run()
"""

from .services.translator import Translator
from .core.policy import TranslatePolicy

__all__ = [
    "Translator",
    "TranslatePolicy",
]
