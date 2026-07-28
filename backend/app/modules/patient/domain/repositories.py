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
from uuid import UUID

from app.modules.patient.domain.entities import (
    EmergencyContact,
    Insurance,
    Patient,
    PatientAllergy,
    PatientContact,
    PatientMedication,
)
from app.modules.patient.domain.enums import ContactType


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
