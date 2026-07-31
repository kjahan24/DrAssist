"""HTTP routes for the Procedures module.

Follows the pattern established in `app.modules.appointment.api.router`.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, ensure_same_organization
from app.api.pagination import Pagination, Sorting, paginate_and_sort
from app.core.exceptions import NotFoundError
from app.modules.procedures.api.dependencies import (
    get_procedure_query_service,
    get_record_procedure_use_case,
)
from app.modules.procedures.api.schemas import (
    RecordVisitProcedureRequest,
    VisitProcedureResponse,
)
from app.modules.procedures.application.dto import RecordVisitProcedureInput
from app.modules.procedures.application.services.procedure_query_service import (
    VisitProcedureQueryService,
)
from app.modules.procedures.application.use_cases.record_procedure import RecordVisitProcedure
from app.schemas.base import PaginatedResponse

router = APIRouter()

_SORT_FIELDS = frozenset({"sequence_number", "procedure_name", "procedure_status"})

QueryService = Annotated[VisitProcedureQueryService, Depends(get_procedure_query_service)]
CreateUseCase = Annotated[RecordVisitProcedure, Depends(get_record_procedure_use_case)]


@router.post("", response_model=VisitProcedureResponse, status_code=status.HTTP_201_CREATED)
async def record_procedure(
    body: RecordVisitProcedureRequest,
    use_case: CreateUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> VisitProcedureResponse:
    output = await use_case.execute(
        RecordVisitProcedureInput(**body.model_dump(), created_by=current_user.user_id)
    )
    summary = await query_service.get_procedure_summary(output.procedure_id)
    assert summary is not None
    return VisitProcedureResponse.model_validate(summary)


@router.get("/{procedure_id}", response_model=VisitProcedureResponse)
async def get_procedure(
    procedure_id: UUID, query_service: QueryService, current_user: CurrentUser
) -> VisitProcedureResponse:
    summary = await query_service.get_procedure_summary(procedure_id)
    if summary is None:
        raise NotFoundError(f"no procedure found with id {procedure_id}")
    response = VisitProcedureResponse.model_validate(summary)
    ensure_same_organization(response.organization_id, current_user)
    return response


@router.get("/visit/{visit_id}", response_model=PaginatedResponse[VisitProcedureResponse])
async def list_procedures_for_visit(
    visit_id: UUID,
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[VisitProcedureResponse]:
    summaries = await query_service.list_procedures_for_visit(visit_id)
    items = [VisitProcedureResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items, pagination=pagination, sorting=sorting, allowed_sort_fields=_SORT_FIELDS
    )
