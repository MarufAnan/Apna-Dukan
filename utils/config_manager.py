"""
utils/config_manager.py
Loads and persists config/config.json (shop details, theme, printer, etc).
This is the single source of truth for application configuration and is
used by the setup wizard, settings screen, and invoice generator.
"""
from __future__ import annotations

import json
import os
from typing import Any

from utils.logger import get_logger

logger = get_logger("config")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.json")

DEFAULT_CONFIG: dict[str, Any] = {
    "shop_name": "",
    "owner_name": "",
    "phone": "",
    "address": "",
    "gst_number": "",
    "logo_path": "",
    "default_printer": "",
    "theme": "dark",
    "color_theme": "blue",
    "currency_symbol": "\u20b9",
    "invoice_prefix": "INV",
    "low_stock_default": 5,
    "first_run_complete": False,
    "backup_on_exit": True,
}


class ConfigManager:
    """Simple JSON-backed configuration store with dict-like access."""

    def __init__(self, path: str = CONFIG_PATH):
        self.path = path
        self._data: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        if not os.path.exists(self.path):
            self._data = dict(DEFAULT_CONFIG)
            self.save()
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self._data = {**DEFAULT_CONFIG, **json.load(f)}
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to read config, using defaults: %s", exc)
            self._data = dict(DEFAULT_CONFIG)

    def save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except OSError as exc:
            logger.error("Failed to write config: %s", exc)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any, save: bool = True) -> None:
        self._data[key] = value
        if save:
            self.save()

    def update(self, values: dict[str, Any], save: bool = True) -> None:
        self._data.update(values)
        if save:
            self.save()

    def as_dict(self) -> dict[str, Any]:
        return dict(self._data)


config = ConfigManager()
