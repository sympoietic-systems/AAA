import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from backend.errors import GlitchError, SecurityViolation, ServiceException, ValidationGlitch, glitch_from_result

logger = logging.getLogger("aaa.exceptions")
__all__ = ["ServiceException", "raise_if_error", "register_error_handlers"]


def _glitch_response(exc: GlitchError) -> JSONResponse:
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


def raise_if_error(result: dict[str, object]) -> dict[str, object]:
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
        raise glitch_from_result(result)
    return result


def register_error_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI app instance."""

    @app.exception_handler(GlitchError)
    async def service_exception_handler(request: Request, exc: GlitchError) -> JSONResponse:
        logger.warning(
            "Domain error on %s %s [%d]: %s",
            request.method,
            request.url.path,
            exc.status_code,
            exc.message,
        )
        return _glitch_response(exc)

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        logger.error(
            "ValueError on %s %s: %s",
            request.method,
            request.url.path,
            str(exc),
        )
        error = ValidationGlitch("Invalid request value")
        return _glitch_response(error)

    @app.exception_handler(PermissionError)
    async def permission_error_handler(request: Request, exc: PermissionError) -> JSONResponse:
        logger.warning(
            "Security violation on %s %s: %s",
            request.method,
            request.url.path,
            str(exc),
        )
        return _glitch_response(SecurityViolation())

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        if exc.status_code >= 500:
            logger.error(
                "HTTPException %d on %s %s: %s",
                exc.status_code,
                request.method,
                request.url.path,
                exc.detail,
            )
        message = "Internal server error" if exc.status_code >= 500 else str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "kind": "http_error",
                "message": message,
                "detail": message,
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
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
