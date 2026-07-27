"""Domain exceptions for the Organization module.

Each names the invariant it protects, not the eventual HTTP outcome — see
`docs/backend-architecture/06_configuration_logging_exceptions.md`.
"""

from uuid import UUID

from app.shared.domain.exceptions import DomainError


class OrganizationNameRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("organization name must not be blank")


class InvalidOrganizationCodeError(DomainError):
    def __init__(self, value: str) -> None:
        super().__init__(f"{value!r} is not a valid organization code")
        self.value = value


class DuplicateOrganizationCodeError(DomainError):
    def __init__(self, organization_code: str) -> None:
        super().__init__(f"an organization with code {organization_code!r} already exists")
        self.organization_code = organization_code


class OrganizationNotFoundError(DomainError):
    def __init__(self, organization_id: UUID) -> None:
        super().__init__(f"no organization found with id {organization_id}")
        self.organization_id = organization_id


class InvalidAppointmentDurationError(DomainError):
    def __init__(self, minutes: int) -> None:
        super().__init__(f"appointment_duration_minutes must be positive, got {minutes}")
        self.minutes = minutes


class OrganizationSettingsNotFoundError(DomainError):
    def __init__(self, organization_id: UUID) -> None:
        super().__init__(f"no settings found for organization {organization_id}")
        self.organization_id = organization_id


class OrganizationSettingsAlreadyExistError(DomainError):
    """Raised if code ever attempts to create a second settings row for the
    same organization — `OrganizationSettings` is one-to-one with
    `Organization` (see module docstring in `container.py`).
    """

    def __init__(self, organization_id: UUID) -> None:
        super().__init__(f"organization {organization_id} already has settings")
        self.organization_id = organization_id


class DepartmentNameRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("department name must not be blank")


class DepartmentNotFoundError(DomainError):
    def __init__(self, department_id: UUID) -> None:
        super().__init__(f"no department found with id {department_id}")
        self.department_id = department_id
