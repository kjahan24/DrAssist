"""Read-only queries for the Doctor module's four sub-resource aggregates
(`DoctorProfile`, `DoctorLicense`, `DoctorSpecialization`, `DoctorSchedule`
— the original doctor-onboarding one, not `app.modules.schedule`'s own
separately-named `DoctorSchedule`).

Added by the REST APIs task — see
`app.modules.patient.application.services.patient_sub_resource_query_service`'s
own docstring for the full reasoning (identical situation: small,
single-repository classes rather than growing `DoctorQueryService`'s own
constructor).
"""

from uuid import UUID

from app.modules.doctor.application.dto import (
    DoctorLicenseSummaryDTO,
    DoctorProfileSummaryDTO,
    DoctorScheduleEntrySummaryDTO,
    DoctorSpecializationSummaryDTO,
)
from app.modules.doctor.domain.entities import (
    DoctorLicense,
    DoctorProfile,
    DoctorSchedule,
    DoctorSpecialization,
)
from app.modules.doctor.domain.repositories import (
    DoctorLicenseRepository,
    DoctorProfileRepository,
    DoctorScheduleRepository,
    DoctorSpecializationRepository,
)


class DoctorProfileQueryService:
    def __init__(self, *, doctor_profile_repository: DoctorProfileRepository) -> None:
        self._profiles = doctor_profile_repository

    async def get_profile_summary_for_doctor(
        self, doctor_id: UUID
    ) -> DoctorProfileSummaryDTO | None:
        profile = await self._profiles.get_by_doctor_id(doctor_id)
        return _profile_to_summary(profile) if profile is not None else None


def _profile_to_summary(profile: DoctorProfile) -> DoctorProfileSummaryDTO:
    return DoctorProfileSummaryDTO(
        profile_id=profile.id,
        doctor_id=profile.doctor_id,
        full_name=profile.full_name,
        gender=profile.gender,
        date_of_birth=profile.date_of_birth,
        phone=profile.phone,
        email=str(profile.email) if profile.email is not None else None,
        address=profile.address,
        biography=profile.biography,
        years_of_experience=profile.years_of_experience,
        qualification=profile.qualification,
        consultation_fee=profile.consultation_fee,
        profile_photo_url=profile.profile_photo_url,
    )


class DoctorLicenseQueryService:
    def __init__(self, *, doctor_license_repository: DoctorLicenseRepository) -> None:
        self._licenses = doctor_license_repository

    async def get_license_summary(self, license_id: UUID) -> DoctorLicenseSummaryDTO | None:
        license_ = await self._licenses.get_by_id(license_id)
        return _license_to_summary(license_) if license_ is not None else None

    async def list_licenses_for_doctor(self, doctor_id: UUID) -> list[DoctorLicenseSummaryDTO]:
        licenses = await self._licenses.list_by_doctor(doctor_id)
        return [_license_to_summary(license_) for license_ in licenses]


def _license_to_summary(license_: DoctorLicense) -> DoctorLicenseSummaryDTO:
    return DoctorLicenseSummaryDTO(
        license_id=license_.id,
        doctor_id=license_.doctor_id,
        license_number=license_.license_number,
        issuing_authority=license_.issuing_authority,
        country=license_.country,
        issue_date=license_.issue_date,
        expiry_date=license_.expiry_date,
        verification_status=license_.verification_status,
    )


class DoctorSpecializationQueryService:
    def __init__(self, *, doctor_specialization_repository: DoctorSpecializationRepository) -> None:
        self._specializations = doctor_specialization_repository

    async def get_specialization_summary(
        self, specialization_id: UUID
    ) -> DoctorSpecializationSummaryDTO | None:
        specialization = await self._specializations.get_by_id(specialization_id)
        return _specialization_to_summary(specialization) if specialization is not None else None

    async def list_specializations_for_doctor(
        self, doctor_id: UUID
    ) -> list[DoctorSpecializationSummaryDTO]:
        specializations = await self._specializations.list_by_doctor(doctor_id)
        return [_specialization_to_summary(s) for s in specializations]


def _specialization_to_summary(
    specialization: DoctorSpecialization,
) -> DoctorSpecializationSummaryDTO:
    return DoctorSpecializationSummaryDTO(
        specialization_id=specialization.id,
        organization_id=specialization.organization_id,
        doctor_id=specialization.doctor_id,
        specialization_name=specialization.specialization_name,
        is_primary=specialization.is_primary,
        years_of_experience=specialization.years_of_experience,
    )


class DoctorScheduleEntryQueryService:
    def __init__(self, *, doctor_schedule_repository: DoctorScheduleRepository) -> None:
        self._schedules = doctor_schedule_repository

    async def get_schedule_entry_summary(
        self, schedule_id: UUID
    ) -> DoctorScheduleEntrySummaryDTO | None:
        schedule = await self._schedules.get_by_id(schedule_id)
        return _schedule_to_summary(schedule) if schedule is not None else None

    async def list_schedule_entries_for_doctor(
        self, doctor_id: UUID
    ) -> list[DoctorScheduleEntrySummaryDTO]:
        schedules = await self._schedules.list_by_doctor(doctor_id)
        return [_schedule_to_summary(schedule) for schedule in schedules]


def _schedule_to_summary(schedule: DoctorSchedule) -> DoctorScheduleEntrySummaryDTO:
    return DoctorScheduleEntrySummaryDTO(
        schedule_id=schedule.id,
        doctor_id=schedule.doctor_id,
        day_of_week=schedule.day_of_week,
        start_time=schedule.start_time,
        end_time=schedule.end_time,
        break_start=schedule.break_start,
        break_end=schedule.break_end,
        is_available=schedule.is_available,
    )
