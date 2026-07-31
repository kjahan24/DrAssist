"""HTTP routes for the Documents module.

Follows the pattern established in `app.modules.appointment.api.router`:
every endpoint requires `CurrentUser` (reusing the already-built
Authentication dependency is not "implementing authentication" — the
same distinction this task's own exclusions draw); every "act on one
resource by id" endpoint calls `ensure_same_organization` right after
fetching, so a cross-tenant request 404s instead of leaking existence;
domain/application exceptions are never caught here —
`app.middlewares.error_handler`'s `DomainError` handler translates them
to the correct HTTP status uniformly.

`upload_document` is the one endpoint that isn't pure request/response
marshalling: it reads the uploaded bytes fully into memory (bounded by
`LocalStorageSettings.max_upload_size_bytes`, checked *before* the
checksum/use-case work so an oversized upload fails cheaply), computes
`checksum_sha256`/`file_size_bytes` from those bytes itself (never
trusting a client-supplied value — see `api/schemas.py`), and derives
`extension` from the uploaded filename. This is the smallest amount of
non-domain orchestration that can live outside the use case while still
keeping the use case's own `file_data: BinaryIO` parameter
framework-agnostic (see `application/dto.py`).
"""

import hashlib
import re
from io import BytesIO
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from starlette.responses import Response

from app.api.deps import CurrentUser, ensure_same_organization
from app.api.pagination import Pagination, Sorting, paginate_and_sort
from app.core.config import get_settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.modules.documents.api.dependencies import (
    get_archive_medical_document_use_case,
    get_delete_medical_document_use_case,
    get_document_query_service,
    get_download_medical_document_use_case,
    get_update_medical_document_details_use_case,
    get_upload_medical_document_use_case,
)
from app.modules.documents.api.schemas import (
    MedicalDocumentResponse,
    UpdateMedicalDocumentDetailsRequest,
)
from app.modules.documents.application.dto import (
    ArchiveMedicalDocumentInput,
    DeleteMedicalDocumentInput,
    DownloadMedicalDocumentInput,
    UpdateMedicalDocumentDetailsInput,
    UploadMedicalDocumentInput,
)
from app.modules.documents.application.services.document_query_service import (
    MedicalDocumentQueryService,
)
from app.modules.documents.application.use_cases.archive_medical_document import (
    ArchiveMedicalDocument,
)
from app.modules.documents.application.use_cases.delete_medical_document import (
    DeleteMedicalDocument,
)
from app.modules.documents.application.use_cases.download_medical_document import (
    DownloadMedicalDocument,
)
from app.modules.documents.application.use_cases.update_medical_document_details import (
    UpdateMedicalDocumentDetails,
)
from app.modules.documents.application.use_cases.upload_medical_document import (
    UploadMedicalDocument,
)
from app.modules.documents.domain.enums import DocumentCategory
from app.schemas.base import PaginatedResponse

router = APIRouter()

_SORT_FIELDS = frozenset({"title", "category", "status", "uploaded_at"})
_UNSAFE_HEADER_CHARS = re.compile(r'[\r\n"]')

QueryService = Annotated[MedicalDocumentQueryService, Depends(get_document_query_service)]
UploadUseCase = Annotated[UploadMedicalDocument, Depends(get_upload_medical_document_use_case)]
UpdateDetailsUseCase = Annotated[
    UpdateMedicalDocumentDetails, Depends(get_update_medical_document_details_use_case)
]
ArchiveUseCase = Annotated[ArchiveMedicalDocument, Depends(get_archive_medical_document_use_case)]
DeleteUseCase = Annotated[DeleteMedicalDocument, Depends(get_delete_medical_document_use_case)]
DownloadUseCase = Annotated[
    DownloadMedicalDocument, Depends(get_download_medical_document_use_case)
]


async def _get_response(
    query_service: MedicalDocumentQueryService, document_id: UUID
) -> MedicalDocumentResponse:
    summary = await query_service.get_document_summary(document_id)
    if summary is None:
        raise NotFoundError(f"no medical document found with id {document_id}")
    return MedicalDocumentResponse.model_validate(summary)


@router.post("", response_model=MedicalDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    use_case: UploadUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
    file: UploadFile = File(...),
    patient_id: UUID = Form(...),
    category: DocumentCategory = Form(...),
    title: str = Form(..., min_length=1, max_length=255),
    visit_id: UUID | None = Form(default=None),
    appointment_id: UUID | None = Form(default=None),
    description: str | None = Form(default=None, max_length=1000),
    tags: str | None = Form(default=None, description="Comma-separated tag list"),
) -> MedicalDocumentResponse:
    extension = Path(file.filename or "").suffix
    if not extension:
        raise BadRequestError("uploaded file must have a filename with an extension")

    content = await file.read()
    max_size = get_settings().local_storage.max_upload_size_bytes
    if len(content) > max_size:
        raise BadRequestError(f"uploaded file exceeds the {max_size}-byte size limit")

    output = await use_case.execute(
        UploadMedicalDocumentInput(
            patient_id=patient_id,
            uploaded_by_user_id=current_user.user_id,
            category=category,
            title=title,
            original_filename=file.filename or "",
            mime_type=file.content_type or "application/octet-stream",
            extension=extension,
            file_size_bytes=len(content),
            checksum_sha256=hashlib.sha256(content).hexdigest(),
            file_data=BytesIO(content),
            visit_id=visit_id,
            appointment_id=appointment_id,
            description=description,
            tags=[tag.strip() for tag in tags.split(",") if tag.strip()] if tags else None,
        )
    )
    return await _get_response(query_service, output.document_id)


