"""Data Transfer Objects for the Patient module's application layer.

Distinct from both domain entities (never leave the module) and API
schemas (`api/schemas.py`, not yet wired to any endpoint). Use-case
input/output DTOs are plain, immutable dataclasses; `PatientSummaryDTO` is
also re-exported from `public/dto.py` for other modules to depend on.
"""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.modules.patient.domain.enums import (
    AdherenceStatus,
    AllergySeverity,
    AllergyStatus,
    AllergyType,
    BloodGroup,
    ConditionSeverity,
    ConditionStatus,
    ContactType,
    Gender,
    InsuranceStatus,
    MaritalStatus,
    PatientStatus,
    RouteOfAdministration,
)

# --- RegisterPatient --------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RegisterPatientInput:
    organization_id: UUID
    patient_number: str
    first_name: str
    last_name: str
    gender: Gender
    date_of_birth: date
    middle_name: str | None = None
    preferred_name: str | None = None
    blood_group: BloodGroup | None = None
    marital_status: MaritalStatus | None = None
    national_id: str | None = None
    passport_number: str | None = None
    phone: str | None = None
    email: str | None = None
    occupation: str | None = None
    nationality: str | None = None
    language: str | None = None
    religion: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    photo_url: str | None = None
    remarks: str | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class RegisterPatientOutput:
    patient_id: UUID
    organization_id: UUID
    patient_number: str
    status: PatientStatus


# --- AddPatientContact ------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AddPatientContactInput:
    patient_id: UUID
    contact_type: ContactType
    phone_number: str
    email: str | None = None
    is_primary: bool = False
    is_verified: bool = False
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class AddPatientContactOutput:
    contact_id: UUID
    patient_id: UUID
    contact_type: ContactType
    is_primary: bool


# --- AddEmergencyContact -----------------------------------------------------


@dataclass(frozen=True, slots=True)
class AddEmergencyContactInput:
    patient_id: UUID
    full_name: str
    relationship: str
    phone_number: str
    email: str | None = None
    address: str | None = None
    priority: int | None = None
    is_primary: bool = False
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class AddEmergencyContactOutput:
    contact_id: UUID
    patient_id: UUID
    full_name: str
    is_primary: bool


# --- AddInsurance -------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AddInsuranceInput:
    patient_id: UUID
    provider_name: str
    policy_number: str
    effective_date: date
    expiry_date: date
    member_id: str | None = None
    group_number: str | None = None
    coverage_type: str | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class AddInsuranceOutput:
    insurance_id: UUID
    patient_id: UUID
    policy_number: str
    status: InsuranceStatus


# --- RecordPatientAllergy ----------------------------------------------------


@dataclass(frozen=True, slots=True)
class RecordPatientAllergyInput:
    patient_id: UUID
    allergy_type: AllergyType
    allergen_name: str
    severity: AllergySeverity
    reaction: str | None = None
    onset_date: date | None = None
    notes: str | None = None
    verified_by: UUID | None = None
    verified_date: date | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class RecordPatientAllergyOutput:
    allergy_id: UUID
    patient_id: UUID
    allergen_name: str
    severity: AllergySeverity
    status: AllergyStatus


# --- AddPatientMedication -----------------------------------------------------


@dataclass(frozen=True, slots=True)
class AddPatientMedicationInput:
    patient_id: UUID
    medication_name: str
    dosage: str
    route: RouteOfAdministration
    start_date: date
    prescribed_by: UUID | None = None
    generic_name: str | None = None
    brand_name: str | None = None
    dosage_unit: str | None = None
    frequency: str | None = None
    indication: str | None = None
    end_date: date | None = None
    is_current: bool = True
    adherence_status: AdherenceStatus = AdherenceStatus.TAKING
    instructions: str | None = None
    notes: str | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class AddPatientMedicationOutput:
    medication_id: UUID
    patient_id: UUID
    medication_name: str
    is_current: bool
    adherence_status: AdherenceStatus


# --- AddPatientMedicalCondition ------------------------------------------------


@dataclass(frozen=True, slots=True)
class AddPatientMedicalConditionInput:
    patient_id: UUID
    condition_name: str
    category: str
    severity: ConditionSeverity
    diagnosis_date: date
    diagnosed_by: UUID | None = None
    icd10_code: str | None = None
    onset_date: date | None = None
    status: ConditionStatus = ConditionStatus.ACTIVE
    is_chronic: bool = False
    is_infectious: bool = False
    notes: str | None = None
    resolved_date: date | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class AddPatientMedicalConditionOutput:
    condition_id: UUID
    patient_id: UUID
    condition_name: str
    status: ConditionStatus


# --- Cross-cutting read models (also re-exported via public/dto.py) --------


@dataclass(frozen=True, slots=True)
class PatientSummaryDTO:
    patient_id: UUID
    organization_id: UUID
    patient_number: str
    first_name: str
    last_name: str
    gender: Gender
    date_of_birth: date
    status: PatientStatus
    middle_name: str | None = None
    preferred_name: str | None = None
    blood_group: BloodGroup | None = None
    marital_status: MaritalStatus | None = None
    national_id: str | None = None
    passport_number: str | None = None
    phone: str | None = None
    email: str | None = None
    occupation: str | None = None
    nationality: str | None = None
    language: str | None = None
    religion: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    photo_url: str | None = None
    remarks: str | None = None

    @property
    def id(self) -> UUID:
        """Alias for `patient_id` — see `AppointmentSummaryDTO.id`'s own
        docstring in `app.modules.appointment.application.dto` for the
        full reasoning (identical situation in every module)."""
        return self.patient_id


