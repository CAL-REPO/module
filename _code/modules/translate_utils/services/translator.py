# -*- coding: utf-8 -*-
"""Translator: Main entrypoint for translate_utils.

Follows the same pattern as FirefoxWebDriver:
- Accepts YAML path, dict, or TranslatePolicy instance
- Uses ConfigLoader for configuration
- Integrates logs_utils via LogContextManager
- Lazy provider creation via ProviderFactory

Example:
    >>> # YAML config
    >>> translator = Translator("config/translate.yaml")
    >>> result = translator.run()
    
    >>> # Dict config
    >>> translator = Translator({"provider": {"provider": "deepl", "target_lang": "KO"}})
    
    >>> # Policy instance
    >>> policy = TranslatePolicy(...)
    >>> translator = Translator(policy)
    
    >>> # Context manager
    >>> with Translator("config.yaml") as t:
    ...     result = t.run()
"""

from __future__ import annotations

from pathlib import Path
from typing import Union, Optional, Any, List, Dict

from pydantic import BaseModel

from cfg_utils import ConfigLoader, ConfigPolicy
from logs_utils import LogContextManager

from ..core.policy import TranslatePolicy
from ..providers.factory import ProviderFactory
from ..providers.base import Provider
from .pipeline import TranslationPipeline
from .source_loader import TextSourceLoader, SourcePayload
from .preprocessor import TextPreprocessor
from .storage import TranslationCache, TranslationResultWriter


