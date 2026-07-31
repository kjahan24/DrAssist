"""HTTP routes for the Schedule/Availability module.

Covers `DoctorSchedule` (weekly recurring availability) and
`DoctorTimeOff` (one-off unavailability windows) — the schedule module's
own entities, distinct from `app.modules.doctor`'s own onboarding-time
`DoctorSchedule`/`api/router.py` sub-resource (see
`app.modules.doctor.application.dto.DoctorScheduleEntrySummaryDTO`'s own
docstring for that pre-existing naming collision). Time-off routes live
under `/time-off` within this same router.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, ensure_same_organization
from app.api.pagination import Pagination, Sorting, paginate_and_sort
from app.core.exceptions import NotFoundError
from app.modules.schedule.api.dependencies import (
    get_activate_doctor_schedule_use_case,
    get_create_doctor_schedule_use_case,
    get_create_doctor_time_off_use_case,
    get_deactivate_doctor_schedule_use_case,
    get_doctor_schedule_query_service,
    get_doctor_time_off_query_service,
    get_update_doctor_schedule_use_case,
    get_update_doctor_time_off_use_case,
)
from app.modules.schedule.api.schemas import (
    CreateDoctorScheduleRequest,
    CreateDoctorTimeOffRequest,
    DoctorScheduleResponse,
    DoctorTimeOffResponse,
    UpdateDoctorScheduleRequest,
    UpdateDoctorTimeOffRequest,
)
from app.modules.schedule.application.dto import (
    ActivateDoctorScheduleInput,
    CreateDoctorScheduleInput,
    CreateDoctorTimeOffInput,
    DeactivateDoctorScheduleInput,
    UpdateDoctorScheduleInput,
    UpdateDoctorTimeOffInput,
)
from app.modules.schedule.application.services.doctor_schedule_query_service import (
    DoctorScheduleQueryService,
)
from app.modules.schedule.application.services.doctor_time_off_query_service import (
    DoctorTimeOffQueryService,
)
from app.modules.schedule.application.use_cases.activate_doctor_schedule import (
    ActivateDoctorSchedule,
)
from app.modules.schedule.application.use_cases.create_doctor_schedule import (
    CreateDoctorSchedule,
)
from app.modules.schedule.application.use_cases.create_doctor_time_off import CreateDoctorTimeOff
from app.modules.schedule.application.use_cases.deactivate_doctor_schedule import (
    DeactivateDoctorSchedule,
)
from app.modules.schedule.application.use_cases.update_doctor_schedule import (
    UpdateDoctorSchedule,
)
from app.modules.schedule.application.use_cases.update_doctor_time_off import UpdateDoctorTimeOff
from app.schemas.base import PaginatedResponse

router = APIRouter()

ScheduleQS = Annotated[DoctorScheduleQueryService, Depends(get_doctor_schedule_query_service)]
TimeOffQS = Annotated[DoctorTimeOffQueryService, Depends(get_doctor_time_off_query_service)]

CreateScheduleUseCase = Annotated[
    CreateDoctorSchedule, Depends(get_create_doctor_schedule_use_case)
]
UpdateScheduleUseCase = Annotated[
    UpdateDoctorSchedule, Depends(get_update_doctor_schedule_use_case)
]
ActivateScheduleUseCase = Annotated[
    ActivateDoctorSchedule, Depends(get_activate_doctor_schedule_use_case)
]
DeactivateScheduleUseCase = Annotated[
    DeactivateDoctorSchedule, Depends(get_deactivate_doctor_schedule_use_case)
]
CreateTimeOffUseCase = Annotated[CreateDoctorTimeOff, Depends(get_create_doctor_time_off_use_case)]
UpdateTimeOffUseCase = Annotated[UpdateDoctorTimeOff, Depends(get_update_doctor_time_off_use_case)]


async def _get_schedule_response(
    schedule_id: UUID, query_service: ScheduleQS, current_user: CurrentUser
) -> DoctorScheduleResponse:
    summary = await query_service.get_doctor_schedule_summary(schedule_id)
    if summary is None:
        raise NotFoundError(f"no doctor schedule found with id {schedule_id}")
    response = DoctorScheduleResponse.model_validate(summary)
    ensure_same_organization(response.organization_id, current_user)
    return response


async def _get_time_off_response(
    time_off_id: UUID, query_service: TimeOffQS, current_user: CurrentUser
) -> DoctorTimeOffResponse:
    summary = await query_service.get_doctor_time_off_summary(time_off_id)
    if summary is None:
        raise NotFoundError(f"no doctor time off found with id {time_off_id}")
    response = DoctorTimeOffResponse.model_validate(summary)
    ensure_same_organization(response.organization_id, current_user)
    return response


# --- DoctorSchedule ----------------------------------------------------------


@router.post("", response_model=DoctorScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_doctor_schedule(
    body: CreateDoctorScheduleRequest,
    use_case: CreateScheduleUseCase,
    query_service: ScheduleQS,
    current_user: CurrentUser,
) -> DoctorScheduleResponse:
    output = await use_case.execute(
        CreateDoctorScheduleInput(**body.model_dump(), created_by=current_user.user_id)
    )
    return await _get_schedule_response(output.schedule_id, query_service, current_user)


@router.get("/{schedule_id}", response_model=DoctorScheduleResponse)
async def get_doctor_schedule(
    schedule_id: UUID, query_service: ScheduleQS, current_user: CurrentUser
) -> DoctorScheduleResponse:
    return await _get_schedule_response(schedule_id, query_service, current_user)


@router.get("/doctor/{doctor_id}", response_model=PaginatedResponse[DoctorScheduleResponse])
async def list_doctor_schedules(
    doctor_id: UUID,
    query_service: ScheduleQS,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[DoctorScheduleResponse]:
    summaries = await query_service.list_doctor_schedules(doctor_id)
    items = [DoctorScheduleResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items,
        pagination=pagination,
        sorting=sorting,
        allowed_sort_fields=frozenset({"weekday", "is_active"}),
    )


@router.put("/{schedule_id}", response_model=DoctorScheduleResponse)
async def update_doctor_schedule(
    schedule_id: UUID,
    body: UpdateDoctorScheduleRequest,
    use_case: UpdateScheduleUseCase,
    query_service: ScheduleQS,
    current_user: CurrentUser,
) -> DoctorScheduleResponse:
    await use_case.execute(UpdateDoctorScheduleInput(schedule_id=schedule_id, **body.model_dump()))
    return await _get_schedule_response(schedule_id, query_service, current_user)


@router.patch("/{schedule_id}/activate", response_model=DoctorScheduleResponse)
async def activate_doctor_schedule(
    schedule_id: UUID,
    use_case: ActivateScheduleUseCase,
    query_service: ScheduleQS,
    current_user: CurrentUser,
) -> DoctorScheduleResponse:
    await use_case.execute(ActivateDoctorScheduleInput(schedule_id=schedule_id))
    return await _get_schedule_response(schedule_id, query_service, current_user)


@router.patch("/{schedule_id}/deactivate", response_model=DoctorScheduleResponse)
async def deactivate_doctor_schedule(
    schedule_id: UUID,
    use_case: DeactivateScheduleUseCase,
    query_service: ScheduleQS,
    current_user: CurrentUser,
) -> DoctorScheduleResponse:
    await use_case.execute(DeactivateDoctorScheduleInput(schedule_id=schedule_id))
    return await _get_schedule_response(schedule_id, query_service, current_user)


# --- DoctorTimeOff -------------------------------------------------------------


@router.post("/time-off", response_model=DoctorTimeOffResponse, status_code=status.HTTP_201_CREATED)
async def create_doctor_time_off(
    body: CreateDoctorTimeOffRequest,
    use_case: CreateTimeOffUseCase,
    query_service: TimeOffQS,
    current_user: CurrentUser,
) -> DoctorTimeOffResponse:
    output = await use_case.execute(
        CreateDoctorTimeOffInput(**body.model_dump(), created_by=current_user.user_id)
    )
    return await _get_time_off_response(output.time_off_id, query_service, current_user)


@router.get("/time-off/{time_off_id}", response_model=DoctorTimeOffResponse)
async def get_doctor_time_off(
    time_off_id: UUID, query_service: TimeOffQS, current_user: CurrentUser
) -> DoctorTimeOffResponse:
    return await _get_time_off_response(time_off_id, query_service, current_user)


@router.get("/time-off/doctor/{doctor_id}", response_model=PaginatedResponse[DoctorTimeOffResponse])
async def list_doctor_time_off(
    doctor_id: UUID,
    query_service: TimeOffQS,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[DoctorTimeOffResponse]:
    summaries = await query_service.list_doctor_time_off(doctor_id)
    items = [DoctorTimeOffResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items,
        pagination=pagination,
        sorting=sorting,
        allowed_sort_fields=frozenset({"start_datetime", "end_datetime"}),
    )


@router.put("/time-off/{time_off_id}", response_model=DoctorTimeOffResponse)
async def update_doctor_time_off(
    time_off_id: UUID,
    body: UpdateDoctorTimeOffRequest,
    use_case: UpdateTimeOffUseCase,
    query_service: TimeOffQS,
    current_user: CurrentUser,
) -> DoctorTimeOffResponse:
    await use_case.execute(UpdateDoctorTimeOffInput(time_off_id=time_off_id, **body.model_dump()))
    return await _get_time_off_response(time_off_id, query_service, current_user)
