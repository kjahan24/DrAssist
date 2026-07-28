"""Domain exceptions for the Patient module.

Each names the invariant it protects, not the eventual HTTP outcome — see
`docs/backend-architecture/06_configuration_logging_exceptions.md`. Email
and phone format violations raise `InvalidEmailAddressError`/
`InvalidPhoneNumberError` directly from their shared value objects, not a
Patient-specific wrapper — see `app.shared.domain.common_value_objects`.
"""

from datetime import date
from uuid import UUID

from app.shared.domain.exceptions import DomainError


class PatientNumberRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("patient_number must not be blank")


class DuplicatePatientNumberError(DomainError):
    def __init__(self, organization_id: UUID, patient_number: str) -> None:
        super().__init__(
            f"patient_number {patient_number!r} already exists in organization {organization_id}"
        )
        self.organization_id = organization_id
        self.patient_number = patient_number


class PatientNotFoundError(DomainError):
    def __init__(self, patient_id: UUID) -> None:
        super().__init__(f"no patient found with id {patient_id}")
        self.patient_id = patient_id


class FirstNameRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("first_name must not be blank")


class LastNameRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("last_name must not be blank")


class FutureDateOfBirthError(DomainError):
    def __init__(self, date_of_birth: date) -> None:
        super().__init__(f"date_of_birth {date_of_birth} must not be in the future")
        self.date_of_birth = date_of_birth


class PatientContactNotFoundError(DomainError):
    def __init__(self, contact_id: UUID) -> None:
        super().__init__(f"no patient contact found with id {contact_id}")
        self.contact_id = contact_id


class EmergencyContactNameRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("full_name must not be blank")


class EmergencyContactRelationshipRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("relationship must not be blank")


class EmergencyContactNotFoundError(DomainError):
    def __init__(self, contact_id: UUID) -> None:
        super().__init__(f"no emergency contact found with id {contact_id}")
        self.contact_id = contact_id


class InsuranceProviderNameRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("provider_name must not be blank")


class InsurancePolicyNumberRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("policy_number must not be blank")


class InvalidInsuranceDateRangeError(DomainError):
    def __init__(self) -> None:
        super().__init__("expiry_date must be after effective_date")


class InsuranceNotFoundError(DomainError):
    def __init__(self, insurance_id: UUID) -> None:
        super().__init__(f"no insurance record found with id {insurance_id}")
        self.insurance_id = insurance_id


class AllergenNameRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("allergen_name must not be blank")


class DuplicateActiveAllergyError(DomainError):
    def __init__(self, patient_id: UUID, allergen_name: str) -> None:
        super().__init__(f"patient {patient_id} already has an active allergy to {allergen_name!r}")
        self.patient_id = patient_id
        self.allergen_name = allergen_name


class VerifiedDateRequiresVerifiedByError(DomainError):
    def __init__(self) -> None:
        super().__init__("verified_date must not be set without verified_by")


class PatientAllergyNotFoundError(DomainError):
    def __init__(self, allergy_id: UUID) -> None:
        super().__init__(f"no patient allergy found with id {allergy_id}")
        self.allergy_id = allergy_id


class MedicationNameRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("medication_name must not be blank")


class DosageRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("dosage must not be blank")


class InvalidMedicationDateRangeError(DomainError):
    def __init__(self) -> None:
        super().__init__("end_date must not be before start_date")


class EndDateRequiredForCompletedMedicationError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "end_date is required when is_current is false and adherence_status is completed"
        )


class PatientMedicationNotFoundError(DomainError):
    def __init__(self, medication_id: UUID) -> None:
        super().__init__(f"no patient medication found with id {medication_id}")
        self.medication_id = medication_id
