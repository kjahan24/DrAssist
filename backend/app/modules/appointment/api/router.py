"""HTTP routes for the Appointment module.

Reference implementation for the REST APIs task's per-module router
pattern (see `docs/backend-architecture/11_standards_and_conventions.md`
for the naming conventions every schema above already follows): every
endpoint requires `CurrentUser` (already-built Authentication dependency
— reusing it is not "implementing authentication", the same distinction
this task's own "Do NOT implement X" exclusions draw everywhere else in
this codebase); every "act on one resource by id" endpoint calls
`ensure_same_organization` right after fetching, so a cross-tenant
request 404s instead of leaking existence; every "create" endpoint
passes `current_user.user_id` for the audit-trail field the DTO already
has (`created_by`/`booked_by_user_id`-shaped) rather than trusting a
client-supplied actor id; domain/application exceptions are never caught
here — `app.middlewares.error_handler`'s `DomainError` handler (added by
this task) translates them to the correct HTTP status uniformly. Reuses
every use case/query service already wired in `api/dependencies.py`
(built in this module's own original task) — no business logic is
duplicated here, only request/response marshalling.
"""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, ensure_same_organization
from app.api.pagination import Pagination, Sorting, paginate_and_sort
from app.api.search_params import SearchFilters, resolve_sort_field
from app.core.exceptions import NotFoundError
from app.modules.appointment.api.dependencies import (
    get_appointment_query_service,
    get_cancel_appointment_use_case,
    get_check_in_appointment_use_case,
    get_complete_appointment_use_case,
    get_confirm_appointment_use_case,
    get_create_appointment_use_case,
    get_mark_appointment_no_show_use_case,
    get_start_appointment_use_case,
    get_update_appointment_use_case,
)
from app.modules.appointment.api.schemas import (
    AppointmentResponse,
    CompleteAppointmentRequest,
    CreateAppointmentRequest,
    UpdateAppointmentRequest,
)
from app.modules.appointment.application.dto import (
    CancelAppointmentInput,
    CheckInAppointmentInput,
    CompleteAppointmentInput,
    ConfirmAppointmentInput,
    CreateAppointmentInput,
    MarkAppointmentNoShowInput,
    StartAppointmentInput,
    UpdateAppointmentInput,
)
from app.modules.appointment.application.services.appointment_query_service import (
    AppointmentQueryService,
)
from app.modules.appointment.application.use_cases.cancel_appointment import CancelAppointment
from app.modules.appointment.application.use_cases.check_in_appointment import CheckInAppointment
from app.modules.appointment.application.use_cases.complete_appointment import (
    CompleteAppointment,
)
from app.modules.appointment.application.use_cases.confirm_appointment import ConfirmAppointment
from app.modules.appointment.application.use_cases.create_appointment import CreateAppointment
from app.modules.appointment.application.use_cases.mark_appointment_no_show import (
    MarkAppointmentNoShow,
)
from app.modules.appointment.application.use_cases.start_appointment import StartAppointment
from app.modules.appointment.application.use_cases.update_appointment import UpdateAppointment
from app.modules.appointment.domain.enums import AppointmentStatus
from app.schemas.base import PaginatedResponse

router = APIRouter()

_SORT_FIELDS = frozenset({"appointment_date", "appointment_number", "status", "appointment_type"})

QueryService = Annotated[AppointmentQueryService, Depends(get_appointment_query_service)]
CreateUseCase = Annotated[CreateAppointment, Depends(get_create_appointment_use_case)]
UpdateUseCase = Annotated[UpdateAppointment, Depends(get_update_appointment_use_case)]
ConfirmUseCase = Annotated[ConfirmAppointment, Depends(get_confirm_appointment_use_case)]
CheckInUseCase = Annotated[CheckInAppointment, Depends(get_check_in_appointment_use_case)]
StartUseCase = Annotated[StartAppointment, Depends(get_start_appointment_use_case)]
CompleteUseCase = Annotated[CompleteAppointment, Depends(get_complete_appointment_use_case)]
CancelUseCase = Annotated[CancelAppointment, Depends(get_cancel_appointment_use_case)]
NoShowUseCase = Annotated[MarkAppointmentNoShow, Depends(get_mark_appointment_no_show_use_case)]


async def _get_response(
    query_service: AppointmentQueryService, appointment_id: UUID
) -> AppointmentResponse:
    summary = await query_service.get_appointment_summary(appointment_id)
    if summary is None:
        raise NotFoundError(f"no appointment found with id {appointment_id}")
    return AppointmentResponse.model_validate(summary)


@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    body: CreateAppointmentRequest,
    use_case: CreateUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> AppointmentResponse:
    output = await use_case.execute(
        CreateAppointmentInput(**body.model_dump(), created_by=current_user.user_id)
    )
    return await _get_response(query_service, output.appointment_id)


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: UUID, query_service: QueryService, current_user: CurrentUser
) -> AppointmentResponse:
    response = await _get_response(query_service, appointment_id)
    ensure_same_organization(response.organization_id, current_user)
    return response


@router.get("/by-number/{appointment_number}", response_model=AppointmentResponse)
async def get_appointment_by_number(
    appointment_number: str, query_service: QueryService, current_user: CurrentUser
) -> AppointmentResponse:
    summary = await query_service.get_by_appointment_number(appointment_number)
    if summary is None:
        raise NotFoundError(f"no appointment found with number {appointment_number!r}")
    response = AppointmentResponse.model_validate(summary)
    ensure_same_organization(response.organization_id, current_user)
    return response


