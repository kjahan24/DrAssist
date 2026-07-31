"""HTTP routes for the Visit module.

Follows the pattern established in `app.modules.appointment.api.router`
(see that module's own docstring for the full reasoning): `CurrentUser`
on every route, `ensure_same_organization` after every by-id fetch,
`DomainError` translated globally, no business logic duplicated here.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, ensure_same_organization
from app.api.pagination import Pagination, Sorting, paginate_and_sort
from app.core.exceptions import NotFoundError
from app.modules.visit.api.dependencies import (
    get_patient_visit_query_service,
    get_schedule_visit_use_case,
)
from app.modules.visit.api.schemas import PatientVisitResponse, ScheduleVisitRequest
from app.modules.visit.application.dto import ScheduleVisitInput
from app.modules.visit.application.services.patient_visit_query_service import (
    PatientVisitQueryService,
)
from app.modules.visit.application.use_cases.schedule_visit import ScheduleVisit
from app.schemas.base import PaginatedResponse

router = APIRouter()

_SORT_FIELDS = frozenset({"visit_date", "visit_number", "visit_status"})

QueryService = Annotated[PatientVisitQueryService, Depends(get_patient_visit_query_service)]
CreateUseCase = Annotated[ScheduleVisit, Depends(get_schedule_visit_use_case)]


@router.post("", response_model=PatientVisitResponse, status_code=status.HTTP_201_CREATED)
async def schedule_visit(
    body: ScheduleVisitRequest,
    use_case: CreateUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> PatientVisitResponse:
    output = await use_case.execute(
        ScheduleVisitInput(**body.model_dump(), created_by=current_user.user_id)
    )
    summary = await query_service.get_visit_summary(output.visit_id)
    assert summary is not None
    return PatientVisitResponse.model_validate(summary)


@router.get("/{visit_id}", response_model=PatientVisitResponse)
async def get_visit(
    visit_id: UUID, query_service: QueryService, current_user: CurrentUser
) -> PatientVisitResponse:
    summary = await query_service.get_visit_summary(visit_id)
    if summary is None:
        raise NotFoundError(f"no visit found with id {visit_id}")
    response = PatientVisitResponse.model_validate(summary)
    ensure_same_organization(response.organization_id, current_user)
    return response


@router.get("/patient/{patient_id}", response_model=PaginatedResponse[PatientVisitResponse])
async def list_visits_for_patient(
    patient_id: UUID,
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[PatientVisitResponse]:
    summaries = await query_service.list_visits_for_patient(patient_id)
    items = [PatientVisitResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items, pagination=pagination, sorting=sorting, allowed_sort_fields=_SORT_FIELDS
    )