# --- Sub-resource read models (added by the REST APIs task) ----------------
#
# These six DTOs and the query service that builds them
# (`application/services/patient_sub_resource_query_service.py`) did not
# exist before this task: `PatientQueryService` only ever covered the
# `Patient` aggregate itself. `api/schemas.py`'s own
# `PatientContactResponse`/`EmergencyContactResponse`/`InsuranceResponse`/
# `PatientAllergyResponse`/`PatientMedicationResponse`/
# `PatientMedicalConditionResponse` (built in this module's original
# task, before endpoints existed) already expected this data to be
# readable; this task adds the read path those response schemas were
# always waiting for. Deliberately *not* added as new methods on
# `PatientQueryService` itself — that would require new required
# constructor parameters (six more repositories), a breaking change to
# every existing caller of `PatientQueryService(...)` — see that
# service's own docstring for why six small, additive, single-repository
# classes were used instead.


@dataclass(frozen=True, slots=True)
class PatientContactSummaryDTO:
    contact_id: UUID
    organization_id: UUID
    patient_id: UUID
    contact_type: ContactType
    phone_number: str
    email: str | None
    is_primary: bool
    is_verified: bool

    @property
    def id(self) -> UUID:
        """Alias for `contact_id` — see `AppointmentSummaryDTO.id`'s own
        docstring in `app.modules.appointment.application.dto` for the
        full reasoning (identical situation in every module)."""
        return self.contact_id


@dataclass(frozen=True, slots=True)
class EmergencyContactSummaryDTO:
    contact_id: UUID
    organization_id: UUID
    patient_id: UUID
    full_name: str
    relationship: str
    phone_number: str
    email: str | None
    address: str | None
    priority: int | None
    is_primary: bool

    @property
    def id(self) -> UUID:
        """Alias for `contact_id` — see `AppointmentSummaryDTO.id`'s own
        docstring in `app.modules.appointment.application.dto` for the
        full reasoning (identical situation in every module)."""
        return self.contact_id


@dataclass(frozen=True, slots=True)
class InsuranceSummaryDTO:
    insurance_id: UUID
    organization_id: UUID
    patient_id: UUID
    provider_name: str
    policy_number: str
    member_id: str | None
    group_number: str | None
    coverage_type: str | None
    effective_date: date
    expiry_date: date
    status: InsuranceStatus

    @property
    def id(self) -> UUID:
        """Alias for `insurance_id` — see `AppointmentSummaryDTO.id`'s own
        docstring in `app.modules.appointment.application.dto` for the
        full reasoning (identical situation in every module)."""
        return self.insurance_id


@dataclass(frozen=True, slots=True)
class PatientAllergySummaryDTO:
    allergy_id: UUID
    organization_id: UUID
    patient_id: UUID
    allergy_type: AllergyType
    allergen_name: str
    severity: AllergySeverity
    reaction: str | None
    onset_date: date | None
    status: AllergyStatus
    notes: str | None
    verified_by: UUID | None
    verified_date: date | None

    @property
    def id(self) -> UUID:
        """Alias for `allergy_id` — see `AppointmentSummaryDTO.id`'s own
        docstring in `app.modules.appointment.application.dto` for the
        full reasoning (identical situation in every module)."""
        return self.allergy_id


@dataclass(frozen=True, slots=True)
class PatientMedicationSummaryDTO:
    medication_id: UUID
    organization_id: UUID
    patient_id: UUID
    prescribed_by: UUID | None
    medication_name: str
    generic_name: str | None
    brand_name: str | None
    dosage: str
    dosage_unit: str | None
    route: RouteOfAdministration
    frequency: str | None
    indication: str | None
    start_date: date
    end_date: date | None
    is_current: bool
    adherence_status: AdherenceStatus
    instructions: str | None
    notes: str | None

    @property
    def id(self) -> UUID:
        """Alias for `medication_id` — see `AppointmentSummaryDTO.id`'s
        own docstring in `app.modules.appointment.application.dto` for
        the full reasoning (identical situation in every module)."""
        return self.medication_id


@dataclass(frozen=True, slots=True)
class PatientMedicalConditionSummaryDTO:
    condition_id: UUID
    organization_id: UUID
    patient_id: UUID
    diagnosed_by: UUID | None
    condition_name: str
    icd10_code: str | None
    category: str
    severity: ConditionSeverity
    diagnosis_date: date
    onset_date: date | None
    status: ConditionStatus
    is_chronic: bool
    is_infectious: bool
    notes: str | None
    resolved_date: date | None

    @property
    def id(self) -> UUID:
        """Alias for `condition_id` — see `AppointmentSummaryDTO.id`'s own
        docstring in `app.modules.appointment.application.dto` for the
        full reasoning (identical situation in every module)."""
        return self.condition_id
