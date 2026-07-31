"""HTTP routes for the Lab Results module.

`LabResult` is 1:1 with `LabOrder`, so `GET` uses
`/lab-results/lab-order/{lab_order_id}` as the primary lookup, matching
`app.modules.prescriptions.api.router`'s own shape for its identical
1:1-with-parent relationship.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, ensure_same_organization
from app.api.pagination import Pagination, Sorting, paginate_and_sort
from app.api.search_params import SearchFilters, resolve_sort_field
from app.core.exceptions import NotFoundError
from app.modules.lab_results.api.dependencies import (
    get_add_lab_result_item_use_case,
    get_create_lab_result_use_case,
    get_finalize_lab_result_use_case,
    get_lab_result_query_service,
    get_update_lab_result_use_case,
)
from app.modules.lab_results.api.schemas import (
    AddLabResultItemRequest,
    CreateLabResultRequest,
    LabResultResponse,
    UpdateLabResultRequest,
)
from app.modules.lab_results.application.dto import (
    AddLabResultItemInput,
    CreateLabResultInput,
    FinalizeLabResultInput,
    UpdateLabResultInput,
)
from app.modules.lab_results.application.services.lab_result_query_service import (
    LabResultQueryService,
)
from app.modules.lab_results.application.use_cases.add_lab_result_item import AddLabResultItem
from app.modules.lab_results.application.use_cases.create_lab_result import CreateLabResult
from app.modules.lab_results.application.use_cases.finalize_lab_result import FinalizeLabResult
from app.modules.lab_results.application.use_cases.update_lab_result import UpdateLabResult
from app.modules.lab_results.domain.enums import LabResultStatus
from app.schemas.base import PaginatedResponse

router = APIRouter()

_SEARCH_SORT_FIELDS = frozenset(
    {"created_at", "updated_at", "result_number", "reported_at", "status"}
)

QueryService = Annotated[LabResultQueryService, Depends(get_lab_result_query_service)]
CreateUseCase = Annotated[CreateLabResult, Depends(get_create_lab_result_use_case)]
UpdateUseCase = Annotated[UpdateLabResult, Depends(get_update_lab_result_use_case)]
AddItemUseCase = Annotated[AddLabResultItem, Depends(get_add_lab_result_item_use_case)]
FinalizeUseCase = Annotated[FinalizeLabResult, Depends(get_finalize_lab_result_use_case)]


async def _get_response_by_id(
    lab_result_id: UUID, query_service: QueryService, current_user: CurrentUser
) -> LabResultResponse:
    summary = await query_service.get_lab_result_summary_by_id(lab_result_id)
    if summary is None:
        raise NotFoundError(f"no lab result found with id {lab_result_id}")
    response = LabResultResponse.model_validate(summary)
    ensure_same_organization(response.organization_id, current_user)
    return response


@router.post("", response_model=LabResultResponse, status_code=status.HTTP_201_CREATED)
async def create_lab_result(
    body: CreateLabResultRequest,
    use_case: CreateUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> LabResultResponse:
    output = await use_case.execute(
        CreateLabResultInput(**body.model_dump(), created_by=current_user.user_id)
    )
    return await _get_response_by_id(output.lab_result_id, query_service, current_user)


@router.get("/lab-order/{lab_order_id}", response_model=LabResultResponse)
async def get_lab_result_for_lab_order(
    lab_order_id: UUID, query_service: QueryService, current_user: CurrentUser
) -> LabResultResponse:
    summary = await query_service.get_lab_result_summary(lab_order_id)
    if summary is None:
        raise NotFoundError(f"no lab result found for lab order {lab_order_id}")
    response = LabResultResponse.model_validate(summary)
    ensure_same_organization(response.organization_id, current_user)
    return response


@router.get("/{lab_result_id}", response_model=LabResultResponse)
async def get_lab_result(
    lab_result_id: UUID, query_service: QueryService, current_user: CurrentUser
) -> LabResultResponse:
    return await _get_response_by_id(lab_result_id, query_service, current_user)


@router.get("", response_model=PaginatedResponse[LabResultResponse])
async def search_lab_results(
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    filters: SearchFilters,
    current_user: CurrentUser,
    status_filter: Annotated[list[LabResultStatus] | None, Query(alias="status")] = None,
    patient_id: UUID | None = None,
    doctor_id: UUID | None = None,
    visit_id: UUID | None = None,
    lab_order_id: UUID | None = None,
    reported_from: datetime | None = None,
    reported_to: datetime | None = None,
) -> PaginatedResponse[LabResultResponse]:
    """Search & Filtering module: organization-scoped, database-backed
    search/filter/sort/paginate over lab results — see
    `LabResultRepository.search`'s docstring for how `filters.q` is
    matched, and `LabResultQueryService.search_lab_results`'s docstring
    for how embedded items are batch-loaded to avoid N+1."""
    sort_field = resolve_sort_field(
        sorting.sort_by, allowed_sort_fields=_SEARCH_SORT_FIELDS, default_field="reported_at"
    )
    summaries, total = await query_service.search_lab_results(
        organization_id=current_user.organization_id,
        query=filters.q,
        statuses=status_filter,
        patient_id=patient_id,
        doctor_id=doctor_id,
        visit_id=visit_id,
        lab_order_id=lab_order_id,
        reported_from=reported_from,
        reported_to=reported_to,
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
    items = [LabResultResponse.model_validate(s) for s in summaries]
    return PaginatedResponse(
        items=items, total=total, offset=pagination.offset, limit=pagination.limit
    )


@router.get("/patient/{patient_id}", response_model=PaginatedResponse[LabResultResponse])
async def list_lab_results_for_patient(
    patient_id: UUID,
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[LabResultResponse]:
    summaries = await query_service.list_lab_results_for_patient(patient_id)
    items = [LabResultResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items,
        pagination=pagination,
        sorting=sorting,
        allowed_sort_fields=frozenset({"result_number", "reported_at", "status"}),
    )


@router.put("/{lab_result_id}", response_model=LabResultResponse)
async def update_lab_result(
    lab_result_id: UUID,
    body: UpdateLabResultRequest,
    use_case: UpdateUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> LabResultResponse:
    await use_case.execute(UpdateLabResultInput(lab_result_id=lab_result_id, **body.model_dump()))
    return await _get_response_by_id(lab_result_id, query_service, current_user)


@router.post("/{lab_result_id}/items", response_model=LabResultResponse, status_code=201)
async def add_lab_result_item(
    lab_result_id: UUID,
    body: AddLabResultItemRequest,
    use_case: AddItemUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> LabResultResponse:
    await use_case.execute(
        AddLabResultItemInput(
            lab_result_id=lab_result_id, **body.model_dump(), created_by=current_user.user_id
        )
    )
    return await _get_response_by_id(lab_result_id, query_service, current_user)


@router.patch("/{lab_result_id}/finalize", response_model=LabResultResponse)
async def finalize_lab_result(
    lab_result_id: UUID,
    use_case: FinalizeUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> LabResultResponse:
    await use_case.execute(FinalizeLabResultInput(lab_result_id=lab_result_id))
    return await _get_response_by_id(lab_result_id, query_service, current_user)
