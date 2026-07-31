"""Public DTOs — the only data shapes another module may depend on.

Re-exported from the application layer's `dto.py`, not redefined, so
there is exactly one definition of each shape. `TimelineFilterInput`/
`TimelinePageDTO` are exposed alongside `TimelineEventDTO` because
`TimelineQueryPort.get_patient_timeline` takes/returns them directly —
a caller needs all three to use the port at all. Domain enums
(`TimelineEventType`/`TimelineEventCategory`/`TimelineSourceModule`) are
*not* re-exported here — a consumer imports them straight from
`app.modules.timeline.domain.enums`, the same "peer domain enums are
plain value types, not behavior" exception every other module's own
DTOs already rely on (e.g. `MedicalDocumentSummaryDTO.category` is
`app.modules.documents.domain.enums.DocumentCategory`, imported directly
by this module's own `application/dto.py`).
"""

from app.modules.timeline.application.dto import (
    TimelineEventDTO,
    TimelineFilterInput,
    TimelinePageDTO,
)

__all__ = ["TimelineEventDTO", "TimelineFilterInput", "TimelinePageDTO"]
