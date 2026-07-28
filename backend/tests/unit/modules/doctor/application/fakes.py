"""In-memory test doubles for the Doctor module's repositories, Unit of
Work, and the cross-module ports `OnboardDoctor` depends on — each
implements the exact same interface its real counterpart does, per
`docs/backend-architecture/12_testing_architecture.md` ("fakes over mocks
as the default"). Application-layer use case/service tests depend on
these, never on a real database or another module's facade.
"""

from uuid import UUID

from app.modules.authentication.public.dto import UserSummaryDTO
from app.modules.authentication.public.interfaces import UserQueryPort
from app.modules.doctor.domain.entities import (
    Doctor,
    DoctorLicense,
    DoctorProfile,
    DoctorSchedule,
    DoctorSpecialization,
)
from app.modules.doctor.domain.enums import DayOfWeek
from app.modules.doctor.domain.repositories import (
    DoctorLicenseRepository,
    DoctorProfileRepository,
    DoctorRepository,
    DoctorScheduleRepository,
    DoctorSpecializationRepository,
)
from app.modules.organization.public.dto import OrganizationSummaryDTO
from app.modules.organization.public.interfaces import OrganizationQueryPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.domain.domain_event import DomainEvent


class FakeDoctorRepository(DoctorRepository):
    def __init__(self) -> None:
        self._doctors: dict[UUID, Doctor] = {}

    async def get_by_id(self, doctor_id: UUID) -> Doctor | None:
        return self._doctors.get(doctor_id)

    async def get_by_user_id(self, user_id: UUID) -> Doctor | None:
        for doctor in self._doctors.values():
            if doctor.user_id == user_id:
                return doctor
        return None

    async def get_by_employee_id(self, *, organization_id: UUID, employee_id: str) -> Doctor | None:
        for doctor in self._doctors.values():
            if (
                doctor.organization_id == organization_id
                and doctor.employee_id == employee_id.strip()
            ):
                return doctor
        return None

    async def list_by_organization(
        self, organization_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[Doctor]:
        matches = [d for d in self._doctors.values() if d.organization_id == organization_id]
        return matches[offset : offset + limit]

    async def add(self, doctor: Doctor) -> None:
        self._doctors[doctor.id] = doctor


class FakeDoctorProfileRepository(DoctorProfileRepository):
    def __init__(self) -> None:
        self._profiles: dict[UUID, DoctorProfile] = {}

    async def get_by_doctor_id(self, doctor_id: UUID) -> DoctorProfile | None:
        for profile in self._profiles.values():
            if profile.doctor_id == doctor_id:
                return profile
        return None

    async def add(self, profile: DoctorProfile) -> None:
        self._profiles[profile.id] = profile


class FakeDoctorLicenseRepository(DoctorLicenseRepository):
    def __init__(self) -> None:
        self._licenses: dict[UUID, DoctorLicense] = {}

    async def get_by_id(self, license_id: UUID) -> DoctorLicense | None:
        return self._licenses.get(license_id)

    async def get_by_license_number(self, license_number: str) -> DoctorLicense | None:
        for license_ in self._licenses.values():
            if license_.license_number == license_number.strip():
                return license_
        return None

    async def list_by_doctor(self, doctor_id: UUID) -> list[DoctorLicense]:
        return [lic for lic in self._licenses.values() if lic.doctor_id == doctor_id]

    async def add(self, license: DoctorLicense) -> None:
        self._licenses[license.id] = license


class FakeDoctorSpecializationRepository(DoctorSpecializationRepository):
    def __init__(self) -> None:
        self._specializations: dict[UUID, DoctorSpecialization] = {}

    async def get_by_id(self, specialization_id: UUID) -> DoctorSpecialization | None:
        return self._specializations.get(specialization_id)

    async def list_by_doctor(self, doctor_id: UUID) -> list[DoctorSpecialization]:
        return [s for s in self._specializations.values() if s.doctor_id == doctor_id]

    async def unset_primary_for_doctor(self, doctor_id: UUID) -> None:
        for specialization in self._specializations.values():
            if specialization.doctor_id == doctor_id and specialization.is_primary:
                specialization.is_primary = False

    async def add(self, specialization: DoctorSpecialization) -> None:
        self._specializations[specialization.id] = specialization


class FakeDoctorScheduleRepository(DoctorScheduleRepository):
    def __init__(self) -> None:
        self._schedules: dict[UUID, DoctorSchedule] = {}

    async def get_by_id(self, schedule_id: UUID) -> DoctorSchedule | None:
        return self._schedules.get(schedule_id)

    async def list_by_doctor(self, doctor_id: UUID) -> list[DoctorSchedule]:
        return [s for s in self._schedules.values() if s.doctor_id == doctor_id]

    async def list_by_doctor_and_day(
        self, doctor_id: UUID, day_of_week: DayOfWeek
    ) -> list[DoctorSchedule]:
        return [
            s
            for s in self._schedules.values()
            if s.doctor_id == doctor_id and s.day_of_week == day_of_week
        ]

    async def add(self, schedule: DoctorSchedule) -> None:
        self._schedules[schedule.id] = schedule


class FakeUnitOfWork(UnitOfWork):
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False
        self.published_events: list[DomainEvent] = []
        self._pending_events: list[DomainEvent] = []

    def collect_events(self, events: list[DomainEvent]) -> None:
        self._pending_events.extend(events)

    async def commit(self) -> None:
        self.committed = True
        self.published_events.extend(self._pending_events)
        self._pending_events = []

    async def rollback(self) -> None:
        self.rolled_back = True
        self._pending_events = []

    async def flush(self) -> None:
        pass


class FakeOrganizationQueryPort(OrganizationQueryPort):
    """Backed by a settable set of "existing" organization ids —
    `OnboardDoctor` only calls `organization_exists`."""

    def __init__(self, *, existing_organization_ids: set[UUID] | None = None) -> None:
        self.existing_organization_ids = existing_organization_ids or set()

    async def organization_exists(self, organization_id: UUID) -> bool:
        return organization_id in self.existing_organization_ids

    async def is_active(self, organization_id: UUID) -> bool:
        return organization_id in self.existing_organization_ids

    async def get_organization_summary(
        self, organization_id: UUID
    ) -> OrganizationSummaryDTO | None:
        raise NotImplementedError("not exercised by any use case tested against this fake")

    async def get_default_timezone(self, organization_id: UUID) -> str | None:
        raise NotImplementedError("not exercised by any use case tested against this fake")


class FakeUserQueryPort(UserQueryPort):
    """Backed by a settable set of "existing" user ids — `OnboardDoctor`
    only calls `user_exists`."""

    def __init__(self, *, existing_user_ids: set[UUID] | None = None) -> None:
        self.existing_user_ids = existing_user_ids or set()

    async def user_exists(self, user_id: UUID) -> bool:
        return user_id in self.existing_user_ids

    async def get_user_summary(self, user_id: UUID) -> UserSummaryDTO | None:
        raise NotImplementedError("not exercised by any use case tested against this fake")
