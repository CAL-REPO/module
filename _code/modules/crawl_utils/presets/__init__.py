# -*- coding: utf-8 -*-
"""crawl_utils.presets v2.0"""

from typing import Dict, Any, Optional, Tuple, List, Callable

from .domains import DOMAIN_MAPPING
from .methods import METHOD_PATTERNS
from .sites import get_aliexpress_detail_preset, get_aliexpress_search_preset
from .webdrivers import WEBDRIVER_OVERRIDES, PROVIDER_SPECIFIC_FIELDS

PresetFunction = Callable[[], Dict[str, Any]]

_PRESET_FUNCTIONS: Dict[Tuple[str, str], PresetFunction] = {
    ("aliexpress", "detail"): get_aliexpress_detail_preset,
    ("aliexpress", "search"): get_aliexpress_search_preset,
}

def get_preset(site: str, method: str) -> Optional[Dict[str, Any]]:
    preset_func = _PRESET_FUNCTIONS.get((site, method))
    return preset_func() if preset_func else None

def list_presets() -> List[Tuple[str, str]]:
    return list(_PRESET_FUNCTIONS.keys())

def register_preset(site: str, method: str, preset_func: PresetFunction) -> None:
    _PRESET_FUNCTIONS[(site, method)] = preset_func

def has_preset(site: str, method: str) -> bool:
    return (site, method) in _PRESET_FUNCTIONS

def analyze_url(url: str) -> Tuple[str, str, str]:
    url_lower = url.lower()
    site = None
    region = None
    for site_name, config in DOMAIN_MAPPING.items():
        if any(domain in url_lower for domain in config["domains"]):
            site = site_name
            region = config["region"]
            break
    if not site or not region:
        raise ValueError(f"Cannot identify site/region from URL: {url}")
    method = None
    for method_name, patterns in METHOD_PATTERNS.items():
        if any(pattern in url_lower for pattern in patterns):
            method = method_name
            break
    if not method:
        raise ValueError(f"Cannot identify method from URL: {url}")
    return site, method, region

def get_webdriver_override(region: str, provider: str) -> Optional[Dict[str, Any]]:
    region_overrides = WEBDRIVER_OVERRIDES.get(region, {})
    return region_overrides.get(provider)

__all__ = [
    "get_preset", "list_presets", "register_preset", "has_preset",
    "analyze_url", "get_webdriver_override",
    "DOMAIN_MAPPING", "METHOD_PATTERNS", "WEBDRIVER_OVERRIDES", "PROVIDER_SPECIFIC_FIELDS",
    "get_aliexpress_detail_preset", "get_aliexpress_search_preset",
]
