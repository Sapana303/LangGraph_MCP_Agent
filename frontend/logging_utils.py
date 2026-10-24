"""File-based frontend logging for Streamlit operations."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def get_logger(name: str) -> logging.Logger:
    root = logging.getLogger()
    if not any(getattr(handler, "_frontend_log", False) for handler in root.handlers):
        log_file = Path(__file__).resolve().parents[1] / "logs" / "frontend.log"
        log_file.parent.mkdir(exist_ok=True)
        handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        handler._frontend_log = True
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        root.addHandler(handler)
        root.setLevel(logging.INFO)
    return logging.getLogger(name)
