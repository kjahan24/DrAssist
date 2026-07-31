"""Shared Pydantic schema bases for API request/response models.

Endpoint-specific schemas (added alongside future endpoint modules) should
inherit from `ORJSONModel` rather than `pydantic.BaseModel` directly, so
serialization behavior stays consistent across the API.

`PaginationParams`/`PaginatedResponse` predate the REST APIs task (already
built); `SortParams` is new, added by that task alongside
`app.api.pagination.paginate_and_sort` — see that module's own docstring
for how the three fit together.

`PaginatedResponse.page`/`page_size`/`total_pages` (added by the Search &
Filtering module) are computed fields derived from `offset`/`limit`/`total`
— purely additive to the response body, so every existing caller of every
existing paginated endpoint keeps working unchanged; only new consumers
that read the extra keys are affected. `offset`/`limit` remain the actual
query-parameter contract (`PaginationParams`); `page`/`page_size` are a
response-side convenience the Search & Filtering module's spec calls for.

`SearchFilterParams` (also added by the Search & Filtering module) is the
generic, cross-module half of that module's query parameters — a free-text
term plus `created_at`/`updated_at` date ranges plus a soft-delete escape
hatch, the same four concerns every one of the thirteen in-scope modules
needs regardless of its own domain shape. Module-specific filters (e.g.
`status: PatientStatus | None`, `doctor_id: UUID | None`) stay declared
directly on each module's own router endpoint, exactly like today's
un-searched list endpoints already do — this class does not attempt to
generalize those, since their type varies per module (see
`app.api.search_params` for how the two combine, and
`app.infrastructure.database.query_utils` for the SQLAlchemy helpers each
repository's `search()` method uses to apply them).
"""

from datetime import datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, computed_field

T = TypeVar("T")


class ORJSONModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PaginationParams(ORJSONModel):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=200)


class PaginatedResponse(ORJSONModel, Generic[T]):
    items: list[T]
    total: int
    offset: int
    limit: int

    @computed_field  # type: ignore[prop-decorator]
    @property
    def page(self) -> int:
        return (self.offset // self.limit) + 1 if self.limit else 1

    @computed_field  # type: ignore[prop-decorator]
    @property
    def page_size(self) -> int:
        return self.limit

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_pages(self) -> int:
        if self.limit <= 0:
            return 0
        return -(-self.total // self.limit)


class SortParams(ORJSONModel):
    sort_by: str | None = None
    sort_order: Literal["asc", "desc"] = "asc"


class SearchFilterParams(ORJSONModel):
    q: str | None = Field(default=None, min_length=1, max_length=200)
    created_from: datetime | None = None
    created_to: datetime | None = None
    updated_from: datetime | None = None
    updated_to: datetime | None = None
    include_deleted: bool = False
