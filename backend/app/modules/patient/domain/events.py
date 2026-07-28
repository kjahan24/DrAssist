"""Domain events published by Patient module aggregates.

Recorded on an aggregate via `record_event()` and only actually published
(to the `EventBus`) after the transaction that raised them commits
successfully — see `app.shared.application.unit_of_work.UnitOfWork` and
`docs/backend-architecture/10_module_communication.md`.
"""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class PatientRegistered(DomainEvent):
    patient_id: UUID
    organization_id: UUID
    patient_number: str


@dataclass(frozen=True, kw_only=True)
class PatientDetailsUpdated(DomainEvent):
    patient_id: UUID
    organization_id: UUID


@dataclass(frozen=True, kw_only=True)
class PatientStatusChanged(DomainEvent):
    patient_id: UUID
    organization_id: UUID
    status: str


@dataclass(frozen=True, kw_only=True)
class PatientContactAdded(DomainEvent):
    contact_id: UUID
    patient_id: UUID
    contact_type: str
    is_primary: bool


@dataclass(frozen=True, kw_only=True)
class PatientContactUpdated(DomainEvent):
    contact_id: UUID
    patient_id: UUID


@dataclass(frozen=True, kw_only=True)
class EmergencyContactAdded(DomainEvent):
    contact_id: UUID
    patient_id: UUID
    is_primary: bool


@dataclass(frozen=True, kw_only=True)
class EmergencyContactUpdated(DomainEvent):
    contact_id: UUID
    patient_id: UUID


@dataclass(frozen=True, kw_only=True)
class InsuranceAdded(DomainEvent):
    insurance_id: UUID
    patient_id: UUID
    policy_number: str


@dataclass(frozen=True, kw_only=True)
class InsuranceUpdated(DomainEvent):
    insurance_id: UUID
    patient_id: UUID


@dataclass(frozen=True, kw_only=True)
class InsuranceStatusChanged(DomainEvent):
    insurance_id: UUID
    patient_id: UUID
    status: str


@dataclass(frozen=True, kw_only=True)
class PatientAllergyRecorded(DomainEvent):
    allergy_id: UUID
    patient_id: UUID
    allergen_name: str
    severity: str


@dataclass(frozen=True, kw_only=True)
class PatientAllergyUpdated(DomainEvent):
    allergy_id: UUID
    patient_id: UUID


@dataclass(frozen=True, kw_only=True)
class PatientAllergyStatusChanged(DomainEvent):
    allergy_id: UUID
    patient_id: UUID
    status: str


@dataclass(frozen=True, kw_only=True)
class PatientAllergyVerified(DomainEvent):
    allergy_id: UUID
    patient_id: UUID
    verified_by: UUID


@dataclass(frozen=True, kw_only=True)
class PatientMedicationAdded(DomainEvent):
    medication_id: UUID
    patient_id: UUID
    medication_name: str


@dataclass(frozen=True, kw_only=True)
class PatientMedicationUpdated(DomainEvent):
    medication_id: UUID
    patient_id: UUID


@dataclass(frozen=True, kw_only=True)
class PatientMedicationDiscontinued(DomainEvent):
    medication_id: UUID
    patient_id: UUID
    end_date: date


@dataclass(frozen=True, kw_only=True)
class PatientMedicationResumed(DomainEvent):
    medication_id: UUID
    patient_id: UUID


@dataclass(frozen=True, kw_only=True)
class PatientMedicalConditionRecorded(DomainEvent):
    condition_id: UUID
    patient_id: UUID
    condition_name: str


@dataclass(frozen=True, kw_only=True)
class PatientMedicalConditionUpdated(DomainEvent):
    condition_id: UUID
    patient_id: UUID


@dataclass(frozen=True, kw_only=True)
class PatientMedicalConditionResolved(DomainEvent):
    condition_id: UUID
    patient_id: UUID
    resolved_date: date


@dataclass(frozen=True, kw_only=True)
class PatientMedicalConditionReactivated(DomainEvent):
    condition_id: UUID
    patient_id: UUID
