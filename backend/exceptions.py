"""Predictable application errors returned by the FastAPI boundary."""

from __future__ import annotations


class AppError(Exception):
    code = "APPLICATION_ERROR"
    status_code = 500

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        self.message = message
        self.detail = detail
        super().__init__(message)


class ServiceUnavailableError(AppError):
    code = "SERVICE_UNAVAILABLE"
    status_code = 503


class ModelUnavailableError(ServiceUnavailableError):
    code = "MODEL_UNAVAILABLE"


class ExternalServiceError(ServiceUnavailableError):
    code = "EXTERNAL_SERVICE_ERROR"


class ConversationNotFoundError(AppError):
    code = "CONVERSATION_NOT_FOUND"
    status_code = 404
