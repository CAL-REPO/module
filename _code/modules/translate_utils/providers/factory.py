# -*- coding: utf-8 -*-
"""Provider factory for translation backends.

Automatically instantiates the appropriate Provider based on configuration.
Supports dynamic registration for extensibility.
"""

from __future__ import annotations

from typing import Dict, Type, Optional, Any

from .base import Provider
from .deepl import DeepLProvider
from .mock import MockProvider


class ProviderFactory:
    """Factory for creating translation providers based on configuration.
    
    Supports automatic provider selection and dynamic registration for extensibility.
    
    Example:
        >>> from translate_utils.core.policy import ProviderPolicy
        >>> policy = ProviderPolicy(provider="deepl", target_lang="KO")
        >>> provider = ProviderFactory.create(policy)
        
        >>> # Register custom provider
        >>> ProviderFactory.register("custom", MyCustomProvider)
    """
    
    _registry: Dict[str, Type[Provider]] = {
        "deepl": DeepLProvider,
        "mock": MockProvider,
        # "google": GoogleProvider,  # Future: Add Google Translate provider
    }
    
    @classmethod
    def create(
        cls,
        provider_name: str,
        *,
        api_key: Optional[str] = None,
        timeout: int = 30,
    ) -> Provider:
        """Create a provider instance based on name.
        
        Args:
            provider_name: Provider identifier ("deepl", "google", "mock")
            api_key: Optional API key (overrides environment variable)
            timeout: Request timeout in seconds
        
        Returns:
            Instantiated Provider
        
        Raises:
            ValueError: If provider is not registered
        """
        provider_id = provider_name.lower().strip()
        
        if provider_id not in cls._registry:
            available = ", ".join(sorted(cls._registry.keys()))
            raise ValueError(
                f"Unknown provider: '{provider_id}'. Available providers: {available}"
            )
        
        provider_class = cls._registry[provider_id]
        
        # Instantiate with common arguments
        return provider_class(api_key=api_key, timeout=timeout)  # type: ignore
    
    @classmethod
    def register(cls, name: str, provider_class: Type[Provider]) -> None:
        """Register a new provider (plugin pattern).
        
        Args:
            name: Provider identifier (case-insensitive)
            provider_class: Provider class implementing the Provider interface
        
        Example:
            >>> class MyProvider(Provider):
            ...     def translate_text(self, texts, *, target_lang, source_lang=None, model_type=None):
            ...         # Implementation
            ...         pass
            >>> 
            >>> ProviderFactory.register("myprovider", MyProvider)
        """
        cls._registry[name.lower().strip()] = provider_class
    
    @classmethod
    def list_providers(cls) -> list[str]:
        """List all registered provider names.
        
        Returns:
            Sorted list of provider identifiers
        """
        return sorted(cls._registry.keys())
    
    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if a provider is registered.
        
        Args:
            name: Provider identifier
        
        Returns:
            True if registered, False otherwise
        """
        return name.lower().strip() in cls._registry