@router.get("", response_model=PaginatedResponse[AppointmentResponse])
async def search_appointments(
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    filters: SearchFilters,
    current_user: CurrentUser,
    status_filter: Annotated[list[AppointmentStatus] | None, Query(alias="status")] = None,
    patient_id: UUID | None = None,
    doctor_id: UUID | None = None,
    appointment_date_from: date | None = None,
    appointment_date_to: date | None = None,
) -> PaginatedResponse[AppointmentResponse]:
    """Search & Filtering module: organization-scoped, database-backed
    search/filter/sort/paginate over appointments — see
    `AppointmentRepository.search`'s docstring for how `filters.q`
    combines full-text and partial matching, and for
    `appointment_date_from`/`_to` vs. the generic `created_from`/`_to`."""
    sort_field = resolve_sort_field(
        sorting.sort_by, allowed_sort_fields=_SORT_FIELDS, default_field="appointment_date"
    )
    summaries, total = await query_service.search_appointments(
        organization_id=current_user.organization_id,
        query=filters.q,
        statuses=status_filter,
        patient_id=patient_id,
        doctor_id=doctor_id,
        appointment_date_from=appointment_date_from,
        appointment_date_to=appointment_date_to,
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
    items = [AppointmentResponse.model_validate(s) for s in summaries]
    return PaginatedResponse(
        items=items, total=total, offset=pagination.offset, limit=pagination.limit
    )


@router.get("/patient/{patient_id}", response_model=PaginatedResponse[AppointmentResponse])
async def list_appointments_for_patient(
    patient_id: UUID,
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[AppointmentResponse]:
    summaries = await query_service.list_appointments_for_patient(patient_id)
    items = [AppointmentResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items, pagination=pagination, sorting=sorting, allowed_sort_fields=_SORT_FIELDS
    )


@router.get("/doctor/{doctor_id}", response_model=PaginatedResponse[AppointmentResponse])
async def list_appointments_for_doctor(
    doctor_id: UUID,
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[AppointmentResponse]:
    summaries = await query_service.list_appointments_for_doctor(doctor_id)
    items = [AppointmentResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items, pagination=pagination, sorting=sorting, allowed_sort_fields=_SORT_FIELDS
    )


@router.put("/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: UUID,
    body: UpdateAppointmentRequest,
    use_case: UpdateUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> AppointmentResponse:
    existing = await _get_response(query_service, appointment_id)
    ensure_same_organization(existing.organization_id, current_user)
    await use_case.execute(
        UpdateAppointmentInput(appointment_id=appointment_id, **body.model_dump())
    )
    return await _get_response(query_service, appointment_id)


@router.patch("/{appointment_id}/confirm", response_model=AppointmentResponse)
async def confirm_appointment(
    appointment_id: UUID,
    use_case: ConfirmUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> AppointmentResponse:
    existing = await _get_response(query_service, appointment_id)
    ensure_same_organization(existing.organization_id, current_user)
    await use_case.execute(ConfirmAppointmentInput(appointment_id=appointment_id))
    return await _get_response(query_service, appointment_id)


@router.patch("/{appointment_id}/check-in", response_model=AppointmentResponse)
async def check_in_appointment(
    appointment_id: UUID,
    use_case: CheckInUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> AppointmentResponse:
    existing = await _get_response(query_service, appointment_id)
    ensure_same_organization(existing.organization_id, current_user)
    await use_case.execute(CheckInAppointmentInput(appointment_id=appointment_id))
    return await _get_response(query_service, appointment_id)


@router.patch("/{appointment_id}/start", response_model=AppointmentResponse)
async def start_appointment(
    appointment_id: UUID,
    use_case: StartUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> AppointmentResponse:
    existing = await _get_response(query_service, appointment_id)
    ensure_same_organization(existing.organization_id, current_user)
    await use_case.execute(StartAppointmentInput(appointment_id=appointment_id))
    return await _get_response(query_service, appointment_id)


@router.patch("/{appointment_id}/complete", response_model=AppointmentResponse)
async def complete_appointment(
    appointment_id: UUID,
    body: CompleteAppointmentRequest,
    use_case: CompleteUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> AppointmentResponse:
    existing = await _get_response(query_service, appointment_id)
    ensure_same_organization(existing.organization_id, current_user)
    await use_case.execute(
        CompleteAppointmentInput(appointment_id=appointment_id, visit_id=body.visit_id)
    )
    return await _get_response(query_service, appointment_id)


@router.patch("/{appointment_id}/cancel", response_model=AppointmentResponse)
async def cancel_appointment(
    appointment_id: UUID,
    use_case: CancelUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> AppointmentResponse:
    existing = await _get_response(query_service, appointment_id)
    ensure_same_organization(existing.organization_id, current_user)
    await use_case.execute(CancelAppointmentInput(appointment_id=appointment_id))
    return await _get_response(query_service, appointment_id)


@router.patch("/{appointment_id}/no-show", response_model=AppointmentResponse)
async def mark_appointment_no_show(
    appointment_id: UUID,
    use_case: NoShowUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> AppointmentResponse:
    existing = await _get_response(query_service, appointment_id)
    ensure_same_organization(existing.organization_id, current_user)
    await use_case.execute(MarkAppointmentNoShowInput(appointment_id=appointment_id))
    return await _get_response(query_service, appointment_id)
