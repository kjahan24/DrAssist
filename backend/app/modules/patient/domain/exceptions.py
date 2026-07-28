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
