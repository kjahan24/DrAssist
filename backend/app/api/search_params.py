"""Shared FastAPI dependency + sort-field validation for the Search &
Filtering module — the API-layer counterpart to
`app.infrastructure.database.query_utils` (SQL-building helpers) and
`app.schemas.base.SearchFilterParams` (the generic query-parameter shape).

`SearchFilters` follows the exact same `Annotated[Model, Depends()]` shape
as `app.api.pagination`'s `Pagination`/`Sorting` — every module's router
adds `filters: SearchFilters` alongside its existing `pagination:
Pagination`/`sorting: Sorting` parameters to pick up
`?q=...&created_from=...&created_to=...&updated_from=...&updated_to=...&
include_deleted=...` with no extra boilerplate.

`resolve_sort_field` mirrors `app.api.pagination.paginate_and_sort`'s own
inline validation (same error message shape, same `BadRequestError`) —
kept as a small shared function purely so thirteen modules don't each
repeat the same four-line `if sort_by not in allowed: raise ...` block.
"""

from typing import Annotated

from fastapi import Depends

from app.core.exceptions import BadRequestError
from app.schemas.base import SearchFilterParams

SearchFilters = Annotated[SearchFilterParams, Depends()]


def resolve_sort_field(
    sort_by: str | None, *, allowed_sort_fields: frozenset[str], default_field: str
) -> str:
    """Returns `default_field` when the caller didn't ask for a specific
    sort, otherwise `sort_by` itself once validated against
    `allowed_sort_fields`. The returned string is a *logical* field name —
    each repository's `search()` method maps it to an actual SQLAlchemy
    column via its own `_SORT_COLUMNS` dict; this function never touches
    SQLAlchemy, keeping ORM concerns out of the API layer.
    """
    if sort_by is None:
        return default_field
    if sort_by not in allowed_sort_fields:
        raise BadRequestError(
            f"cannot sort by {sort_by!r}; allowed fields: {sorted(allowed_sort_fields)}"
        )
    return sort_by