class Translator:
    """Translation service entrypoint.
    
    Follows the same pattern as FirefoxWebDriver and ImageLoader:
    - ConfigLoader integration for YAML/dict/Policy loading
    - logs_utils LogContextManager for logging
    - ProviderFactory for automatic provider selection
    - Context manager support
    
    Usage:
        >>> # From YAML config
        >>> translator = Translator("config/translate.yaml")
        >>> result = translator.run()
        >>> print(result)  # {"Hello": "안녕하세요", ...}
        
        >>> # Runtime override (provider 변경)
        >>> translator = Translator("config.yaml", provider__provider="google")
        >>> result = translator.run()
        
        >>> # Runtime override (동적 텍스트 주입)
        >>> translator = Translator(
        ...     "config.yaml",
        ...     source__text=["你好", "谢谢", "再见"]  # 텍스트 동적 주입
        ... )
        >>> result = translator.run()
        >>> print(result)  # {"你好": "안녕하세요", "谢谢": "감사합니다", ...}
        
        >>> # Dict config (간단한 사용)
        >>> translator = Translator({
        ...     "source": {"text": ["Hello", "Thank you"]},
        ...     "provider": {"provider": "deepl", "target_lang": "KO"}
        ... })
        >>> result = translator.run()
        
        >>> # Context manager
        >>> with Translator("config.yaml") as t:
        ...     result = t.run()
    """
    
    def __init__(
        self,
        cfg_like: Union[TranslatePolicy, Path, str, dict, list, None] = None,
        *,
        policy_overrides: Optional[dict] = None,
        **overrides: Any
    ):
        """Initialize Translator with configuration.
        
        Args:
            cfg_like: Configuration source:
                - TranslatePolicy: Policy instance
                - str/Path: YAML file path
                - dict: Configuration dict
                - list[str/Path]: Multiple YAML files (merged)
                - None: Use default config/translate.yaml
            policy_overrides: ConfigPolicy 필드 개별 오버라이드 (merge_mode, yaml.source_paths 등)
            **overrides: Runtime overrides (e.g., provider__target_lang="EN")
        
        Example:
            >>> # YAML path
            >>> t = Translator("config/translate.yaml")
            
            >>> # Multiple files
            >>> t = Translator(["base.yaml", "override.yaml"])
            
            >>> # Dict
            >>> t = Translator({"provider": {"provider": "deepl"}})
            
            >>> # Runtime override
            >>> t = Translator("config.yaml", provider__target_lang="EN")
        """
        self.config = self._load_config(cfg_like, policy_overrides=policy_overrides, **overrides)
        self._provider: Optional[Provider] = None
        self._pipeline: Optional[TranslationPipeline] = None
        self._logging_active = False
        self._context_managed = False
        self._setup_logging()
    
    # ==========================================================================
    # Configuration Loading
    # ==========================================================================
    
    def _load_config(
        self,
        cfg_like: Union[TranslatePolicy, Path, str, dict, list, None],
        *,
        policy_overrides: Optional[dict] = None,
        **overrides: Any
    ) -> TranslatePolicy:
        """Load configuration using ConfigLoader pattern.
        
        Args:
            cfg_like: Configuration source
            policy_overrides: ConfigPolicy 필드 개별 오버라이드 (merge_mode, yaml.source_paths 등)
            **overrides: Runtime overrides
        
        Returns:
            Loaded TranslatePolicy instance
        """
        if cfg_like is None:
            default_path = Path(__file__).parent.parent / "configs" / "translate.yaml"
            if policy_overrides is None:
                policy_overrides = {}

            # ConfigLoader 정책 파일 지정
            policy_overrides.setdefault("config_loader_path",
                str(Path(__file__).parent.parent / "configs" / "config_loader_translate.yaml"))

            # 데이터 파일 + 섹션 지정
            policy_overrides.setdefault("yaml.source_paths", {
                "path": str(default_path),
                "section": "translate"
            })
        
        return ConfigLoader.load(
            cfg_like,
            model=TranslatePolicy,
            policy_overrides=policy_overrides,
            **overrides
        )
    
    # ==========================================================================
    # Provider & Pipeline (Lazy Creation)
    # ==========================================================================
    
    @property
    def provider(self) -> Provider:
        """Lazy provider creation using ProviderFactory.
        
        Returns:
            Provider instance
        """
        if self._provider is None:
            self.logger.debug(f"Creating provider: {self.config.provider.provider}")
            self._provider = ProviderFactory.create(
                provider_name=self.config.provider.provider,
                api_key=None,  # Will use env var
                timeout=self.config.provider.timeout
            )
        return self._provider
    
    @property
    def pipeline(self) -> TranslationPipeline:
        """Lazy pipeline creation.
        
        Returns:
            TranslationPipeline instance
        """
        if self._pipeline is None:
            self.logger.debug("Creating translation pipeline")
            
            # Create components
            preprocessor = TextPreprocessor(self.config.zh)
            
            # Cache (optional)
            cache = None
            if self.config.store.save_db:
                from path_utils.os_paths import OSPath
                default_dir = OSPath.downloads()
                cache = TranslationCache(self.config.store, default_dir=default_dir)
            
            # Writer (optional)
            writer = None
            if self.config.store.save_tr:
                from path_utils.os_paths import OSPath
                default_dir = OSPath.downloads()
                writer = TranslationResultWriter(self.config.store, default_dir=default_dir)
            
            # Create pipeline
            self._pipeline = TranslationPipeline(
                policy=self.config,
                provider=self.provider,
                preprocessor=preprocessor,
                cache=cache,
                writer=writer,
                logger=self.logger
            )
        
        return self._pipeline
    
    # ==========================================================================
    # Main Execution
    # ==========================================================================
    
    def run(self) -> Dict[str, str]:
        """Execute translation and return source→translated mapping.
        
        Returns:
            Dict mapping source text to translated text
        
        Example:
            >>> translator = Translator("config.yaml")
            >>> result = translator.run()
            >>> print(result)
            {"Hello": "안녕하세요", "Thank you": "감사합니다"}
        """
        self.logger.info("=" * 70)
        self.logger.info("[Translator] Starting translation")
        self.logger.info(f"  Provider: {self.config.provider.provider}")
        self.logger.info(f"  {self.config.provider.source_lang} → {self.config.provider.target_lang}")
        
        # Load source texts
        source_loader = TextSourceLoader(self.config.source)
        payload = source_loader.load()
        sources = payload.texts
        
        if not sources:
            self.logger.warning("No texts to translate")
            return {}
        
        self.logger.info(f"  Texts: {len(sources)}")
        
        # Run pipeline
        translations = self.pipeline.run(payload)
        
        # Create mapping
        mapping: Dict[str, str] = {}
        for idx, src in enumerate(sources):
            translated = translations[idx] if idx < len(translations) else ""
            mapping[src] = translated
        
        self.logger.success(f"[Translator] Completed: {len(mapping)} translations")
        self.logger.info("=" * 70)
        
        return mapping
    
    # ==========================================================================
    # Logging Setup
    # ==========================================================================
    
    def _setup_logging(self):
        """Setup logging using LogContextManager (same as BaseWebDriver)."""
        # Get log_config from policy
        log_config = self.config.log_config
        
        # If no log_config, use default console logging
        if log_config is None:
            log_config_dict = {
                "name": "Translator",
                "sinks": [
                    {
                        "sink_type": "console",
                        "level": "INFO",
                        "format": "<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | <cyan>{name}</cyan> | <level>{message}</level>",
                        "colorize": True
                    }
                ]
            }
        else:
            log_config_dict = log_config.model_dump()
        
        self._log_context = LogContextManager(log_config_dict)
        self.logger = self._log_context.__enter__()
        self._logging_active = True
        self.logger.debug("Translator initialized")
    
    def _stop_logging(self, exc_type=None, exc_val=None, exc_tb=None):
        """Stop logging context."""
        if self._logging_active and self._log_context:
            self._log_context.__exit__(exc_type, exc_val, exc_tb)
            self._logging_active = False
    
    # ==========================================================================
    # Resource Cleanup
    # ==========================================================================
    
    def close(self):
        """Close provider and cleanup resources."""
        if self._provider:
            try:
                self._provider.close()
                self.logger.debug("Provider closed")
            except Exception as e:
                self.logger.warning(f"Error closing provider: {e}")
            finally:
                self._provider = None
        
        if not self._context_managed:
            self._stop_logging()
    
    # ==========================================================================
    # Context Manager
    # ==========================================================================
    
    def __enter__(self) -> "Translator":
        """Context manager entry.
        
        Example:
            >>> with Translator("config.yaml") as t:
            ...     result = t.run()
        """
        self._context_managed = True
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        try:
            self.close()
        finally:
            self._stop_logging(exc_type, exc_val, exc_tb)
            self._context_managed = False
    
    def __del__(self):
        """Destructor - cleanup resources."""
        try:
            if self._provider or self._logging_active:
                self.close()
        except Exception:
            pass
