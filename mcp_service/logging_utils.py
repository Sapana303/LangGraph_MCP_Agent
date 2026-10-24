"""File-only logging for the MCP service; never write logs to MCP stdout."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from mcp_service.config import PROJECT_ROOT


def get_logger(name: str) -> logging.Logger:
    root = logging.getLogger()
    if not any(getattr(handler, "_mcp_service_log", False) for handler in root.handlers):
        log_file = PROJECT_ROOT / "logs" / "mcp-service.log"
        log_file.parent.mkdir(exist_ok=True)
        handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        handler._mcp_service_log = True
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        root.addHandler(handler)
        root.setLevel(logging.INFO)
    return logging.getLogger(name)
