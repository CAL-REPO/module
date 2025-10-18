"""Script utilities for main scripts.

This package provides helper modules for common patterns in main scripts:
- ENV variable loading
- Config initialization
- Path management
- OTO Policy integration
"""

from .env_loader import EnvBasedConfigInitializer
from .core.oto_policy import OTOPolicy

__all__ = [
    "EnvBasedConfigInitializer",
    "OTOPolicy",
]
