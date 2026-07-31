"""Shared pagination/sorting/filtering support for every module's router.

`Pagination`/`Sorting` are FastAPI dependency aliases — `Depends()` on a
plain `ORJSONModel` binds its fields to individual query parameters
(`?offset=0&limit=20&sort_by=...&sort_order=asc`) with no extra
boilerplate, so every endpoint that lists a resource takes the exact
same two query-parameter groups.

`paginate_and_sort` is intentionally simple: it sorts and slices an
*already-fetched* Python list, rather than pushing `ORDER BY`/`OFFSET`/
`LIMIT` down into SQL. This is a deliberate scope boundary for this
task ("Do NOT modify domain logic" — most existing query service methods
return an unbounded `list[...]`, and only a few, built with pagination
already in mind, accept `offset`/`limit` natively; changing every other
module's own query service to add native support would mean modifying
~20 previous modules' application layers, which rule 1 reserves for
"absolutely necessary"). For the request volumes multi-tenant clinic
data implies (per-organization/per-patient/per-doctor collections, not
platform-wide unbounded scans), in-memory pagination is a reasonable,
disclosed first pass — a query service gaining native `offset`/`limit`
support later is a non-breaking, purely additive change this shape
already anticipates.

"Filtering hooks" (per this task's own Implement checklist) are each
endpoint's own optional query parameters (e.g. `status: AppointmentStatus
| None`), applied by the endpoint itself via a plain list comprehension
*before* calling `paginate_and_sort` — there is no generic filter-
expression parser here; inventing one without a stated need would be
over-engineering (rule 10).
"""

from collections.abc import Callable
from typing import Annotated, Any, TypeVar

from fastapi import Depends

from app.core.exceptions import BadRequestError
from app.schemas.base import PaginatedResponse, PaginationParams, SortParams

Pagination = Annotated[PaginationParams, Depends()]
Sorting = Annotated[SortParams, Depends()]

T = TypeVar("T")


def paginate_and_sort(
    items: list[T],
    *,
    pagination: PaginationParams,
    sorting: SortParams,
    allowed_sort_fields: frozenset[str],
    sort_key: Callable[[T], Any] | None = None,
) -> PaginatedResponse[T]:
    """`sort_key` defaults to `getattr(item, sorting.sort_by)` — pass an
    explicit one when the list holds dicts/dataclasses without attribute
    access, or when the sortable label doesn't match the underlying
    field name 1:1.
    """
    if sorting.sort_by is not None:
        if sorting.sort_by not in allowed_sort_fields:
            raise BadRequestError(
                f"cannot sort by {sorting.sort_by!r}; allowed fields: "
                f"{sorted(allowed_sort_fields)}"
            )
        key = sort_key or (lambda item: getattr(item, sorting.sort_by))  # type: ignore[arg-type]
        items = sorted(items, key=key, reverse=sorting.sort_order == "desc")

    total = len(items)
    page = items[pagination.offset : pagination.offset + pagination.limit]
    return PaginatedResponse(
        items=page, total=total, offset=pagination.offset, limit=pagination.limit
    )
