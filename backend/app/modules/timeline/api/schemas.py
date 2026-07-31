"""Pydantic v2 response schema for the Timeline module.

There is no request/create schema — this module is entirely read-only
(see `container.py`'s own scope note); the only "input" is the query
parameters `api/router.py` declares directly on its one endpoint.

`TimelineEventResponse` never exposes a domain entity (there isn't
one — see `application/dto.py`'s own docstring); it mirrors
`TimelineEventDTO` field-for-field via `model_validate`.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from app.modules.timeline.domain.enums import (
    TimelineEventCategory,
    TimelineEventType,
    TimelineSourceModule,
)
from app.schemas.base import ORJSONModel


class TimelineEventResponse(ORJSONModel):
    id: UUID
    event_type: TimelineEventType
    event_category: TimelineEventCategory
    patient_id: UUID
    organization_id: UUID
    reference_id: UUID
    title: str
    summary: str | None = None
    event_datetime: datetime
    source_module: TimelineSourceModule
    icon_key: str
    color_key: str
    visit_id: UUID | None = None
    appointment_id: UUID | None = None
    created_by: UUID | None = None
    metadata: dict[str, Any] | None = None
    chronological_order: int
