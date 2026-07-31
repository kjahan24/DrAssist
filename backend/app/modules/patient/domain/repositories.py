"""Repository interfaces for the Patient module's aggregates, expressed in
domain vocabulary only (no session, no SQL). Concrete implementations live
in `app.modules.patient.infrastructure.repositories`. See
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

from app.modules.patient.domain.entities import (
    EmergencyContact,
    Insurance,
    Patient,
    PatientAllergy,
    PatientContact,
    PatientMedicalCondition,
    PatientMedication,
)
from app.modules.patient.domain.enums import ContactType, PatientStatus


class PatientRepository(ABC):
    @abstractmethod
    async def get_by_id(self, patient_id: UUID) -> Patient | None: ...

    @abstractmethod
    async def get_by_patient_number(
        self, *, organization_id: UUID, patient_number: str
    ) -> Patient | None: ...

    @abstractmethod
    async def list_by_organization(
        self, organization_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[Patient]: ...

    @abstractmethod
    async def search(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        statuses: Sequence[PatientStatus] | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "created_at",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Patient], int]:
        """Search & Filtering module: organization-scoped search over
        patients, combining full-text search (`first_name`/`last_name`/
        `preferred_name`) with a partial `patient_number` match in a single
        `query` parameter, plus status/date-range filtering, sorting, and
        SQL-level pagination — see
        `app.infrastructure.database.query_utils` for the building blocks
        and `SqlAlchemyPatientRepository.search` for how they compose.
        Returns `(page_of_patients, total_matching_count)`; the count
        reflects every filter but not `offset`/`limit`."""
        ...

    @abstractmethod
    async def add(self, patient: Patient) -> None: ...


class PatientContactRepository(ABC):
    @abstractmethod
    async def get_by_id(self, contact_id: UUID) -> PatientContact | None: ...

    @abstractmethod
    async def list_by_patient(self, patient_id: UUID) -> list[PatientContact]: ...

    @abstractmethod
    async def unset_primary_for_patient_and_type(
        self, patient_id: UUID, contact_type: ContactType
    ) -> None:
        """Clear `is_primary` on every existing contact of `contact_type`
        for `patient_id` — called before adding a new primary contact of
        that type, so "one primary contact per contact type" holds
        without relying on the caller to check first."""
        ...

    @abstractmethod
    async def add(self, contact: PatientContact) -> None: ...


class EmergencyContactRepository(ABC):
    @abstractmethod
    async def get_by_id(self, contact_id: UUID) -> EmergencyContact | None: ...

    @abstractmethod
    async def list_by_patient(self, patient_id: UUID) -> list[EmergencyContact]: ...

    @abstractmethod
    async def unset_primary_for_patient(self, patient_id: UUID) -> None:
        """Clear `is_primary` on every existing emergency contact for
        `patient_id` — called before adding a new primary emergency
        contact, so "one primary emergency contact" holds without relying
        on the caller to check first."""
        ...

    @abstractmethod
    async def add(self, contact: EmergencyContact) -> None: ...


class InsuranceRepository(ABC):
    @abstractmethod
    async def get_by_id(self, insurance_id: UUID) -> Insurance | None: ...

    @abstractmethod
    async def list_by_patient(self, patient_id: UUID) -> list[Insurance]: ...

    @abstractmethod
    async def add(self, insurance: Insurance) -> None: ...


class PatientAllergyRepository(ABC):
    @abstractmethod
    async def get_by_id(self, allergy_id: UUID) -> PatientAllergy | None: ...

    @abstractmethod
    async def list_by_patient(self, patient_id: UUID) -> list[PatientAllergy]: ...

    @abstractmethod
    async def get_active_by_patient_and_allergen(
        self, *, patient_id: UUID, allergen_name: str
    ) -> PatientAllergy | None:
        """Used to enforce "duplicate active allergy (same patient +
        allergen) is not allowed" before adding a new one."""
        ...

    @abstractmethod
    async def add(self, allergy: PatientAllergy) -> None: ...


class PatientMedicationRepository(ABC):
    @abstractmethod
    async def get_by_id(self, medication_id: UUID) -> PatientMedication | None: ...

    @abstractmethod
    async def list_by_patient(self, patient_id: UUID) -> list[PatientMedication]: ...

    @abstractmethod
    async def add(self, medication: PatientMedication) -> None: ...


class PatientMedicalConditionRepository(ABC):
    @abstractmethod
    async def get_by_id(self, condition_id: UUID) -> PatientMedicalCondition | None: ...

    @abstractmethod
    async def list_by_patient(self, patient_id: UUID) -> list[PatientMedicalCondition]: ...

    @abstractmethod
    async def get_active_by_patient_and_condition_name(
        self, *, patient_id: UUID, condition_name: str
    ) -> PatientMedicalCondition | None:
        """Used to enforce "duplicate active conditions are not allowed"
        before adding a new one."""
        ...

    @abstractmethod
    async def add(self, condition: PatientMedicalCondition) -> None: ...
