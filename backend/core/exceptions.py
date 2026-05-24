from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.logging import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    """Base application error with an HTTP status and machine-readable code."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        code: str = "app_error",
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(message)


class ConfigurationError(AppError):
    """Raised when required runtime configuration is missing or invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(
            message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="configuration_error",
        )


class ExternalServiceError(AppError):
    """Raised when Redis, ChromaDB, Ollama, or Spring APIs fail."""

    def __init__(self, message: str) -> None:
        super().__init__(
            message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="external_service_error",
        )


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _sanitize_validation_errors(exc: RequestValidationError) -> list[dict[str, Any]]:
    """Return validation errors without echoing rejected input values."""

    sanitized: list[dict[str, Any]] = []
    for error in exc.errors():
        sanitized.append(
            {
                "type": error.get("type"),
                "loc": error.get("loc"),
                "msg": error.get("msg"),
            }
        )
    return sanitized


def register_exception_handlers(app: FastAPI) -> None:
    """Register consistent JSON exception responses."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> ORJSONResponse:
        logger.warning(
            "app_error",
            code=exc.code,
            message=exc.message,
            path=request.url.path,
        )
        return ORJSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": _request_id(request),
                },
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> ORJSONResponse:
        details = _sanitize_validation_errors(exc)
        logger.warning("validation_error", path=request.url.path, errors=details)
        return ORJSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": {
                    "code": "validation_error",
                    "message": "Request validation failed.",
                    "details": details,
                    "request_id": _request_id(request),
                },
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": "http_error",
                    "message": exc.detail,
                    "request_id": _request_id(request),
                },
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> ORJSONResponse:
        logger.exception("unhandled_error", path=request.url.path, error=str(exc))
        return ORJSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "internal_server_error",
                    "message": "Internal server error.",
                    "request_id": _request_id(request),
                },
            },
        )
