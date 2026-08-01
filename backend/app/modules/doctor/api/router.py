"""HTTP routes for the Doctor module.

Follows the pattern established in `app.modules.patient.api.router`.
Covers `Doctor` itself plus its sub-resources (Profile, Licenses,
Specializations, Schedule). `DoctorProfile` is 1:1 with `Doctor` and is
created as part of `OnboardDoctor` itself, so it only gets a `GET`
(no separate `add` endpoint); License/Specialization/Schedule are 1:N
and each get `POST /doctors/{doctor_id}/<sub-resource>` (add) plus
`GET /doctors/{doctor_id}/<sub-resource>` (list).
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, ensure_same_organization
from app.api.pagination import Pagination, Sorting, paginate_and_sort
from app.api.search_params import SearchFilters, resolve_sort_field
from app.core.exceptions import NotFoundError
from app.modules.doctor.api.dependencies import (
    get_add_doctor_license_use_case,
    get_add_doctor_schedule_use_case,
    get_add_doctor_specialization_use_case,
    get_doctor_license_query_service,
    get_doctor_profile_query_service,
    get_doctor_query_service,
    get_doctor_schedule_entry_query_service,
    get_doctor_specialization_query_service,
    get_onboard_doctor_use_case,
)
from app.modules.doctor.api.schemas import (
    AddDoctorLicenseRequest,
    AddDoctorScheduleRequest,
    AddDoctorSpecializationRequest,
    DoctorLicenseResponse,
    DoctorProfileResponse,
    DoctorResponse,
    DoctorScheduleResponse,
    DoctorSpecializationResponse,
    OnboardDoctorRequest,
)
from app.modules.doctor.application.dto import (
    AddDoctorLicenseInput,
    AddDoctorScheduleInput,
    AddDoctorSpecializationInput,
    OnboardDoctorInput,
)
from app.modules.doctor.application.services.doctor_query_service import DoctorQueryService
from app.modules.doctor.application.services.doctor_sub_resource_query_service import (
    DoctorLicenseQueryService,
    DoctorProfileQueryService,
    DoctorScheduleEntryQueryService,
    DoctorSpecializationQueryService,
)
from app.modules.doctor.application.use_cases.add_doctor_license import AddDoctorLicense
from app.modules.doctor.application.use_cases.add_doctor_schedule import AddDoctorSchedule
from app.modules.doctor.application.use_cases.add_doctor_specialization import (
    AddDoctorSpecialization,
)
from app.modules.doctor.application.use_cases.onboard_doctor import OnboardDoctor
from app.modules.doctor.domain.enums import DoctorStatus
from app.schemas.base import PaginatedResponse

router = APIRouter()

_SEARCH_SORT_FIELDS = frozenset(
    {"created_at", "updated_at", "employee_id", "status", "joining_date"}
)

DoctorQS = Annotated[DoctorQueryService, Depends(get_doctor_query_service)]
ProfileQS = Annotated[DoctorProfileQueryService, Depends(get_doctor_profile_query_service)]
LicenseQS = Annotated[DoctorLicenseQueryService, Depends(get_doctor_license_query_service)]
SpecializationQS = Annotated[
    DoctorSpecializationQueryService, Depends(get_doctor_specialization_query_service)
]
ScheduleQS = Annotated[
    DoctorScheduleEntryQueryService, Depends(get_doctor_schedule_entry_query_service)
]

OnboardUseCase = Annotated[OnboardDoctor, Depends(get_onboard_doctor_use_case)]
AddLicenseUseCase = Annotated[AddDoctorLicense, Depends(get_add_doctor_license_use_case)]
AddSpecializationUseCase = Annotated[
    AddDoctorSpecialization, Depends(get_add_doctor_specialization_use_case)
]
AddScheduleUseCase = Annotated[AddDoctorSchedule, Depends(get_add_doctor_schedule_use_case)]


# --- Doctor --------------------------------------------------------------


@router.post("", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED)
async def onboard_doctor(
    body: OnboardDoctorRequest,
    use_case: OnboardUseCase,
    query_service: DoctorQS,
    current_user: CurrentUser,
) -> DoctorResponse:
    output = await use_case.execute(
        OnboardDoctorInput(
            organization_id=current_user.organization_id,
            **body.model_dump(),
            created_by=current_user.user_id,
        )
    )
    summary = await query_service.get_doctor_summary(output.doctor_id)
    assert summary is not None
    return DoctorResponse.model_validate(summary)


@router.get("/{doctor_id}", response_model=DoctorResponse)
async def get_doctor(
    doctor_id: UUID, query_service: DoctorQS, current_user: CurrentUser
) -> DoctorResponse:
    summary = await query_service.get_doctor_summary(doctor_id)
    if summary is None:
        raise NotFoundError(f"no doctor found with id {doctor_id}")
    response = DoctorResponse.model_validate(summary)
    ensure_same_organization(response.organization_id, current_user)
    return response


@router.get("", response_model=PaginatedResponse[DoctorResponse])
async def search_doctors(
    query_service: DoctorQS,
    pagination: Pagination,
    sorting: Sorting,
    filters: SearchFilters,
    current_user: CurrentUser,
    status_filter: Annotated[list[DoctorStatus] | None, Query(alias="status")] = None,
) -> PaginatedResponse[DoctorResponse]:
    """Search & Filtering module: organization-scoped, database-backed
    search/filter/sort/paginate over doctors — see
    `DoctorRepository.search`'s docstring for how `filters.q` combines
    full-text (profile name) and partial (employee id) matching."""
    sort_field = resolve_sort_field(
        sorting.sort_by, allowed_sort_fields=_SEARCH_SORT_FIELDS, default_field="created_at"
    )
    summaries, total = await query_service.search_doctors(
        organization_id=current_user.organization_id,
        query=filters.q,
        statuses=status_filter,
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
    items = [DoctorResponse.model_validate(s) for s in summaries]
    return PaginatedResponse(
        items=items, total=total, offset=pagination.offset, limit=pagination.limit
    )


# --- Profile ---------------------------------------------------------------


@router.get("/{doctor_id}/profile", response_model=DoctorProfileResponse)
async def get_doctor_profile(
    doctor_id: UUID, query_service: ProfileQS, current_user: CurrentUser
) -> DoctorProfileResponse:
    summary = await query_service.get_profile_summary_for_doctor(doctor_id)
    if summary is None:
        raise NotFoundError(f"no profile found for doctor {doctor_id}")
    return DoctorProfileResponse.model_validate(summary)


# --- Licenses --------------------------------------------------------------


@router.post("/{doctor_id}/licenses", response_model=DoctorLicenseResponse, status_code=201)
async def add_doctor_license(
    doctor_id: UUID,
    body: AddDoctorLicenseRequest,
    use_case: AddLicenseUseCase,
    query_service: LicenseQS,
    current_user: CurrentUser,
) -> DoctorLicenseResponse:
    output = await use_case.execute(
        AddDoctorLicenseInput(
            doctor_id=doctor_id, **body.model_dump(), created_by=current_user.user_id
        )
    )
    summary = await query_service.get_license_summary(output.license_id)
    assert summary is not None
    return DoctorLicenseResponse.model_validate(summary)


@router.get("/{doctor_id}/licenses", response_model=PaginatedResponse[DoctorLicenseResponse])
async def list_doctor_licenses(
    doctor_id: UUID,
    query_service: LicenseQS,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[DoctorLicenseResponse]:
    summaries = await query_service.list_licenses_for_doctor(doctor_id)
    items = [DoctorLicenseResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items,
        pagination=pagination,
        sorting=sorting,
        allowed_sort_fields=frozenset({"expiry_date", "verification_status"}),
    )


# --- Specializations ---------------------------------------------------------


@router.post(
    "/{doctor_id}/specializations", response_model=DoctorSpecializationResponse, status_code=201
)
async def add_doctor_specialization(
    doctor_id: UUID,
    body: AddDoctorSpecializationRequest,
    use_case: AddSpecializationUseCase,
    query_service: SpecializationQS,
    current_user: CurrentUser,
) -> DoctorSpecializationResponse:
    output = await use_case.execute(
        AddDoctorSpecializationInput(
            doctor_id=doctor_id, **body.model_dump(), created_by=current_user.user_id
        )
    )
    summary = await query_service.get_specialization_summary(output.specialization_id)
    assert summary is not None
    return DoctorSpecializationResponse.model_validate(summary)


@router.get(
    "/{doctor_id}/specializations",
    response_model=PaginatedResponse[DoctorSpecializationResponse],
)
async def list_doctor_specializations(
    doctor_id: UUID,
    query_service: SpecializationQS,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[DoctorSpecializationResponse]:
    summaries = await query_service.list_specializations_for_doctor(doctor_id)
    items = [DoctorSpecializationResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items,
        pagination=pagination,
        sorting=sorting,
        allowed_sort_fields=frozenset({"specialization_name", "is_primary"}),
    )


# --- Schedule (deprecated — see app.modules.doctor.domain.entities
# .DoctorSchedule's own docstring and
# docs/backend-architecture/14_doctor_schedule_ownership.md) -----------------


@router.post(
    "/{doctor_id}/schedule",
    response_model=DoctorScheduleResponse,
    status_code=201,
    deprecated=True,
)
async def add_doctor_schedule(
    doctor_id: UUID,
    body: AddDoctorScheduleRequest,
    use_case: AddScheduleUseCase,
    query_service: ScheduleQS,
    current_user: CurrentUser,
) -> DoctorScheduleResponse:
    output = await use_case.execute(
        AddDoctorScheduleInput(
            doctor_id=doctor_id, **body.model_dump(), created_by=current_user.user_id
        )
    )
    summary = await query_service.get_schedule_entry_summary(output.schedule_id)
    assert summary is not None
    return DoctorScheduleResponse.model_validate(summary)


@router.get(
    "/{doctor_id}/schedule",
    response_model=PaginatedResponse[DoctorScheduleResponse],
    deprecated=True,
)
async def list_doctor_schedule(
    doctor_id: UUID,
    query_service: ScheduleQS,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[DoctorScheduleResponse]:
    summaries = await query_service.list_schedule_entries_for_doctor(doctor_id)
    items = [DoctorScheduleResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items,
        pagination=pagination,
        sorting=sorting,
        allowed_sort_fields=frozenset({"day_of_week", "is_available"}),
    )
