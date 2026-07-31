"""Global exception -> HTTP response translation.

Registers handlers so every `AppError` raised anywhere in the application
(services, use cases, repositories) resolves to a consistent JSON error
shape, instead of each endpoint needing its own try/except.

The REST API module additionally registers a handler for
`app.shared.domain.exceptions.DomainError` — the common base class every
domain exception across all ~25 backend modules already inherits from
(confirmed: every module's own `domain/exceptions.py` built so far
imports and subclasses it). With dozens of modules and, in total,
well over a hundred distinct domain exception classes, requiring each of
the ~150+ API endpoint functions to `try/except` its own module's
specific exceptions and re-raise the matching `AppError` subclass would
be significant, repetitive boilerplate — see rule 9/10 (small,
maintainable, not over-engineered). Instead, this one handler maps by a
naming convention this codebase has already applied *consistently*,
turn after turn, across every module: exception class names containing
"NotFound" -> 404; names signaling a conflict with the current state of
an existing resource ("Duplicate", "AlreadyExists", "Transition"
covering every `InvalidXStatusTransitionError`/`InvalidXTransitionError`,
"Immutable", "Inactive") -> 409; everything else (required-field,
mismatch, invalid-format, not-registered, scope-consistency violations)
-> 422, the correct default for "well-formed request, semantically
invalid" per `app.core.exceptions.ValidationError`'s own docstring.
This is a deliberate, disclosed heuristic, not an exhaustive per-class
registry — reasonable engineers could place a handful of borderline
exception names differently; it is documented here precisely so it can
be audited and adjusted.
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import AppError, ConflictError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.shared.domain.exceptions import DomainError

logger = get_logger(__name__)

_CONFLICT_KEYWORDS = ("Duplicate", "AlreadyExists", "Transition", "Immutable", "Inactive")


def _map_domain_error(exc: DomainError) -> AppError:
    name = type(exc).__name__
    message = str(exc)
    if "NotFound" in name:
        return NotFoundError(message)
    if any(keyword in name for keyword in _CONFLICT_KEYWORDS):
        return ConflictError(message)
    return ValidationError(message)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "app_error",
            error_code=exc.error_code,
            message=exc.message,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"error_code": exc.error_code, "message": exc.message},
        )

    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        return await handle_app_error(request, _map_domain_error(exc))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error_code": "validation_error",
                "message": "Invalid request",
                "details": exc.errors(),
            },
        )

    @app.exception_handler(Exception)
    async def handle_unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled_exception", path=request.url.path, exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error_code": "internal_error", "message": "Internal server error"},
        )
