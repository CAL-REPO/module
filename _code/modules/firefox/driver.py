# -*- coding: utf-8 -*-
# firefox/driver.py - Firefox WebDriver 캡슐화 클래스 with LoggerPolicy 설정 기반 적용

from __future__ import annotations

import shutil
from typing import Any, Optional
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

from firefox.config import FirefoxConfig
from cfg_utils import ConfigLoader
from fso_utils import JsonFileIO, FSOOpsPolicy, ExistencePolicy
from log_utils import LogManager


class FirefoxDriver:
    def __init__(self, cfg_like: FirefoxConfig | dict | str, **overrides: Any):
        self.config: FirefoxConfig = ConfigLoader(cfg_like).as_model(FirefoxConfig, **overrides)
        self._driver: Optional[webdriver.Firefox] = None

        log_file = self._get_log_file()
        self.logger = LogManager("firefox", log_file=log_file, policy=self.config.logger).setup()
        self.logger.debug("FirefoxDriver initialized.")

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

    def _get_driver_path(self) -> str:
        if self.config.driver_path:
            return str(self.config.driver_path)
        elif shutil.which("geckodriver"):
            return "geckodriver"
        else:
            from webdriver_manager.firefox import GeckoDriverManager
            return GeckoDriverManager().install()

    def _get_log_file(self) -> Optional[Path]:
        if self.config.log_dir:
            self.config.log_dir.mkdir(parents=True, exist_ok=True)
            log_name = datetime.now().strftime("%Y-%m-%d.log")
            log_path = self.config.log_dir / log_name
            return log_path
        return None

    def _load_session_headers(self) -> dict:
        path = self.config.session_path
        if not path:
            return {}

        policy = FSOOpsPolicy(exist=ExistencePolicy(must_exist=True))
        try:
            headers = JsonFileIO(path, policy=policy).read().get("headers", {})
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
            io = JsonFileIO(self.config.session_path, policy=policy)
            data = io.read() if self.config.session_path.is_file() else {}
            data["headers"] = {**data.get("headers", {}), **headers}
            io.write(data)
        except Exception as e:
            self.logger.warning(f"Failed to save session headers: {e}")