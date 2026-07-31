"""HTTP routes for the Vital Signs module.

Follows the pattern established in `app.modules.appointment.api.router`.
At most one `VisitVitalSigns` record exists per visit (see
`domain/entities.py`), so there is no separate "get by own id"/"list"
pair here the way every other visit sub-resource has — lookup is always
by `visit_id`, matching `VisitVitalSignsQueryService`'s own shape.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, ensure_same_organization
from app.core.exceptions import NotFoundError
from app.modules.vital_signs.api.dependencies import (
    get_record_vital_signs_use_case,
    get_vital_signs_query_service,
)
from app.modules.vital_signs.api.schemas import (
    RecordVisitVitalSignsRequest,
    VisitVitalSignsResponse,
)
from app.modules.vital_signs.application.dto import RecordVisitVitalSignsInput
from app.modules.vital_signs.application.services.vital_signs_query_service import (
    VisitVitalSignsQueryService,
)
from app.modules.vital_signs.application.use_cases.record_vital_signs import (
    RecordVisitVitalSigns,
)

router = APIRouter()

QueryService = Annotated[VisitVitalSignsQueryService, Depends(get_vital_signs_query_service)]
CreateUseCase = Annotated[RecordVisitVitalSigns, Depends(get_record_vital_signs_use_case)]


@router.post("", response_model=VisitVitalSignsResponse, status_code=status.HTTP_201_CREATED)
async def record_vital_signs(
    body: RecordVisitVitalSignsRequest,
    use_case: CreateUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> VisitVitalSignsResponse:
    await use_case.execute(
        RecordVisitVitalSignsInput(**body.model_dump(), created_by=current_user.user_id)
    )
    summary = await query_service.get_vital_signs_summary_for_visit(body.visit_id)
    assert summary is not None
    return VisitVitalSignsResponse.model_validate(summary)


@router.get("/visit/{visit_id}", response_model=VisitVitalSignsResponse)
async def get_vital_signs_for_visit(
    visit_id: UUID, query_service: QueryService, current_user: CurrentUser
) -> VisitVitalSignsResponse:
    summary = await query_service.get_vital_signs_summary_for_visit(visit_id)
    if summary is None:
        raise NotFoundError(f"no vital signs found for visit {visit_id}")
    response = VisitVitalSignsResponse.model_validate(summary)
    ensure_same_organization(response.organization_id, current_user)
    return response
