"""HTTP routes for the Diagnosis module.

Follows the pattern established in `app.modules.appointment.api.router`.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, ensure_same_organization
from app.api.pagination import Pagination, Sorting, paginate_and_sort
from app.core.exceptions import NotFoundError
from app.modules.diagnosis.api.dependencies import (
    get_diagnosis_query_service,
    get_record_diagnosis_use_case,
)
from app.modules.diagnosis.api.schemas import (
    RecordVisitDiagnosisRequest,
    VisitDiagnosisResponse,
)
from app.modules.diagnosis.application.dto import RecordVisitDiagnosisInput
from app.modules.diagnosis.application.services.diagnosis_query_service import (
    VisitDiagnosisQueryService,
)
from app.modules.diagnosis.application.use_cases.record_diagnosis import RecordVisitDiagnosis
from app.schemas.base import PaginatedResponse

router = APIRouter()

_SORT_FIELDS = frozenset({"sequence_number", "diagnosis_name", "diagnosis_status"})

QueryService = Annotated[VisitDiagnosisQueryService, Depends(get_diagnosis_query_service)]
CreateUseCase = Annotated[RecordVisitDiagnosis, Depends(get_record_diagnosis_use_case)]


@router.post("", response_model=VisitDiagnosisResponse, status_code=status.HTTP_201_CREATED)
async def record_diagnosis(
    body: RecordVisitDiagnosisRequest,
    use_case: CreateUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> VisitDiagnosisResponse:
    output = await use_case.execute(
        RecordVisitDiagnosisInput(**body.model_dump(), created_by=current_user.user_id)
    )
    summary = await query_service.get_diagnosis_summary(output.diagnosis_id)
    assert summary is not None
    return VisitDiagnosisResponse.model_validate(summary)


@router.get("/{diagnosis_id}", response_model=VisitDiagnosisResponse)
async def get_diagnosis(
    diagnosis_id: UUID, query_service: QueryService, current_user: CurrentUser
) -> VisitDiagnosisResponse:
    summary = await query_service.get_diagnosis_summary(diagnosis_id)
    if summary is None:
        raise NotFoundError(f"no diagnosis found with id {diagnosis_id}")
    response = VisitDiagnosisResponse.model_validate(summary)
    ensure_same_organization(response.organization_id, current_user)
    return response


@router.get("/visit/{visit_id}", response_model=PaginatedResponse[VisitDiagnosisResponse])
async def list_diagnoses_for_visit(
    visit_id: UUID,
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[VisitDiagnosisResponse]:
    summaries = await query_service.list_diagnoses_for_visit(visit_id)
    items = [VisitDiagnosisResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items, pagination=pagination, sorting=sorting, allowed_sort_fields=_SORT_FIELDS
    )
