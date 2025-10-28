# -*- coding: utf-8 -*-
"""XLOTO Package.

Excel + OTO 통합 파이프라인.

사용자 인터페이스:
    >>> from xloto import Xloto
    >>> xloto = Xloto()
    >>> result = xloto.run()

Adapter (Standalone):
    >>> from xloto.adapter import XlOTO
    >>> xloto = XlOTO(cfg_like="xloto.yaml")
"""

# Adapter (Standalone)
from cashop.xloto.adapter.xloto import XlOTO  # noqa: F401

__all__ = ["XlOTO"]
