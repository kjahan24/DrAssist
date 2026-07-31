"""HTTP routes for the Prescription module.

`Prescription` is 1:1 with `ClinicalNote`, so `GET` uses
`/prescriptions/clinical-note/{clinical_note_id}` as the primary lookup;
`PUT`/`POST items`/`finalize` address the prescription by its own id.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, ensure_same_organization
from app.api.pagination import Pagination, Sorting, paginate_and_sort
from app.core.exceptions import NotFoundError
from app.modules.prescriptions.api.dependencies import (
    get_add_prescription_item_use_case,
    get_create_prescription_use_case,
    get_finalize_prescription_use_case,
    get_prescription_query_service,
    get_update_prescription_use_case,
)
from app.modules.prescriptions.api.schemas import (
    AddPrescriptionItemRequest,
    CreatePrescriptionRequest,
    PrescriptionResponse,
    UpdatePrescriptionRequest,
)
from app.modules.prescriptions.application.dto import (
    AddPrescriptionItemInput,
    CreatePrescriptionInput,
    FinalizePrescriptionInput,
    UpdatePrescriptionInput,
)
from app.modules.prescriptions.application.services.prescription_query_service import (
    PrescriptionQueryService,
)
from app.modules.prescriptions.application.use_cases.add_prescription_item import (
    AddPrescriptionItem,
)
from app.modules.prescriptions.application.use_cases.create_prescription import CreatePrescription
from app.modules.prescriptions.application.use_cases.finalize_prescription import (
    FinalizePrescription,
)
from app.modules.prescriptions.application.use_cases.update_prescription import UpdatePrescription
from app.schemas.base import PaginatedResponse

router = APIRouter()

QueryService = Annotated[PrescriptionQueryService, Depends(get_prescription_query_service)]
CreateUseCase = Annotated[CreatePrescription, Depends(get_create_prescription_use_case)]
UpdateUseCase = Annotated[UpdatePrescription, Depends(get_update_prescription_use_case)]
AddItemUseCase = Annotated[AddPrescriptionItem, Depends(get_add_prescription_item_use_case)]
FinalizeUseCase = Annotated[FinalizePrescription, Depends(get_finalize_prescription_use_case)]


@router.post("", response_model=PrescriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_prescription(
    body: CreatePrescriptionRequest,
    use_case: CreateUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> PrescriptionResponse:
    output = await use_case.execute(
        CreatePrescriptionInput(**body.model_dump(), created_by=current_user.user_id)
    )
    summary = await query_service.get_prescription_summary(output.clinical_note_id)
    assert summary is not None
    return PrescriptionResponse.model_validate(summary)


@router.get("/clinical-note/{clinical_note_id}", response_model=PrescriptionResponse)
async def get_prescription_for_clinical_note(
    clinical_note_id: UUID, query_service: QueryService, current_user: CurrentUser
) -> PrescriptionResponse:
    summary = await query_service.get_prescription_summary(clinical_note_id)
    if summary is None:
        raise NotFoundError(f"no prescription found for clinical note {clinical_note_id}")
    response = PrescriptionResponse.model_validate(summary)
    ensure_same_organization(response.organization_id, current_user)
    return response


@router.get("/{prescription_id}", response_model=PrescriptionResponse)
async def get_prescription(
    prescription_id: UUID, query_service: QueryService, current_user: CurrentUser
) -> PrescriptionResponse:
    summary = await query_service.get_prescription_summary_by_id(prescription_id)
    if summary is None:
        raise NotFoundError(f"no prescription found with id {prescription_id}")
    response = PrescriptionResponse.model_validate(summary)
    ensure_same_organization(response.organization_id, current_user)
    return response


@router.get("/patient/{patient_id}", response_model=PaginatedResponse[PrescriptionResponse])
async def list_prescriptions_for_patient(
    patient_id: UUID,
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[PrescriptionResponse]:
    summaries = await query_service.list_prescriptions_for_patient(patient_id)
    items = [PrescriptionResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items,
        pagination=pagination,
        sorting=sorting,
        allowed_sort_fields=frozenset({"prescription_number", "prescription_date", "status"}),
    )


@router.put("/{prescription_id}", response_model=PrescriptionResponse)
async def update_prescription(
    prescription_id: UUID,
    body: UpdatePrescriptionRequest,
    use_case: UpdateUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> PrescriptionResponse:
    await use_case.execute(
        UpdatePrescriptionInput(prescription_id=prescription_id, **body.model_dump())
    )
    summary = await query_service.get_prescription_summary_by_id(prescription_id)
    assert summary is not None
    response = PrescriptionResponse.model_validate(summary)
    ensure_same_organization(response.organization_id, current_user)
    return response


@router.post("/{prescription_id}/items", response_model=PrescriptionResponse, status_code=201)
async def add_prescription_item(
    prescription_id: UUID,
    body: AddPrescriptionItemRequest,
    use_case: AddItemUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> PrescriptionResponse:
    await use_case.execute(
        AddPrescriptionItemInput(
            prescription_id=prescription_id,
            **body.model_dump(),
            created_by=current_user.user_id,
        )
    )
    summary = await query_service.get_prescription_summary_by_id(prescription_id)
    assert summary is not None
    response = PrescriptionResponse.model_validate(summary)
    ensure_same_organization(response.organization_id, current_user)
    return response


@router.patch("/{prescription_id}/finalize", response_model=PrescriptionResponse)
async def finalize_prescription(
    prescription_id: UUID,
    use_case: FinalizeUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> PrescriptionResponse:
    await use_case.execute(FinalizePrescriptionInput(prescription_id=prescription_id))
    summary = await query_service.get_prescription_summary_by_id(prescription_id)
    assert summary is not None
    response = PrescriptionResponse.model_validate(summary)
    ensure_same_organization(response.organization_id, current_user)
    return response
