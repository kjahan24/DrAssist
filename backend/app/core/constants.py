"""Cross-cutting, environment-independent constants.

Only truly global values belong here (header names, default pagination
limits, timeouts). Domain-specific enums belong in
`app/domain/value_objects/`, not here.
"""

from enum import StrEnum


class RequestHeader(StrEnum):
    REQUEST_ID = "X-Request-ID"
    CORRELATION_ID = "X-Correlation-ID"


DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

DEFAULT_TIMEOUT_SECONDS = 30
