"""Shared Pydantic schema bases for API request/response models.

Endpoint-specific schemas (added alongside future endpoint modules) should
inherit from `ORJSONModel` rather than `pydantic.BaseModel` directly, so
serialization behavior stays consistent across the API.
"""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORJSONModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PaginationParams(ORJSONModel):
    offset: int = 0
    limit: int = 20


class PaginatedResponse(ORJSONModel, Generic[T]):
    items: list[T]
    total: int
    offset: int
    limit: int
