# -*- coding: utf-8 -*-
"""XLOTO Package.

Excel + OTO 통합 파이프라인.

사용자 인터페이스:
    >>> from xloto import Xloto
    >>> xloto = Xloto()
    >>> result = xloto.run()

Adapter (Standalone):
    >>> from xloto.adapter import XlOto
    >>> xloto = XlOto(cfg_like="xloto.yaml")
"""

# EntryPoint (사용자 인터페이스)
from xloto.entry_point.xloto import Xloto  # noqa: F401

# Adapter (Standalone)
from xloto.adapter.xloto import XlOto  # noqa: F401

__all__ = ["Xloto", "XlOto"]
