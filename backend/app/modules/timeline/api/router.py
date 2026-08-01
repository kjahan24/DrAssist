"""HTTP routes for the Personal Health Timeline module.

Follows the pattern established in `app.modules.appointment.api.router`:
requires `CurrentUser` (reusing the already-built Authentication
dependency is not "implementing authentication" — the same distinction
this task's own exclusions draw); fetches the patient summary first and
calls `ensure_same_organization` before running the actual query, so a
cross-tenant `patient_id` 404s instead of leaking whether that patient
exists in another organization — the same "act on one resource by id"
pattern every other module's own `GET` endpoints already use, applied
here to `patient_id` as this module's one and only "resource".
Domain/application exceptions (`PatientNotFoundError`,
`VisitOwnershipMismatchError`, `AppointmentOwnershipMismatchError`) are
never caught here — `app.middlewares.error_handler`'s `DomainError`
handler translates them to the correct HTTP status uniformly.

One endpoint only: `GET /patients/{patient_id}`. `sort_order` defaults
to `"desc"` (newest first) — the natural default for a health timeline,
per this task's own "Support: Newest First, Oldest First" (both remain
selectable; nothing here special-cases "no sort" the way
`app.api.pagination.paginate_and_sort` does for generic list endpoints,
since a timeline is chronological by definition — see
`TimelineQueryService`'s own docstring).
"""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, ensure_same_organization
from app.core.exceptions import NotFoundError
from app.modules.documents.public.enums import DocumentCategory
from app.modules.timeline.api.dependencies import PatientPort, QueryService
from app.modules.timeline.api.schemas import TimelineEventResponse
from app.modules.timeline.application.dto import TimelineFilterInput
from app.modules.timeline.domain.enums import TimelineEventType, TimelineSourceModule
from app.schemas.base import PaginatedResponse

router = APIRouter()


@router.get("/patients/{patient_id}", response_model=PaginatedResponse[TimelineEventResponse])
async def get_patient_timeline(
    patient_id: UUID,
    patient_query_port: PatientPort,
    query_service: QueryService,
    current_user: CurrentUser,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=200),
    sort_order: Literal["asc", "desc"] = Query(default="desc"),
    event_type: Annotated[list[TimelineEventType] | None, Query()] = None,
    source_module: Annotated[list[TimelineSourceModule] | None, Query()] = None,
    visit_id: UUID | None = None,
    appointment_id: UUID | None = None,
    document_category: DocumentCategory | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> PaginatedResponse[TimelineEventResponse]:
    patient_summary = await patient_query_port.get_patient_summary(patient_id)
    if patient_summary is None:
        raise NotFoundError(f"no patient found with id {patient_id}")
    ensure_same_organization(patient_summary.organization_id, current_user)

    filters = TimelineFilterInput(
        event_types=frozenset(event_type) if event_type else None,
        source_modules=frozenset(source_module) if source_module else None,
        visit_id=visit_id,
        appointment_id=appointment_id,
        document_category=document_category,
        date_from=date_from,
        date_to=date_to,
    )
    page = await query_service.get_patient_timeline(
        patient_id, filters=filters, offset=offset, limit=limit, sort_order=sort_order
    )
    return PaginatedResponse(
        items=[TimelineEventResponse.model_validate(e) for e in page.items],
        total=page.total,
        offset=page.offset,
        limit=page.limit,
    )
