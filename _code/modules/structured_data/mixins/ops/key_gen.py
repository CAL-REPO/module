"""Key generation mixin for creating cache keys.

Provides utilities for generating stable, unique keys from arbitrary inputs.
"""

import hashlib
from ...core import BaseOperationsMixin, BaseOperationsPolicy


class KeyGenerationMixin(BaseOperationsMixin):
    """Mixin for generating cache keys.
    
    Provides static methods for creating stable, unique keys from
    multiple string parts using different strategies.
    """
    
    def _default_policy(self) -> BaseOperationsPolicy:
        """Return default policy."""
        return BaseOperationsPolicy()
    
    @staticmethod
    def make_key(*parts: str) -> str:
        """Generate a stable SHA256-based key from parts.
        
        Creates a cryptographically stable key by hashing all parts
        together. The same parts in the same order will always produce
        the same key.
        
        Args:
            *parts: String parts to combine into a key. ``None`` values
                are treated as empty strings.
        
        Returns:
            A 64-character hexadecimal string (SHA256 hash).
        
        Example:
            >>> KeyGenerationMixin.make_key("user", "123", "en")
            'a3f5d8...'
        """
        h = hashlib.sha256()
        for p in parts:
            h.update((p or "").encode("utf-8", errors="ignore"))
            h.update(b"\0")  # Separator to prevent collision
        return h.hexdigest()
    
    @staticmethod
    def make_simple_key(*parts: str) -> str:
        """Generate a simple colon-separated key from parts.
        
        Creates a human-readable key by joining parts with colons.
        Less stable than :meth:`make_key` but easier to debug.
        
        Args:
            *parts: String parts to join. ``None`` and empty values
                are filtered out.
        
        Returns:
            A colon-separated string.
        
        Example:
            >>> KeyGenerationMixin.make_simple_key("user", "123", "en")
            'user:123:en'
        """
        return ":".join(str(p) for p in parts if p)
