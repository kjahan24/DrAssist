"""`TimelineQueryService` — the read API this whole module exists to
serve: validate the patient (and, when given, that `visit_id`/
`appointment_id` filters actually belong to that patient — see below),
delegate to `TimelineAggregationService` for the cross-module fan-out,
apply the filters that can't be pushed down to a peer module's own SQL
query (date range, `document_category` — both operate on the unified
`TimelineEventDTO` shape only after mapping), sort, assign
`chronological_order`, and paginate.

Ownership validation for `visit_id`/`appointment_id` filters is a
deliberate security measure, not a convenience check: without it, a
caller could request `patient_id=<their own, authorized patient>` but
`visit_id=<belongs to a different patient>`, and
`TimelineAggregationService` would happily call a peer module's
visit-scoped fetch (e.g. `DocumentQueryPort.list_documents_for_visit`)
and merge that *other* patient's records into this response — a genuine
cross-patient data leak. Both are treated as "cross-tenant/cross-patient
= not found", the same pattern `app.api.deps.ensure_same_organization`
already establishes at the API layer, applied here at the application
layer since this service has no HTTP request to inspect.

Sorting/pagination are intentionally simple, in-memory operations over
the already-aggregated list — the same disclosed tradeoff
`app.api.pagination.paginate_and_sort`'s own docstring documents for
this codebase, unavoidable here since events are merged from independent
modules with no shared SQL query to `ORDER BY`/`LIMIT` against.
`chronological_order` is assigned only after the full filtered list is
sorted — it reflects each event's absolute position across every page,
not merely its position within the current page.
"""

from dataclasses import replace
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.modules.appointment.public.interfaces import AppointmentQueryPort
from app.modules.documents.domain.enums import DocumentCategory
from app.modules.patient.public.interfaces import PatientQueryPort
from app.modules.timeline.application.dto import (
    TimelineEventDTO,
    TimelineFilterInput,
    TimelinePageDTO,
)
from app.modules.timeline.application.services.timeline_aggregation_service import (
    TimelineAggregationService,
)
from app.modules.timeline.domain.enums import TimelineEventType
from app.modules.timeline.domain.exceptions import (
    AppointmentOwnershipMismatchError,
    PatientNotFoundError,
    VisitOwnershipMismatchError,
)
from app.modules.visit.public.interfaces import VisitQueryPort


class TimelineQueryService:
    def __init__(
        self,
        *,
        aggregation_service: TimelineAggregationService,
        patient_query_port: PatientQueryPort,
        visit_query_port: VisitQueryPort,
        appointment_query_port: AppointmentQueryPort,
    ) -> None:
        self._aggregation = aggregation_service
        self._patients = patient_query_port
        self._visits = visit_query_port
        self._appointments = appointment_query_port

    async def get_patient_timeline(
        self,
        patient_id: UUID,
        *,
        filters: TimelineFilterInput,
        offset: int = 0,
        limit: int = 20,
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> TimelinePageDTO:
        patient_summary = await self._patients.get_patient_summary(patient_id)
        if patient_summary is None:
            raise PatientNotFoundError(patient_id)

        if filters.visit_id is not None:
            visit_summary = await self._visits.get_visit_summary(filters.visit_id)
            if visit_summary is None or visit_summary.patient_id != patient_id:
                raise VisitOwnershipMismatchError(filters.visit_id)

        if filters.appointment_id is not None:
            appointment_summary = await self._appointments.get_appointment_summary(
                filters.appointment_id
            )
            if appointment_summary is None or appointment_summary.patient_id != patient_id:
                raise AppointmentOwnershipMismatchError(filters.appointment_id)

        events = await self._aggregation.collect_for_patient(patient_id, filters=filters)
        events = _apply_date_range(events, date_from=filters.date_from, date_to=filters.date_to)
        events = _apply_document_category(events, category=filters.document_category)

        events.sort(
            key=lambda e: (e.event_datetime, e.source_module.value, str(e.reference_id)),
            reverse=(sort_order == "desc"),
        )
        events = [
            replace(event, chronological_order=index) for index, event in enumerate(events, start=1)
        ]

        total = len(events)
        page = events[offset : offset + limit]
        return TimelinePageDTO(items=page, total=total, offset=offset, limit=limit)


def _apply_date_range(
    events: list[TimelineEventDTO], *, date_from: datetime | None, date_to: datetime | None
) -> list[TimelineEventDTO]:
    if date_from is not None:
        events = [e for e in events if e.event_datetime >= date_from]
    if date_to is not None:
        events = [e for e in events if e.event_datetime <= date_to]
    return events


def _apply_document_category(
    events: list[TimelineEventDTO], *, category: DocumentCategory | None
) -> list[TimelineEventDTO]:
    """Unlike date range (which narrows every event type), a
    `document_category` scopes the whole timeline down to *only*
    `DOCUMENT` events of that category — the natural reading of a filter
    named "Document Category" sitting alongside "Event Type" in this
    task's own Filtering section: a caller selecting one is asking to
    see just that, not "every event, but any documents among them
    restricted further"."""
    if category is None:
        return events
    return [
        e
        for e in events
        if e.event_type is TimelineEventType.DOCUMENT
        and e.metadata is not None
        and e.metadata.get("category") == category.value
    ]
