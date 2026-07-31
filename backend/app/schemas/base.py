"""Shared Pydantic schema bases for API request/response models.

Endpoint-specific schemas (added alongside future endpoint modules) should
inherit from `ORJSONModel` rather than `pydantic.BaseModel` directly, so
serialization behavior stays consistent across the API.

`PaginationParams`/`PaginatedResponse` predate the REST APIs task (already
built); `SortParams` is new, added by that task alongside
`app.api.pagination.paginate_and_sort` — see that module's own docstring
for how the three fit together.
"""

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

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


class SortParams(ORJSONModel):
    sort_by: str | None = None
    sort_order: Literal["asc", "desc"] = "asc"
