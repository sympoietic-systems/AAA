"""Custom exceptions and FastAPI error handlers.

Provides a unified error-handling story for service-layer errors,
eliminating repetitive try/except blocks in route handlers.
"""

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class ServiceException(HTTPException):
    """Raised by service-layer code when a business logic error occurs.

    Usage:
        raise ServiceException(message="Belief not found", status_code=404)
        raise ServiceException("Invalid parameters")  # defaults to 400
    """

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(status_code=status_code, detail=message)
        self.message = message

    def __str__(self) -> str:
        return f"ServiceException({self.status_code}): {self.message}"


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

    @app.exception_handler(ServiceException)
    async def service_exception_handler(request: Request, exc: ServiceException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"status": "error", "detail": exc.message},
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=500,
            content={"status": "error", "detail": str(exc)},
        )
