"""Domain exceptions for the Community Moderation module.

Naming follows the codebase-wide convention `app.middlewares.error_handler
._map_domain_error` relies on: a name containing "NotFound" maps to 404; a
name containing "Duplicate"/"AlreadyExists"/"Transition"/"Immutable"/
"Inactive" maps to 409; everything else maps to 422. See that module's own
docstring for the full heuristic. `Already<X>Error`/`NotFound`-shaped
transition guards (e.g. `DoctorVerificationNotPendingError`) therefore
resolve to 422, not 409 — the same outcome every other module's identical
`*AlreadyPublishedError`/`*CannotBeRestoredError` shape already produces
(none of those contain the literal substring "AlreadyExists" either), so
this is consistency with existing precedent, not a new convention.

`ReportTargetNotFoundError`/`DoctorNotFoundForVerificationError` are
raised for *both* "genuinely doesn't exist" and "belongs to a different
organization" — the same deliberate tenant-isolation-via-indistinguishable-
404 shape `app.modules.community_engagement.domain.exceptions
.VoteTargetNotFoundError`'s own docstring establishes.
"""

from uuid import UUID

from app.modules.community_moderation.domain.enums import ModerationActionType, ModerationTargetType
from app.shared.domain.exceptions import DomainError


class ReportNotFoundError(DomainError):
    def __init__(self, report_id: UUID) -> None:
        self.report_id = report_id
        super().__init__(f"No report found with id {report_id}.")


class ReportTargetNotFoundError(DomainError):
    def __init__(self, target_id: UUID) -> None:
        self.target_id = target_id
        super().__init__(f"No report target found with id {target_id}.")


class UnsupportedModerationTargetTypeError(DomainError):
    def __init__(self, target_type: ModerationTargetType) -> None:
        self.target_type = target_type
        super().__init__(f"Content of type {target_type.value!r} cannot be moderated as content.")


class UnsupportedModerationActionTypeError(DomainError):
    def __init__(self, action_type: ModerationActionType) -> None:
        self.action_type = action_type
        super().__init__(
            f"Action {action_type.value!r} cannot be recorded against a content target."
        )


class DuplicateOpenReportError(DomainError):
    def __init__(self, reporter_id: UUID, target_id: UUID) -> None:
        self.reporter_id = reporter_id
        self.target_id = target_id
        super().__init__(
            f"User {reporter_id} already has an open report against target {target_id}."
        )


class ReportAlreadyClosedError(DomainError):
    def __init__(self, report_id: UUID) -> None:
        self.report_id = report_id
        super().__init__(f"Report {report_id} has already been resolved or rejected.")


class ContentActionTargetNotFoundError(DomainError):
    def __init__(self, target_id: UUID) -> None:
        self.target_id = target_id
        super().__init__(f"No content found with id {target_id} to moderate.")


class ModerationReasonRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("A moderation action requires a non-empty reason.")


class DoctorNotFoundForVerificationError(DomainError):
    def __init__(self, doctor_id: UUID) -> None:
        self.doctor_id = doctor_id
        super().__init__(f"No doctor found with id {doctor_id}.")


class DoctorVerificationNotFoundError(DomainError):
    def __init__(self, verification_id: UUID) -> None:
        self.verification_id = verification_id
        super().__init__(f"No verification found with id {verification_id}.")


class DoctorVerificationAlreadyPendingError(DomainError):
    def __init__(self, doctor_id: UUID) -> None:
        self.doctor_id = doctor_id
        super().__init__(f"Doctor {doctor_id} already has a pending verification request.")


class DoctorVerificationAlreadyVerifiedError(DomainError):
    def __init__(self, doctor_id: UUID) -> None:
        self.doctor_id = doctor_id
        super().__init__(f"Doctor {doctor_id} is already verified.")


class DoctorVerificationNotPendingError(DomainError):
    def __init__(self, verification_id: UUID) -> None:
        self.verification_id = verification_id
        super().__init__(f"Verification {verification_id} is not pending review.")


class DoctorVerificationNotVerifiedError(DomainError):
    def __init__(self, verification_id: UUID) -> None:
        self.verification_id = verification_id
        super().__init__(f"Verification {verification_id} is not currently verified.")


class DoctorVerificationCannotBeResubmittedError(DomainError):
    def __init__(self, verification_id: UUID) -> None:
        self.verification_id = verification_id
        super().__init__(f"Verification {verification_id} cannot be resubmitted from its status.")


class CannotVerifySelfError(DomainError):
    def __init__(self, user_id: UUID) -> None:
        self.user_id = user_id
        super().__init__(f"User {user_id} cannot review their own verification request.")


class UserNotFoundForModerationError(DomainError):
    def __init__(self, user_id: UUID) -> None:
        self.user_id = user_id
        super().__init__(f"No user found with id {user_id}.")


class CannotModerateSelfError(DomainError):
    def __init__(self, user_id: UUID) -> None:
        self.user_id = user_id
        super().__init__(f"User {user_id} cannot take moderation action against themselves.")


class ModerationMembershipRequiredError(DomainError):
    def __init__(self, community_id: UUID, user_id: UUID) -> None:
        self.community_id = community_id
        self.user_id = user_id
        super().__init__(f"User {user_id} is not an active member of community {community_id}.")


class InsufficientModeratorRoleError(DomainError):
    def __init__(self, community_id: UUID, user_id: UUID) -> None:
        self.community_id = community_id
        self.user_id = user_id
        super().__init__(
            f"User {user_id} does not have moderator rank in community {community_id}."
        )


class InsufficientAdminRoleError(DomainError):
    def __init__(self, community_id: UUID, user_id: UUID) -> None:
        self.community_id = community_id
        self.user_id = user_id
        super().__init__(f"User {user_id} does not have admin rank in community {community_id}.")
