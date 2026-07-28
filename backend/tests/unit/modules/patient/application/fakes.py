"""In-memory test doubles for the Patient module's repository, Unit of
Work, and the Organization module's cross-module port `RegisterPatient`
depends on — each implements the exact same interface its real
counterpart does, per
`docs/backend-architecture/12_testing_architecture.md` ("fakes over mocks
as the default"). Application-layer use case/service tests depend on
these, never on a real database or another module's facade.
"""

from uuid import UUID

from app.modules.doctor.public.dto import DoctorSummaryDTO
from app.modules.doctor.public.interfaces import DoctorQueryPort
from app.modules.organization.public.dto import OrganizationSummaryDTO
from app.modules.organization.public.interfaces import OrganizationQueryPort
from app.modules.patient.domain.entities import (
    EmergencyContact,
    Insurance,
    Patient,
    PatientAllergy,
    PatientContact,
    PatientMedicalCondition,
    PatientMedication,
)
from app.modules.patient.domain.enums import AllergyStatus, ConditionStatus, ContactType
from app.modules.patient.domain.repositories import (
    EmergencyContactRepository,
    InsuranceRepository,
    PatientAllergyRepository,
    PatientContactRepository,
    PatientMedicalConditionRepository,
    PatientMedicationRepository,
    PatientRepository,
)
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.domain.domain_event import DomainEvent


class FakePatientRepository(PatientRepository):
    def __init__(self) -> None:
        self._patients: dict[UUID, Patient] = {}

    async def get_by_id(self, patient_id: UUID) -> Patient | None:
        return self._patients.get(patient_id)

    async def get_by_patient_number(
        self, *, organization_id: UUID, patient_number: str
    ) -> Patient | None:
        for patient in self._patients.values():
            if (
                patient.organization_id == organization_id
                and patient.patient_number == patient_number.strip()
            ):
                return patient
        return None

    async def list_by_organization(
        self, organization_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[Patient]:
        matches = [p for p in self._patients.values() if p.organization_id == organization_id]
        return matches[offset : offset + limit]

    async def add(self, patient: Patient) -> None:
        self._patients[patient.id] = patient


class FakePatientContactRepository(PatientContactRepository):
    def __init__(self) -> None:
        self._contacts: dict[UUID, PatientContact] = {}

    async def get_by_id(self, contact_id: UUID) -> PatientContact | None:
        return self._contacts.get(contact_id)

    async def list_by_patient(self, patient_id: UUID) -> list[PatientContact]:
        return [c for c in self._contacts.values() if c.patient_id == patient_id]

    async def unset_primary_for_patient_and_type(
        self, patient_id: UUID, contact_type: ContactType
    ) -> None:
        for contact in self._contacts.values():
            if (
                contact.patient_id == patient_id
                and contact.contact_type == contact_type
                and contact.is_primary
            ):
                contact.is_primary = False

    async def add(self, contact: PatientContact) -> None:
        self._contacts[contact.id] = contact


class FakeEmergencyContactRepository(EmergencyContactRepository):
    def __init__(self) -> None:
        self._contacts: dict[UUID, EmergencyContact] = {}

    async def get_by_id(self, contact_id: UUID) -> EmergencyContact | None:
        return self._contacts.get(contact_id)

    async def list_by_patient(self, patient_id: UUID) -> list[EmergencyContact]:
        return [c for c in self._contacts.values() if c.patient_id == patient_id]

    async def unset_primary_for_patient(self, patient_id: UUID) -> None:
        for contact in self._contacts.values():
            if contact.patient_id == patient_id and contact.is_primary:
                contact.is_primary = False

    async def add(self, contact: EmergencyContact) -> None:
        self._contacts[contact.id] = contact


class FakeInsuranceRepository(InsuranceRepository):
    def __init__(self) -> None:
        self._insurance: dict[UUID, Insurance] = {}

    async def get_by_id(self, insurance_id: UUID) -> Insurance | None:
        return self._insurance.get(insurance_id)

    async def list_by_patient(self, patient_id: UUID) -> list[Insurance]:
        return [i for i in self._insurance.values() if i.patient_id == patient_id]

    async def add(self, insurance: Insurance) -> None:
        self._insurance[insurance.id] = insurance


class FakePatientAllergyRepository(PatientAllergyRepository):
    def __init__(self) -> None:
        self._allergies: dict[UUID, PatientAllergy] = {}

    async def get_by_id(self, allergy_id: UUID) -> PatientAllergy | None:
        return self._allergies.get(allergy_id)

    async def list_by_patient(self, patient_id: UUID) -> list[PatientAllergy]:
        return [a for a in self._allergies.values() if a.patient_id == patient_id]

    async def get_active_by_patient_and_allergen(
        self, *, patient_id: UUID, allergen_name: str
    ) -> PatientAllergy | None:
        normalized = allergen_name.strip().lower()
        for allergy in self._allergies.values():
            if (
                allergy.patient_id == patient_id
                and allergy.allergen_name.lower() == normalized
                and allergy.status is AllergyStatus.ACTIVE
            ):
                return allergy
        return None

    async def add(self, allergy: PatientAllergy) -> None:
        self._allergies[allergy.id] = allergy


class FakePatientMedicationRepository(PatientMedicationRepository):
    def __init__(self) -> None:
        self._medications: dict[UUID, PatientMedication] = {}

    async def get_by_id(self, medication_id: UUID) -> PatientMedication | None:
        return self._medications.get(medication_id)

    async def list_by_patient(self, patient_id: UUID) -> list[PatientMedication]:
        return [m for m in self._medications.values() if m.patient_id == patient_id]

    async def add(self, medication: PatientMedication) -> None:
        self._medications[medication.id] = medication


class FakePatientMedicalConditionRepository(PatientMedicalConditionRepository):
    def __init__(self) -> None:
        self._conditions: dict[UUID, PatientMedicalCondition] = {}

    async def get_by_id(self, condition_id: UUID) -> PatientMedicalCondition | None:
        return self._conditions.get(condition_id)

    async def list_by_patient(self, patient_id: UUID) -> list[PatientMedicalCondition]:
        return [c for c in self._conditions.values() if c.patient_id == patient_id]

    async def get_active_by_patient_and_condition_name(
        self, *, patient_id: UUID, condition_name: str
    ) -> PatientMedicalCondition | None:
        normalized = condition_name.strip().lower()
        for condition in self._conditions.values():
            if (
                condition.patient_id == patient_id
                and condition.condition_name.lower() == normalized
                and condition.status is ConditionStatus.ACTIVE
            ):
                return condition
        return None

    async def add(self, condition: PatientMedicalCondition) -> None:
        self._conditions[condition.id] = condition


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
    `RegisterPatient` only calls `organization_exists`."""

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


class FakeDoctorQueryPort(DoctorQueryPort):
    """Backed by a settable set of "existing" doctor ids —
    `RecordPatientAllergy` only calls `doctor_exists`."""

    def __init__(self, *, existing_doctor_ids: set[UUID] | None = None) -> None:
        self.existing_doctor_ids = existing_doctor_ids or set()

    async def doctor_exists(self, doctor_id: UUID) -> bool:
        return doctor_id in self.existing_doctor_ids

    async def is_active(self, doctor_id: UUID) -> bool:
        return doctor_id in self.existing_doctor_ids

    async def get_doctor_summary(self, doctor_id: UUID) -> DoctorSummaryDTO | None:
        raise NotImplementedError("not exercised by any use case tested against this fake")
