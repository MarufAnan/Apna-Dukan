"""
utils/logger.py
Centralized logging configuration for ShopEase POS.
Every module imports get_logger() to obtain a consistently configured logger
that writes to logs/shopease.log (rotating) and echoes warnings+ to console.
"""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "shopease.log")

_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_configured = False


def _configure_root() -> None:
    global _configured
    if _configured:
        return
    root = logging.getLogger("shopease")
    root.setLevel(logging.DEBUG)

    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(_FORMAT))

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(logging.Formatter(_FORMAT))

    root.addHandler(file_handler)
    root.addHandler(console_handler)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a named logger under the 'shopease' hierarchy."""
    _configure_root()
    return logging.getLogger(f"shopease.{name}")
