"""Domain exceptions for the Family / Caregiver Access module.

`PatientNotFoundError`/`CaregiverNotFoundError` are defined locally
rather than imported from the Patient/Authentication modules — the same
"no module exposes a not-found error a peer module is allowed to import"
reasoning `app.modules.appointment.domain.exceptions` and
`app.modules.documents.domain.exceptions` already establish for this
codebase (neither `app.modules.patient` nor `app.modules.authentication`
expose one across the `domain/` boundary; only their `public/` ports are
importable from outside).
"""

from uuid import UUID

from app.shared.domain.exceptions import DomainError


class PatientNotFoundError(DomainError):
    def __init__(self, patient_id: UUID) -> None:
        super().__init__(f"no patient found with id {patient_id}")
        self.patient_id = patient_id


class CaregiverNotFoundError(DomainError):
    def __init__(self, caregiver_user_id: UUID) -> None:
        super().__init__(f"no user found with id {caregiver_user_id}")
        self.caregiver_user_id = caregiver_user_id


class FamilyAccessNotFoundError(DomainError):
    def __init__(self, family_access_id: UUID) -> None:
        super().__init__(f"no family access grant found with id {family_access_id}")
        self.family_access_id = family_access_id


class InvitationNotFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__("no invitation found for the given token")


class InvalidInvitationTokenHashError(DomainError):
    def __init__(self, value: str) -> None:
        super().__init__(f"{value!r} is not a valid invitation token hash")
        self.value = value


class DuplicateActiveAccessError(DomainError):
    def __init__(self, patient_id: UUID, caregiver_user_id: UUID) -> None:
        super().__init__(
            f"caregiver {caregiver_user_id} already has active access to patient {patient_id}"
        )
        self.patient_id = patient_id
        self.caregiver_user_id = caregiver_user_id


class DuplicateInvitationTokenError(DomainError):
    def __init__(self) -> None:
        super().__init__("generated invitation token is already in use")


class InvitationExpiredError(DomainError):
    def __init__(self, family_access_id: UUID) -> None:
        super().__init__(f"invitation {family_access_id} has expired and cannot be accepted")
        self.family_access_id = family_access_id


class InvalidFamilyAccessStatusTransitionError(DomainError):
    def __init__(self, current_status: str, target_status: str) -> None:
        super().__init__(
            f"cannot transition family access grant from {current_status} to {target_status}"
        )
        self.current_status = current_status
        self.target_status = target_status
