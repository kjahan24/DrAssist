"""HTTP routes for the Visit module.

Follows the pattern established in `app.modules.appointment.api.router`
(see that module's own docstring for the full reasoning): `CurrentUser`
on every route, `ensure_same_organization` after every by-id fetch,
`DomainError` translated globally, no business logic duplicated here.
"""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, ensure_same_organization
from app.api.pagination import Pagination, Sorting, paginate_and_sort
from app.api.search_params import SearchFilters, resolve_sort_field
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
from app.modules.visit.domain.enums import VisitStatus
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


@router.get("", response_model=PaginatedResponse[PatientVisitResponse])
async def search_visits(
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    filters: SearchFilters,
    current_user: CurrentUser,
    status_filter: Annotated[list[VisitStatus] | None, Query(alias="status")] = None,
    patient_id: UUID | None = None,
    doctor_id: UUID | None = None,
    visit_date_from: date | None = None,
    visit_date_to: date | None = None,
) -> PaginatedResponse[PatientVisitResponse]:
    """Search & Filtering module: organization-scoped, database-backed
    search/filter/sort/paginate over patient visits — see
    `PatientVisitRepository.search`'s docstring for how `filters.q`
    combines full-text and partial matching."""
    sort_field = resolve_sort_field(
        sorting.sort_by, allowed_sort_fields=_SORT_FIELDS, default_field="visit_date"
    )
    summaries, total = await query_service.search_visits(
        organization_id=current_user.organization_id,
        query=filters.q,
        statuses=status_filter,
        patient_id=patient_id,
        doctor_id=doctor_id,
        visit_date_from=visit_date_from,
        visit_date_to=visit_date_to,
        created_from=filters.created_from,
        created_to=filters.created_to,
        updated_from=filters.updated_from,
        updated_to=filters.updated_to,
        include_deleted=filters.include_deleted,
        sort_by=sort_field,
        sort_order=sorting.sort_order,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    items = [PatientVisitResponse.model_validate(s) for s in summaries]
    return PaginatedResponse(
        items=items, total=total, offset=pagination.offset, limit=pagination.limit
    )


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
