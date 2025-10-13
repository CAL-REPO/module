# -*- coding: utf-8 -*-
# firefox/driver.py - Firefox WebDriver 캡슐화 클래스 with LoggerPolicy 설정 기반 적용

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Optional, Union
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

from firefox.config import FirefoxConfig
from cfg_utils import ConfigLoader
from fso_utils import JsonFileIO, FSOOpsPolicy, ExistencePolicy
from log_utils import LogContextManager


class FirefoxDriver:
    def __init__(self, cfg_like: Union[FirefoxConfig, dict[str, Any], str, Path, None] = None, **overrides: Any):
        self.config = self._load_config(cfg_like, **overrides)
        self._driver: Optional[webdriver.Firefox] = None

        self._log_context = LogContextManager("firefox", policy=self.config.log_policy)
        self.logger = self._log_context.__enter__()
        self._logging_active = True
        self._context_managed = False
        self.logger.debug("FirefoxDriver initialized.")

    @staticmethod
    def _load_config(cfg_like: Union[FirefoxConfig, dict[str, Any], str, Path, None], **overrides: Any) -> FirefoxConfig:
        if isinstance(cfg_like, FirefoxConfig):
            return cfg_like.model_copy(update=overrides)
        if isinstance(cfg_like, (str, Path)):
            loader = ConfigLoader(str(cfg_like))
            return loader.as_model(FirefoxConfig, **overrides)
        if isinstance(cfg_like, dict):
            merged = {**cfg_like, **overrides}
            return FirefoxConfig(**merged)
        if cfg_like is None:
            return FirefoxConfig(**overrides)
        raise TypeError(f"Unsupported Firefox config input: {type(cfg_like)!r}")

    @property
    def driver(self) -> webdriver.Firefox:
        if self._driver is None:
            self.logger.debug("Creating WebDriver instance...")
            self.create()
        return self._driver  # pyright: ignore[reportReturnType]

    def create(self):
        cfg = self.config
        opts = Options()

        if cfg.binary_path:
            opts.binary_location = str(cfg.binary_path)
            self.logger.debug(f"Set binary path: {cfg.binary_path}")

        if cfg.profile_path:
            opts.add_argument("-profile")
            opts.add_argument(str(cfg.profile_path))
            self.logger.debug(f"Using Firefox profile: {cfg.profile_path}")

        if cfg.headless:
            opts.add_argument("--headless")

        if cfg.window_size:
            w, h = cfg.window_size
            opts.add_argument(f"--width={w}")
            opts.add_argument(f"--height={h}")

        headers = self._load_session_headers()

        if headers:
            self.logger.debug("Restoring headers from session file")
            if "User-Agent" in headers:
                opts.set_preference("general.useragent.override", headers["User-Agent"])
            if "Accept-Language" in headers:
                opts.set_preference("intl.accept_languages", headers["Accept-Language"])
        else:
            if cfg.accept_languages:
                opts.set_preference("intl.accept_languages", cfg.accept_languages)
            if cfg.user_agent:
                opts.set_preference("general.useragent.override", cfg.user_agent)

        opts.set_preference("dom.webdriver.enabled", cfg.dom_enabled)
        opts.set_preference("privacy.resistFingerprinting", cfg.resist_fingerprint_enabled)

        exe = self._get_driver_path()

        self.logger.info("Launching Firefox WebDriver")
        self._driver = webdriver.Firefox(service=Service(executable_path=exe), options=opts)

        self._save_session_headers()

    def quit(self):
        if self._driver:
            try:
                self._driver.quit()
                self.logger.info("FirefoxDriver session terminated.")
            except Exception as e:
                self.logger.warning(f"Error during driver quit: {e}")
            finally:
                self._driver = None
        if not self._context_managed:
            self._stop_logging()

    def _get_driver_path(self) -> str:
        if self.config.driver_path:
            return str(self.config.driver_path)
        elif shutil.which("geckodriver"):
            return "geckodriver"
        else:
            from webdriver_manager.firefox import GeckoDriverManager
            return GeckoDriverManager().install()

    def _load_session_headers(self) -> dict:
        path = self.config.session_path
        if not path:
            return {}

        policy = FSOOpsPolicy(exist=ExistencePolicy(must_exist=True))
        try:
            headers = JsonFileIO(path, ops_policy=policy).read().get("headers", {})
            return headers
        except Exception as e:
            self.logger.warning(f"Failed to load session headers: {e}")
            return {}

    def _save_session_headers(self):
        if not self.config.session_path or not self._driver:
            return
        try:
            ua = self._driver.execute_script("return navigator.userAgent")
            langs = self._driver.execute_script("return navigator.languages")
            headers = {
                "User-Agent": ua,
                "Accept-Language": ",".join(langs) if langs else None,
            }
            policy = FSOOpsPolicy(exist=ExistencePolicy(create_if_missing=True))
            io = JsonFileIO(self.config.session_path, ops_policy=policy)
            data = io.read() if self.config.session_path.is_file() else {}
            data["headers"] = {**data.get("headers", {}), **headers}
            io.write(data)
        except Exception as e:
            self.logger.warning(f"Failed to save session headers: {e}")

    # ------------------------------------------------------------------
    # Context management & cleanup
    # ------------------------------------------------------------------
    def __enter__(self) -> "FirefoxDriver":
        if not self._logging_active:
            self.logger = self._log_context.__enter__()
            self._logging_active = True
        self._context_managed = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.quit()
        finally:
            self._stop_logging(exc_type, exc_val, exc_tb)
            self._context_managed = False

    def _stop_logging(self, exc_type=None, exc_val=None, exc_tb=None):
        if self._logging_active:
            self._log_context.__exit__(exc_type, exc_val, exc_tb)
            self._logging_active = False

    def __del__(self):
        try:
            self.quit()
        except Exception:
            pass
