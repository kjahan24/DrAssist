"""HTTP routes for the Attachments module.

Follows the pattern established in `app.modules.appointment.api.router`.
Only upload *metadata* is accepted here — see `api/schemas.py`'s own
docstring: no endpoint handles raw file bytes.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, ensure_same_organization
from app.api.pagination import Pagination, Sorting, paginate_and_sort
from app.core.exceptions import NotFoundError
from app.modules.attachments.api.dependencies import (
    get_attachment_query_service,
    get_upload_attachment_use_case,
)
from app.modules.attachments.api.schemas import (
    UploadVisitAttachmentRequest,
    VisitAttachmentResponse,
)
from app.modules.attachments.application.dto import UploadVisitAttachmentInput
from app.modules.attachments.application.services.attachment_query_service import (
    VisitAttachmentQueryService,
)
from app.modules.attachments.application.use_cases.upload_attachment import (
    UploadVisitAttachment,
)
from app.schemas.base import PaginatedResponse

router = APIRouter()

_SORT_FIELDS = frozenset({"file_name", "attachment_type", "uploaded_at"})

QueryService = Annotated[VisitAttachmentQueryService, Depends(get_attachment_query_service)]
CreateUseCase = Annotated[UploadVisitAttachment, Depends(get_upload_attachment_use_case)]


@router.post("", response_model=VisitAttachmentResponse, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    body: UploadVisitAttachmentRequest,
    use_case: CreateUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> VisitAttachmentResponse:
    output = await use_case.execute(
        UploadVisitAttachmentInput(**body.model_dump(), created_by=current_user.user_id)
    )
    summary = await query_service.get_attachment_summary(output.attachment_id)
    assert summary is not None
    return VisitAttachmentResponse.model_validate(summary)


@router.get("/{attachment_id}", response_model=VisitAttachmentResponse)
async def get_attachment(
    attachment_id: UUID, query_service: QueryService, current_user: CurrentUser
) -> VisitAttachmentResponse:
    summary = await query_service.get_attachment_summary(attachment_id)
    if summary is None:
        raise NotFoundError(f"no attachment found with id {attachment_id}")
    response = VisitAttachmentResponse.model_validate(summary)
    ensure_same_organization(response.organization_id, current_user)
    return response


@router.get("/visit/{visit_id}", response_model=PaginatedResponse[VisitAttachmentResponse])
async def list_attachments_for_visit(
    visit_id: UUID,
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[VisitAttachmentResponse]:
    summaries = await query_service.list_attachments_for_visit(visit_id)
    items = [VisitAttachmentResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items, pagination=pagination, sorting=sorting, allowed_sort_fields=_SORT_FIELDS
    )
