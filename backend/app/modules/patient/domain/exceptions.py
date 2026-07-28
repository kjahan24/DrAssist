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
