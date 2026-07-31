"""HTTP routes for the Chief Complaints module.

Follows the pattern established in `app.modules.appointment.api.router`.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, ensure_same_organization
from app.api.pagination import Pagination, Sorting, paginate_and_sort
from app.core.exceptions import NotFoundError
from app.modules.chief_complaints.api.dependencies import (
    get_chief_complaint_query_service,
    get_record_chief_complaint_use_case,
)
from app.modules.chief_complaints.api.schemas import (
    RecordVisitChiefComplaintRequest,
    VisitChiefComplaintResponse,
)
from app.modules.chief_complaints.application.dto import RecordVisitChiefComplaintInput
from app.modules.chief_complaints.application.services.chief_complaint_query_service import (
    VisitChiefComplaintQueryService,
)
from app.modules.chief_complaints.application.use_cases.record_chief_complaint import (
    RecordVisitChiefComplaint,
)
from app.schemas.base import PaginatedResponse

router = APIRouter()

_SORT_FIELDS = frozenset({"sequence_number", "severity", "recorded_at"})

QueryService = Annotated[
    VisitChiefComplaintQueryService, Depends(get_chief_complaint_query_service)
]
CreateUseCase = Annotated[RecordVisitChiefComplaint, Depends(get_record_chief_complaint_use_case)]


@router.post("", response_model=VisitChiefComplaintResponse, status_code=status.HTTP_201_CREATED)
async def record_chief_complaint(
    body: RecordVisitChiefComplaintRequest,
    use_case: CreateUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> VisitChiefComplaintResponse:
    output = await use_case.execute(
        RecordVisitChiefComplaintInput(**body.model_dump(), created_by=current_user.user_id)
    )
    summary = await query_service.get_chief_complaint_summary(output.chief_complaint_id)
    assert summary is not None
    return VisitChiefComplaintResponse.model_validate(summary)


@router.get("/{chief_complaint_id}", response_model=VisitChiefComplaintResponse)
async def get_chief_complaint(
    chief_complaint_id: UUID, query_service: QueryService, current_user: CurrentUser
) -> VisitChiefComplaintResponse:
    summary = await query_service.get_chief_complaint_summary(chief_complaint_id)
    if summary is None:
        raise NotFoundError(f"no chief complaint found with id {chief_complaint_id}")
    response = VisitChiefComplaintResponse.model_validate(summary)
    ensure_same_organization(response.organization_id, current_user)
    return response


@router.get("/visit/{visit_id}", response_model=PaginatedResponse[VisitChiefComplaintResponse])
async def list_chief_complaints_for_visit(
    visit_id: UUID,
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[VisitChiefComplaintResponse]:
    summaries = await query_service.list_chief_complaints_for_visit(visit_id)
    items = [VisitChiefComplaintResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items, pagination=pagination, sorting=sorting, allowed_sort_fields=_SORT_FIELDS
    )
