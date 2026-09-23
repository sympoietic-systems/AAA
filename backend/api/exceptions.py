import logging

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from backend.errors import GlitchError, ServiceException

logger = logging.getLogger("aaa.exceptions")


def raise_if_error(result: dict) -> dict:
    """Convenience: raise ServiceException if result contains an error.

    Checks for the common service result pattern
    {'status': 'error', 'message': '...'} and raises a ServiceException.

    Args:
        result: A dict from a service method call.

    Returns:
        The result dict if no error.

    Raises:
        ServiceException: If result['status'] == 'error'.
    """
    if isinstance(result, dict) and result.get("status") == "error":
        raise ServiceException(
            message=result.get("message", "Unknown error"),
            status_code=400,
        )
    return result


def register_error_handlers(app):
    """Register global exception handlers on the FastAPI app instance."""

    @app.exception_handler(GlitchError)
    async def service_exception_handler(request: Request, exc: GlitchError):
        logger.warning(
            "ServiceException on %s %s [%d]: %s",
            request.method,
            request.url.path,
            exc.status_code,
            exc.message,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "kind": exc.kind,
                "message": exc.message,
                "detail": exc.message,
                "entity": exc.entity,
                "details": exc.details,
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        logger.error(
            "ValueError on %s %s: %s",
            request.method,
            request.url.path,
            str(exc),
        )
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "kind": "validation_error",
                "message": str(exc),
                "detail": str(exc),
            },
        )

    @app.exception_handler(PermissionError)
    async def permission_error_handler(request: Request, exc: PermissionError):
        logger.warning(
            "Security violation on %s %s: %s",
            request.method,
            request.url.path,
            str(exc),
        )
        return JSONResponse(
            status_code=403,
            content={
                "status": "error",
                "kind": "security_violation",
                "message": "Access denied: security violation",
                "detail": "Access denied: security violation",
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        # Allow standard HTTPExceptions to preserve their status code
        if isinstance(exc, HTTPException):
            if exc.status_code >= 500:
                logger.error(
                    "HTTPException %d on %s %s: %s",
                    exc.status_code,
                    request.method,
                    request.url.path,
                    exc.detail,
                )
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "status": "error",
                    "kind": "http_error",
                    "message": str(exc.detail),
                    "detail": str(exc.detail),
                },
            )

        # Full stack trace fidelity per protocols/GLITCH.md and protocols/SECURITY.md
        logger.exception(
            "Unhandled server crash on %s %s: %s",
            request.method,
            request.url.path,
            str(exc),
        )
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "kind": "internal_error",
                "message": "An unexpected internal server error occurred",
                "detail": "Internal server error",
            },
        )
