"""Request IDs make one user action traceable across backend log entries."""

from __future__ import annotations

from contextvars import ContextVar


request_id: ContextVar[str] = ContextVar("request_id", default="system")