@router.get("/{document_id}", response_model=MedicalDocumentResponse)
async def get_document(
    document_id: UUID, query_service: QueryService, current_user: CurrentUser
) -> MedicalDocumentResponse:
    response = await _get_response(query_service, document_id)
    ensure_same_organization(response.organization_id, current_user)
    return response


@router.get("/{document_id}/download")
async def download_document(
    document_id: UUID,
    use_case: DownloadUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> Response:
    existing = await _get_response(query_service, document_id)
    ensure_same_organization(existing.organization_id, current_user)
    output = await use_case.execute(DownloadMedicalDocumentInput(document_id=document_id))
    safe_filename = _UNSAFE_HEADER_CHARS.sub("_", output.original_filename)
    return Response(
        content=output.file_data,
        media_type=existing.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'},
    )


@router.get("/patient/{patient_id}", response_model=PaginatedResponse[MedicalDocumentResponse])
async def list_documents_for_patient(
    patient_id: UUID,
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[MedicalDocumentResponse]:
    summaries = await query_service.list_documents_for_patient(patient_id)
    items = [
        MedicalDocumentResponse.model_validate(s)
        for s in summaries
        if s.organization_id == current_user.organization_id
    ]
    return paginate_and_sort(
        items, pagination=pagination, sorting=sorting, allowed_sort_fields=_SORT_FIELDS
    )


@router.get("/visit/{visit_id}", response_model=PaginatedResponse[MedicalDocumentResponse])
async def list_documents_for_visit(
    visit_id: UUID,
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[MedicalDocumentResponse]:
    summaries = await query_service.list_documents_for_visit(visit_id)
    items = [
        MedicalDocumentResponse.model_validate(s)
        for s in summaries
        if s.organization_id == current_user.organization_id
    ]
    return paginate_and_sort(
        items, pagination=pagination, sorting=sorting, allowed_sort_fields=_SORT_FIELDS
    )


@router.get(
    "/appointment/{appointment_id}", response_model=PaginatedResponse[MedicalDocumentResponse]
)
async def list_documents_for_appointment(
    appointment_id: UUID,
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[MedicalDocumentResponse]:
    summaries = await query_service.list_documents_for_appointment(appointment_id)
    items = [
        MedicalDocumentResponse.model_validate(s)
        for s in summaries
        if s.organization_id == current_user.organization_id
    ]
    return paginate_and_sort(
        items, pagination=pagination, sorting=sorting, allowed_sort_fields=_SORT_FIELDS
    )


@router.patch("/{document_id}", response_model=MedicalDocumentResponse)
async def update_document_details(
    document_id: UUID,
    body: UpdateMedicalDocumentDetailsRequest,
    use_case: UpdateDetailsUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> MedicalDocumentResponse:
    existing = await _get_response(query_service, document_id)
    ensure_same_organization(existing.organization_id, current_user)
    await use_case.execute(
        UpdateMedicalDocumentDetailsInput(document_id=document_id, **body.model_dump())
    )
    return await _get_response(query_service, document_id)


@router.patch("/{document_id}/archive", response_model=MedicalDocumentResponse)
async def archive_document(
    document_id: UUID,
    use_case: ArchiveUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> MedicalDocumentResponse:
    existing = await _get_response(query_service, document_id)
    ensure_same_organization(existing.organization_id, current_user)
    await use_case.execute(ArchiveMedicalDocumentInput(document_id=document_id))
    return await _get_response(query_service, document_id)


@router.patch("/{document_id}/delete", response_model=MedicalDocumentResponse)
async def delete_document(
    document_id: UUID,
    use_case: DeleteUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> MedicalDocumentResponse:
    """Unlike `archive_document`, this cannot re-fetch through
    `query_service` after the use case runs: soft-deleting sets
    `deleted_at`, and every repository read filters `deleted_at IS NULL`
    (see `infrastructure/repositories.py`), so the row would already look
    gone. The pre-delete snapshot plus the use case's own returned
    `status` is the full post-delete representation regardless — nothing
    else changes.
    """
    existing = await _get_response(query_service, document_id)
    ensure_same_organization(existing.organization_id, current_user)
    output = await use_case.execute(DeleteMedicalDocumentInput(document_id=document_id))
    return existing.model_copy(update={"status": output.status})
