"""Data Transfer Objects for the Timeline module's application layer.

`TimelineEventDTO` is the unified read model this whole module exists to
produce — never persisted (see `container.py`'s own scope note), always
built fresh from the 10 peer modules' own summary DTOs by
`TimelineAggregationService`. `document_category` on `TimelineFilterInput`
reuses `app.modules.documents.domain.enums.DocumentCategory` directly (a
plain value type, not a cross-layer import of behavior) rather than
redefining an identical enum here — it is only ever meaningful for
`TimelineEventType.DOCUMENT` events.

`TimelinePageDTO` mirrors `app.schemas.base.PaginatedResponse`'s fields
exactly (`items`/`total`/`offset`/`limit`) so `api/schemas.py` can adapt
it into that Pydantic response model with a single `model_validate` —
but stays a plain dataclass here, since the application layer never
depends on Pydantic or any other API-layer type.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from app.modules.documents.domain.enums import DocumentCategory
from app.modules.timeline.domain.enums import (
    TimelineEventCategory,
    TimelineEventType,
    TimelineSourceModule,
)


@dataclass(frozen=True, slots=True)
class TimelineEventDTO:
    event_id: UUID
    event_type: TimelineEventType
    event_category: TimelineEventCategory
    patient_id: UUID
    organization_id: UUID
    reference_id: UUID
    title: str
    summary: str | None
    event_datetime: datetime
    source_module: TimelineSourceModule
    icon_key: str
    color_key: str
    visit_id: UUID | None = None
    appointment_id: UUID | None = None
    created_by: UUID | None = None
    metadata: dict[str, Any] | None = None
    chronological_order: int = 0

    @property
    def id(self) -> UUID:
        """Alias for `event_id` — see `AppointmentSummaryDTO.id`'s own
        docstring in `app.modules.appointment.application.dto` for the
        full reasoning (identical situation in every module)."""
        return self.event_id


@dataclass(frozen=True, slots=True)
class TimelineFilterInput:
    event_types: frozenset[TimelineEventType] | None = None
    source_modules: frozenset[TimelineSourceModule] | None = None
    visit_id: UUID | None = None
    appointment_id: UUID | None = None
    document_category: DocumentCategory | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


@dataclass(frozen=True, slots=True)
class TimelinePageDTO:
    items: list[TimelineEventDTO]
    total: int
    offset: int
    limit: int
