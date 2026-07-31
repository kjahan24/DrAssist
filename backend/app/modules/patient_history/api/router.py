"""HTTP routes for the Patient History module.

`Create`/`Get`/`List` only — "History records are immutable" means there
is no update or status-transition action to wire up here (see
`api/schemas.py`'s own docstring). `get_by_reference` is exposed as a
query-parameter search on the list endpoint rather than a separate route,
since `(reference_type, reference_id)` is a lookup key, not a
sub-resource path.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, ensure_same_organization
from app.api.pagination import Pagination, Sorting, paginate_and_sort
from app.core.exceptions import NotFoundError
from app.modules.patient_history.api.dependencies import (
    get_create_patient_history_use_case,
    get_patient_history_query_service,
)
from app.modules.patient_history.api.schemas import (
    CreatePatientHistoryRequest,
    PatientHistoryResponse,
)
from app.modules.patient_history.application.dto import CreatePatientHistoryInput
from app.modules.patient_history.application.services.patient_history_query_service import (
    PatientHistoryQueryService,
)
from app.modules.patient_history.application.use_cases.create_patient_history import (
    CreatePatientHistory,
)
from app.schemas.base import PaginatedResponse

router = APIRouter()

QueryService = Annotated[PatientHistoryQueryService, Depends(get_patient_history_query_service)]
CreateUseCase = Annotated[CreatePatientHistory, Depends(get_create_patient_history_use_case)]


@router.post("", response_model=PatientHistoryResponse, status_code=status.HTTP_201_CREATED)
async def create_patient_history(
    body: CreatePatientHistoryRequest,
    use_case: CreateUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> PatientHistoryResponse:
    output = await use_case.execute(
        CreatePatientHistoryInput(**body.model_dump(), created_by=current_user.user_id)
    )
    summary = await query_service.get_patient_history_summary(output.patient_history_id)
    assert summary is not None
    return PatientHistoryResponse.model_validate(summary)


@router.get("/{patient_history_id}", response_model=PatientHistoryResponse)
async def get_patient_history(
    patient_history_id: UUID, query_service: QueryService, current_user: CurrentUser
) -> PatientHistoryResponse:
    summary = await query_service.get_patient_history_summary(patient_history_id)
    if summary is None:
        raise NotFoundError(f"no patient history found with id {patient_history_id}")
    response = PatientHistoryResponse.model_validate(summary)
    ensure_same_organization(response.organization_id, current_user)
    return response


@router.get("/patient/{patient_id}", response_model=PaginatedResponse[PatientHistoryResponse])
async def list_patient_history_for_patient(
    patient_id: UUID,
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[PatientHistoryResponse]:
    summaries = await query_service.list_patient_history_for_patient(patient_id)
    items = [PatientHistoryResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items,
        pagination=pagination,
        sorting=sorting,
        allowed_sort_fields=frozenset({"encounter_date", "history_type", "reference_type"}),
    )


@router.get("/visit/{visit_id}", response_model=PaginatedResponse[PatientHistoryResponse])
async def list_patient_history_for_visit(
    visit_id: UUID,
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[PatientHistoryResponse]:
    summaries = await query_service.list_patient_history_for_visit(visit_id)
    items = [PatientHistoryResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items,
        pagination=pagination,
        sorting=sorting,
        allowed_sort_fields=frozenset({"encounter_date", "history_type", "reference_type"}),
    )
