"""Base exception for domain-layer rule violations.

`DomainError` and its subclasses carry no HTTP knowledge (no status code) —
that translation happens at the Application/API boundary, once, so the
same domain rule behaves identically whether it's violated via HTTP, a
Celery task, or a script. See
`docs/backend-architecture/06_configuration_logging_exceptions.md`.
"""


class DomainError(Exception):
    """Base class for every exception raised by a domain entity or value object."""
