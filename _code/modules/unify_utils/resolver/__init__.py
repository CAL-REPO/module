# -*- coding: utf-8 -*-
"""Resolver subpackage with placeholder and reference resolvers."""

# PlaceholderResolver, ReferenceResolver는 제거됨 (VarsResolver로 통합)
from .vars import VarsResolver

__all__ = ["VarsResolver"]

