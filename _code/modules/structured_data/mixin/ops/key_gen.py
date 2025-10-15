
# -*- coding: utf-8 -*-
"""
structured_data.mixin.ops.key_gen
---------------------------------
Role-based mixin for key generation operations in structured data.
"""

from __future__ import annotations

import hashlib
from typing import Optional

from ...core import DBPolicy, BaseOperationsMixin


class KeyGenerationMixin(BaseOperationsMixin):
    """Key generation mixin for creating hashed keys from parts.
    
    Provides make_key method for generating SHA256 hash-based keys
    from multiple parts (useful for composite keys in caching).
    
    Attributes:
        policy: DBPolicy instance (inherited from BaseOperationsMixin).
    """
    
    def __init__(self, policy: Optional[DBPolicy] = None):
        """Initialize key generation mixin with policy.
        
        Args:
            policy: DBPolicy instance. If None, uses default DBPolicy().
        """
        super().__init__(policy or DBPolicy())
    
    @staticmethod
    def make_key(*parts: str) -> str:
        """Generate SHA256 hash key from string parts.
        
        Useful for creating composite keys from multiple fields.
        
        Args:
            *parts: Variable number of string parts to hash together.
        
        Returns:
            64-character hexadecimal SHA256 hash string.
        
        Example:
            >>> make_key("user", "123", "en")
            'a3f2...' # 64-char hash
        """
        joined = "\x1f".join(parts)  # Use ASCII Unit Separator as delimiter
        return hashlib.sha256(joined.encode("utf-8")).hexdigest()
