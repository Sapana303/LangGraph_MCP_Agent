"""Shared, file-only logging that is safe for MCP stdio subprocesses."""

from __future__ import annotations

import logging
import json
from logging.handlers import RotatingFileHandler

from backend.config import PROJECT_ROOT


LOG_FILE = PROJECT_ROOT / "logs" / "backend.log"


class JsonFormatter(logging.Formatter):
    """Keep logs machine-readable without recording private prompt/document data."""

    def format(self, record: logging.LogRecord) -> str:
        from backend.request_context import request_id

        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "service": "backend",
            "request_id": request_id.get(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


class FrontendJsonFormatter(logging.Formatter):
    """Format browser event logs separately from backend service logs."""

    def format(self, record: logging.LogRecord) -> str:
        from backend.request_context import request_id

        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "service": "web",
            "request_id": request_id.get(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        return json.dumps(payload, ensure_ascii=True)


def get_logger(name: str) -> logging.Logger:
    """Return a logger backed by a rotating file, without writing to MCP stdout."""
    root = logging.getLogger()
    if not any(getattr(handler, "_mcp_agent_log", False) for handler in root.handlers):
        LOG_FILE.parent.mkdir(exist_ok=True)
        handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        handler._mcp_agent_log = True
        handler.setFormatter(JsonFormatter())
        root.addHandler(handler)
        root.setLevel(logging.INFO)
    return logging.getLogger(name)


def get_frontend_logger(name: str) -> logging.Logger:
    """Return a dedicated rotating logger for events reported by the React UI."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not any(getattr(handler, "_web_frontend_log", False) for handler in logger.handlers):
        log_file = PROJECT_ROOT / "logs" / "frontend.log"
        log_file.parent.mkdir(exist_ok=True)
        handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        handler._web_frontend_log = True
        handler.setFormatter(FrontendJsonFormatter())
        logger.addHandler(handler)
    return logger
