"""Sanity tests confirming every domain exception carries the identifying
fields its raising site relies on, and that each message is non-empty."""

from uuid import uuid4

from app.modules.community_moderation.domain.enums import ModerationTargetType
from app.modules.community_moderation.domain.exceptions import (
    CannotModerateSelfError,
    CannotVerifySelfError,
    ContentActionTargetNotFoundError,
    DoctorNotFoundForVerificationError,
    DoctorVerificationAlreadyPendingError,
    DoctorVerificationAlreadyVerifiedError,
    DoctorVerificationCannotBeResubmittedError,
    DoctorVerificationNotFoundError,
    DoctorVerificationNotPendingError,
    DoctorVerificationNotVerifiedError,
    DuplicateOpenReportError,
    InsufficientAdminRoleError,
    InsufficientModeratorRoleError,
    ModerationMembershipRequiredError,
    ModerationReasonRequiredError,
    ReportAlreadyClosedError,
    ReportNotFoundError,
    ReportTargetNotFoundError,
    UnsupportedModerationTargetTypeError,
    UserNotFoundForModerationError,
)


class TestExceptionsCarryIdentifyingFields:
    def test_report_not_found(self) -> None:
        report_id = uuid4()
        exc = ReportNotFoundError(report_id)
        assert exc.report_id == report_id
        assert str(report_id) in str(exc)

    def test_report_target_not_found(self) -> None:
        target_id = uuid4()
        exc = ReportTargetNotFoundError(target_id)
        assert exc.target_id == target_id

    def test_unsupported_moderation_target_type(self) -> None:
        exc = UnsupportedModerationTargetTypeError(ModerationTargetType.COMMUNITY)
        assert exc.target_type is ModerationTargetType.COMMUNITY
        assert "community" in str(exc)

    def test_duplicate_open_report(self) -> None:
        reporter_id, target_id = uuid4(), uuid4()
        exc = DuplicateOpenReportError(reporter_id, target_id)
        assert exc.reporter_id == reporter_id
        assert exc.target_id == target_id

    def test_report_already_closed(self) -> None:
        report_id = uuid4()
        exc = ReportAlreadyClosedError(report_id)
        assert exc.report_id == report_id

    def test_content_action_target_not_found(self) -> None:
        target_id = uuid4()
        exc = ContentActionTargetNotFoundError(target_id)
        assert exc.target_id == target_id

    def test_moderation_reason_required(self) -> None:
        exc = ModerationReasonRequiredError()
        assert str(exc)

    def test_doctor_not_found_for_verification(self) -> None:
        doctor_id = uuid4()
        exc = DoctorNotFoundForVerificationError(doctor_id)
        assert exc.doctor_id == doctor_id

    def test_doctor_verification_not_found(self) -> None:
        verification_id = uuid4()
        exc = DoctorVerificationNotFoundError(verification_id)
        assert exc.verification_id == verification_id

    def test_doctor_verification_already_pending(self) -> None:
        doctor_id = uuid4()
        exc = DoctorVerificationAlreadyPendingError(doctor_id)
        assert exc.doctor_id == doctor_id

    def test_doctor_verification_already_verified(self) -> None:
        doctor_id = uuid4()
        exc = DoctorVerificationAlreadyVerifiedError(doctor_id)
        assert exc.doctor_id == doctor_id

    def test_doctor_verification_not_pending(self) -> None:
        verification_id = uuid4()
        exc = DoctorVerificationNotPendingError(verification_id)
        assert exc.verification_id == verification_id

    def test_doctor_verification_not_verified(self) -> None:
        verification_id = uuid4()
        exc = DoctorVerificationNotVerifiedError(verification_id)
        assert exc.verification_id == verification_id

    def test_doctor_verification_cannot_be_resubmitted(self) -> None:
        verification_id = uuid4()
        exc = DoctorVerificationCannotBeResubmittedError(verification_id)
        assert exc.verification_id == verification_id

    def test_cannot_verify_self(self) -> None:
        user_id = uuid4()
        exc = CannotVerifySelfError(user_id)
        assert exc.user_id == user_id

    def test_user_not_found_for_moderation(self) -> None:
        user_id = uuid4()
        exc = UserNotFoundForModerationError(user_id)
        assert exc.user_id == user_id

    def test_cannot_moderate_self(self) -> None:
        user_id = uuid4()
        exc = CannotModerateSelfError(user_id)
        assert exc.user_id == user_id

    def test_moderation_membership_required(self) -> None:
        community_id, user_id = uuid4(), uuid4()
        exc = ModerationMembershipRequiredError(community_id, user_id)
        assert exc.community_id == community_id
        assert exc.user_id == user_id

    def test_insufficient_moderator_role(self) -> None:
        community_id, user_id = uuid4(), uuid4()
        exc = InsufficientModeratorRoleError(community_id, user_id)
        assert exc.community_id == community_id
        assert exc.user_id == user_id

    def test_insufficient_admin_role(self) -> None:
        community_id, user_id = uuid4(), uuid4()
        exc = InsufficientAdminRoleError(community_id, user_id)
        assert exc.community_id == community_id
        assert exc.user_id == user_id
