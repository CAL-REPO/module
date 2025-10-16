"""Script utilities for main scripts.

This package provides helper modules for common patterns in main scripts:
- ENV variable loading
- Config initialization
- Path management
"""

from .env_loader import EnvBasedConfigInitializer

__all__ = [
    "EnvBasedConfigInitializer",
]
