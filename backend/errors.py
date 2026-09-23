"""Framework-independent domain errors."""


class GlitchError(Exception):
    def __init__(
        self,
        message: str,
        *,
        kind: str = "service_error",
        status_code: int = 400,
        entity: str | None = None,
        details: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.kind = kind
        self.status_code = status_code
        self.entity = entity
        self.details = details or {}


class ServiceException(GlitchError):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message, kind="service_error", status_code=status_code)

    def __str__(self) -> str:
        return f"ServiceException({self.status_code}): {self.message}"
