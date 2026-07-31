"""HTTP routes for the Lab Orders module.

`LabOrder` is one-to-many with `ClinicalNote` (unlike `Prescription`'s
1:1), so `GET` is keyed by the lab order's own id, and listing by
clinical note or patient are separate collection endpoints — matching
`app.modules.lab_orders.application.services.lab_order_query_service`'s
own shape.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, ensure_same_organization
from app.api.pagination import Pagination, Sorting, paginate_and_sort
from app.core.exceptions import NotFoundError
from app.modules.lab_orders.api.dependencies import (
    get_add_lab_order_item_use_case,
    get_cancel_lab_order_use_case,
    get_create_lab_order_use_case,
    get_lab_order_query_service,
    get_mark_lab_order_collected_use_case,
    get_place_lab_order_use_case,
    get_update_lab_order_use_case,
)
from app.modules.lab_orders.api.schemas import (
    AddLabOrderItemRequest,
    CreateLabOrderRequest,
    LabOrderResponse,
    UpdateLabOrderRequest,
)
from app.modules.lab_orders.application.dto import (
    AddLabOrderItemInput,
    CancelLabOrderInput,
    CreateLabOrderInput,
    MarkLabOrderCollectedInput,
    PlaceLabOrderInput,
    UpdateLabOrderInput,
)
from app.modules.lab_orders.application.services.lab_order_query_service import (
    LabOrderQueryService,
)
from app.modules.lab_orders.application.use_cases.add_lab_order_item import AddLabOrderItem
from app.modules.lab_orders.application.use_cases.cancel_lab_order import CancelLabOrder
from app.modules.lab_orders.application.use_cases.create_lab_order import CreateLabOrder
from app.modules.lab_orders.application.use_cases.mark_lab_order_collected import (
    MarkLabOrderCollected,
)
from app.modules.lab_orders.application.use_cases.place_lab_order import PlaceLabOrder
from app.modules.lab_orders.application.use_cases.update_lab_order import UpdateLabOrder
from app.schemas.base import PaginatedResponse

router = APIRouter()

_SORT_FIELDS = frozenset({"order_number", "ordered_at", "priority", "status"})

QueryService = Annotated[LabOrderQueryService, Depends(get_lab_order_query_service)]
CreateUseCase = Annotated[CreateLabOrder, Depends(get_create_lab_order_use_case)]
UpdateUseCase = Annotated[UpdateLabOrder, Depends(get_update_lab_order_use_case)]
AddItemUseCase = Annotated[AddLabOrderItem, Depends(get_add_lab_order_item_use_case)]
PlaceUseCase = Annotated[PlaceLabOrder, Depends(get_place_lab_order_use_case)]
MarkCollectedUseCase = Annotated[
    MarkLabOrderCollected, Depends(get_mark_lab_order_collected_use_case)
]
CancelUseCase = Annotated[CancelLabOrder, Depends(get_cancel_lab_order_use_case)]


async def _get_response(
    lab_order_id: UUID, query_service: QueryService, current_user: CurrentUser
) -> LabOrderResponse:
    summary = await query_service.get_lab_order_summary(lab_order_id)
    if summary is None:
        raise NotFoundError(f"no lab order found with id {lab_order_id}")
    response = LabOrderResponse.model_validate(summary)
    ensure_same_organization(response.organization_id, current_user)
    return response


@router.post("", response_model=LabOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_lab_order(
    body: CreateLabOrderRequest,
    use_case: CreateUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> LabOrderResponse:
    output = await use_case.execute(
        CreateLabOrderInput(**body.model_dump(), created_by=current_user.user_id)
    )
    return await _get_response(output.lab_order_id, query_service, current_user)


@router.get("/{lab_order_id}", response_model=LabOrderResponse)
async def get_lab_order(
    lab_order_id: UUID, query_service: QueryService, current_user: CurrentUser
) -> LabOrderResponse:
    return await _get_response(lab_order_id, query_service, current_user)


@router.get("/clinical-note/{clinical_note_id}", response_model=PaginatedResponse[LabOrderResponse])
async def list_lab_orders_for_clinical_note(
    clinical_note_id: UUID,
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[LabOrderResponse]:
    summaries = await query_service.list_lab_orders_for_clinical_note(clinical_note_id)
    items = [LabOrderResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items, pagination=pagination, sorting=sorting, allowed_sort_fields=_SORT_FIELDS
    )


@router.get("/patient/{patient_id}", response_model=PaginatedResponse[LabOrderResponse])
async def list_lab_orders_for_patient(
    patient_id: UUID,
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[LabOrderResponse]:
    summaries = await query_service.list_lab_orders_for_patient(patient_id)
    items = [LabOrderResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items, pagination=pagination, sorting=sorting, allowed_sort_fields=_SORT_FIELDS
    )


@router.put("/{lab_order_id}", response_model=LabOrderResponse)
async def update_lab_order(
    lab_order_id: UUID,
    body: UpdateLabOrderRequest,
    use_case: UpdateUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> LabOrderResponse:
    await use_case.execute(UpdateLabOrderInput(lab_order_id=lab_order_id, **body.model_dump()))
    return await _get_response(lab_order_id, query_service, current_user)


@router.post("/{lab_order_id}/items", response_model=LabOrderResponse, status_code=201)
async def add_lab_order_item(
    lab_order_id: UUID,
    body: AddLabOrderItemRequest,
    use_case: AddItemUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> LabOrderResponse:
    await use_case.execute(
        AddLabOrderItemInput(
            lab_order_id=lab_order_id, **body.model_dump(), created_by=current_user.user_id
        )
    )
    return await _get_response(lab_order_id, query_service, current_user)


@router.patch("/{lab_order_id}/place", response_model=LabOrderResponse)
async def place_lab_order(
    lab_order_id: UUID,
    use_case: PlaceUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> LabOrderResponse:
    await use_case.execute(PlaceLabOrderInput(lab_order_id=lab_order_id))
    return await _get_response(lab_order_id, query_service, current_user)


@router.patch("/{lab_order_id}/mark-collected", response_model=LabOrderResponse)
async def mark_lab_order_collected(
    lab_order_id: UUID,
    use_case: MarkCollectedUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> LabOrderResponse:
    await use_case.execute(MarkLabOrderCollectedInput(lab_order_id=lab_order_id))
    return await _get_response(lab_order_id, query_service, current_user)


@router.patch("/{lab_order_id}/cancel", response_model=LabOrderResponse)
async def cancel_lab_order(
    lab_order_id: UUID,
    use_case: CancelUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> LabOrderResponse:
    await use_case.execute(CancelLabOrderInput(lab_order_id=lab_order_id))
    return await _get_response(lab_order_id, query_service, current_user)
