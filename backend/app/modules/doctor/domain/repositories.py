"""Repository interfaces — one per aggregate root, expressed in domain
vocabulary only (no session, no SQL). Concrete implementations live in
`app.modules.doctor.infrastructure.repositories`. See
`docs/backend-architecture/04_repository_and_service_patterns.md`.

No `update()` method: a repository returns the actual aggregate object,
the caller mutates it via its own methods, and the Unit of Work's
`commit()` persists the change through SQLAlchemy's session-level change
tracking.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.modules.doctor.domain.entities import (
    Doctor,
    DoctorLicense,
    DoctorProfile,
    DoctorSchedule,
    DoctorSpecialization,
)
from app.modules.doctor.domain.enums import DayOfWeek, DoctorStatus


class DoctorRepository(ABC):
    @abstractmethod
    async def get_by_id(self, doctor_id: UUID) -> Doctor | None: ...

    @abstractmethod
    async def get_by_user_id(self, user_id: UUID) -> Doctor | None: ...

    @abstractmethod
    async def get_by_employee_id(
        self, *, organization_id: UUID, employee_id: str
    ) -> Doctor | None: ...

    @abstractmethod
    async def list_by_organization(
        self, organization_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[Doctor]: ...

    @abstractmethod
    async def search(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        statuses: Sequence[DoctorStatus] | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "created_at",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Doctor], int]:
        """Search & Filtering module: organization-scoped search over
        doctors — `query` combines a full-text match on the doctor's
        profile `full_name` (outer-joined, since a profile is not
        guaranteed to exist) with a partial match on `employee_id`, the
        same "one term, two techniques" shape as
        `PatientRepository.search`. Returns `(page_of_doctors,
        total_matching_count)`."""
        ...

    @abstractmethod
    async def add(self, doctor: Doctor) -> None: ...


class DoctorProfileRepository(ABC):
    @abstractmethod
    async def get_by_doctor_id(self, doctor_id: UUID) -> DoctorProfile | None: ...

    @abstractmethod
    async def add(self, profile: DoctorProfile) -> None: ...


class DoctorLicenseRepository(ABC):
    @abstractmethod
    async def get_by_id(self, license_id: UUID) -> DoctorLicense | None: ...

    @abstractmethod
    async def get_by_license_number(self, license_number: str) -> DoctorLicense | None: ...

    @abstractmethod
    async def list_by_doctor(self, doctor_id: UUID) -> list[DoctorLicense]: ...

    @abstractmethod
    async def add(self, license: DoctorLicense) -> None: ...


class DoctorSpecializationRepository(ABC):
    @abstractmethod
    async def get_by_id(self, specialization_id: UUID) -> DoctorSpecialization | None: ...

    @abstractmethod
    async def list_by_doctor(self, doctor_id: UUID) -> list[DoctorSpecialization]: ...

    @abstractmethod
    async def unset_primary_for_doctor(self, doctor_id: UUID) -> None:
        """Clear `is_primary` on every existing specialization for `doctor_id`
        — called before adding a new primary specialization, so "one primary
        per doctor" holds without relying on the caller to check first."""
        ...

    @abstractmethod
    async def add(self, specialization: DoctorSpecialization) -> None: ...


class DoctorScheduleRepository(ABC):
    @abstractmethod
    async def get_by_id(self, schedule_id: UUID) -> DoctorSchedule | None: ...

    @abstractmethod
    async def list_by_doctor(self, doctor_id: UUID) -> list[DoctorSchedule]: ...

    @abstractmethod
    async def list_by_doctor_and_day(
        self, doctor_id: UUID, day_of_week: DayOfWeek
    ) -> list[DoctorSchedule]: ...

    @abstractmethod
    async def add(self, schedule: DoctorSchedule) -> None: ...
