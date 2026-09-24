"""Framework-independent domain error taxonomy."""

from collections.abc import Mapping
from typing import Final


class GlitchError(Exception):
    def __init__(
        self,
        message: str,
        *,
        kind: str = "service_error",
        status_code: int = 400,
        entity: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.kind = kind
        self.status_code = status_code
        self.entity = entity
        self.details = details or {}


class ServiceException(GlitchError):
    """Compatibility error for callers that still choose an HTTP status."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message, kind="service_error", status_code=status_code)

    def __str__(self) -> str:
        return f"ServiceException({self.status_code}): {self.message}"


class ValidationGlitch(GlitchError):
    def __init__(self, message: str, *, entity: str | None = None, details: dict[str, object] | None = None) -> None:
        super().__init__(message, kind="validation_error", status_code=400, entity=entity, details=details)


class ConstraintViolation(GlitchError):
    def __init__(self, message: str, *, entity: str | None = None, details: dict[str, object] | None = None) -> None:
        super().__init__(message, kind="constraint_violation", status_code=409, entity=entity, details=details)


class ResourceNotFound(GlitchError):
    def __init__(self, message: str, *, entity: str | None = None, details: dict[str, object] | None = None) -> None:
        super().__init__(message, kind="not_found", status_code=404, entity=entity, details=details)


class SecurityViolation(GlitchError):
    def __init__(
        self,
        message: str = "Access denied: security violation",
        *,
        entity: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message, kind="security_violation", status_code=403, entity=entity, details=details)


class ProviderGlitch(GlitchError):
    def __init__(self, message: str, *, entity: str | None = None, details: dict[str, object] | None = None) -> None:
        super().__init__(message, kind="provider_glitch", status_code=502, entity=entity, details=details)


GLITCH_TYPES: Final[dict[str, type[GlitchError]]] = {
    "validation_error": ValidationGlitch,
    "constraint_violation": ConstraintViolation,
    "not_found": ResourceNotFound,
    "security_violation": SecurityViolation,
    "provider_glitch": ProviderGlitch,
}


def glitch_from_result(result: Mapping[str, object]) -> GlitchError:
    """Translate a service error result into its domain exception."""
    message_value = result.get("message", "Unknown error")
    message = message_value if isinstance(message_value, str) else "Unknown error"
    kind_value = result.get("kind", "service_error")
    kind = kind_value if isinstance(kind_value, str) else "service_error"
    error_type = GLITCH_TYPES.get(kind)
    if error_type is None:
        return ServiceException(message)
    entity_value = result.get("entity")
    entity = entity_value if isinstance(entity_value, str) else None
    details_value = result.get("details")
    details = dict(details_value) if isinstance(details_value, Mapping) else None
    return error_type(message, entity=entity, details=details)
