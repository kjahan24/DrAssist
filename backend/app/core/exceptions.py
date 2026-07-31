"""Application-wide exception hierarchy.

These are structural base classes only — they carry no business rules.
Concrete domain errors should subclass from here inside
`app/domain/` or `app/application/` so the global error handler
(`app/middlewares/error_handler.py`) can translate them to HTTP responses
in one place.
"""


class AppError(Exception):
    """Base class for all application-raised errors."""

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.error_code)
        self.message = message or self.error_code


class BadRequestError(AppError):
    status_code = 400
    error_code = "bad_request"


class NotFoundError(AppError):
    status_code = 404
    error_code = "not_found"


class ValidationError(AppError):
    status_code = 422
    error_code = "validation_error"


class UnauthorizedError(AppError):
    status_code = 401
    error_code = "unauthorized"


class ForbiddenError(AppError):
    status_code = 403
    error_code = "forbidden"


class ConflictError(AppError):
    status_code = 409
    error_code = "conflict"


class ServiceUnavailableError(AppError):
    status_code = 503
    error_code = "service_unavailable"
