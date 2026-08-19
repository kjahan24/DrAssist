"""Validation tests for the Community Moderation module's Pydantic v2
request/response schemas."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.community_moderation.domain.enums import (
    ModerationActionType,
    ModerationRestrictionType,
    ModerationTargetType,
    ReportPriority,
    ReportReason,
    ReportStatus,
    VerificationStatus,
)
from app.modules.community_moderation.presentation.schemas import (
    ApproveDoctorVerificationRequest,
    AssignReportRequest,
    ContentModerationRequest,
    CreateModerationActionRequest,
    CreateReportRequest,
    ModerationActionResponse,
    ModerationStatusResponse,
    RejectDoctorVerificationRequest,
    RejectReportRequest,
    ReportFeedResponse,
    ReportResponse,
    RequestDoctorVerificationRequest,
    ResolveReportRequest,
    RestrictionResponse,
    RestrictUserRequest,
    RevokeDoctorVerificationRequest,
    SuspendUserRequest,
    VerificationResponse,
    WarnUserRequest,
)


class TestCreateReportRequest:
    def test_constructs_with_only_required_fields(self) -> None:
        request = CreateReportRequest(
            community_id=uuid4(),
            target_type=ModerationTargetType.POST,
            target_id=uuid4(),
            reason=ReportReason.SPAM,
        )
        assert request.description is None

    def test_description_over_max_length_raises(self) -> None:
        with pytest.raises(ValidationError):
            CreateReportRequest(
                community_id=uuid4(),
                target_type=ModerationTargetType.POST,
                target_id=uuid4(),
                reason=ReportReason.SPAM,
                description="x" * 2001,
            )


class TestReportActionRequests:
    def test_assign_report_request_defaults_note_to_none(self) -> None:
        request = AssignReportRequest(community_id=uuid4())
        assert request.note is None

    def test_resolve_report_request_requires_non_empty_resolution(self) -> None:
        with pytest.raises(ValidationError):
            ResolveReportRequest(community_id=uuid4(), resolution="")

    def test_reject_report_request_requires_non_empty_resolution(self) -> None:
        with pytest.raises(ValidationError):
            RejectReportRequest(community_id=uuid4(), resolution="")


class TestModerationActionRequests:
    def test_create_moderation_action_request_requires_non_empty_reason(self) -> None:
        with pytest.raises(ValidationError):
            CreateModerationActionRequest(
                action_type=ModerationActionType.RESTRICT,
                target_type=ModerationTargetType.POST,
                target_id=uuid4(),
                reason="",
            )

    def test_content_moderation_request_defaults(self) -> None:
        request = ContentModerationRequest(
            target_type=ModerationTargetType.POST, target_id=uuid4(), reason="Reason."
        )
        assert request.report_id is None
        assert request.moderator_note is None


class TestUserRestrictionRequests:
    def test_warn_user_request_defaults_report_id_to_none(self) -> None:
        request = WarnUserRequest(community_id=uuid4(), reason="Reason.")
        assert request.report_id is None

    def test_restrict_user_request_requires_positive_duration(self) -> None:
        with pytest.raises(ValidationError):
            RestrictUserRequest(community_id=uuid4(), reason="Reason.", duration_days=0)

    def test_restrict_user_request_rejects_excessive_duration(self) -> None:
        with pytest.raises(ValidationError):
            RestrictUserRequest(community_id=uuid4(), reason="Reason.", duration_days=4000)

    def test_suspend_user_request_defaults_duration_to_none(self) -> None:
        request = SuspendUserRequest(community_id=uuid4(), reason="Reason.")
        assert request.duration_days is None

    def test_suspend_user_request_accepts_a_positive_duration(self) -> None:
        request = SuspendUserRequest(community_id=uuid4(), reason="Reason.", duration_days=30)
        assert request.duration_days == 30


class TestDoctorVerificationRequests:
    def test_request_doctor_verification_request_defaults(self) -> None:
        request = RequestDoctorVerificationRequest()
        assert request.specialty is None
        assert request.metadata is None

    def test_approve_doctor_verification_request_defaults_specialty_to_none(self) -> None:
        request = ApproveDoctorVerificationRequest()
        assert request.specialty is None

    def test_reject_doctor_verification_request_requires_non_empty_reason(self) -> None:
        with pytest.raises(ValidationError):
            RejectDoctorVerificationRequest(reason="")

    def test_revoke_doctor_verification_request_requires_non_empty_reason(self) -> None:
        with pytest.raises(ValidationError):
            RevokeDoctorVerificationRequest(reason="")


class TestReportResponse:
    def test_constructs_from_a_full_field_set(self) -> None:
        now = datetime.now(UTC)
        response = ReportResponse(
            id=uuid4(),
            organization_id=uuid4(),
            community_id=uuid4(),
            reporter_id=uuid4(),
            target_type=ModerationTargetType.POST,
            target_id=uuid4(),
            reason=ReportReason.SPAM,
            status=ReportStatus.OPEN,
            priority=ReportPriority.MEDIUM,
            created_at=now,
            updated_at=now,
        )
        assert response.status is ReportStatus.OPEN


class TestReportFeedResponse:
    def test_defaults_next_cursor_to_none(self) -> None:
        response = ReportFeedResponse(items=[])
        assert response.next_cursor is None


class TestModerationActionResponse:
    def test_constructs_from_a_full_field_set(self) -> None:
        response = ModerationActionResponse(
            id=uuid4(),
            organization_id=uuid4(),
            actor_id=uuid4(),
            action_type=ModerationActionType.REMOVE,
            target_type=ModerationTargetType.POST,
            target_id=uuid4(),
            reason="Reason.",
            created_at=datetime.now(UTC),
        )
        assert response.action_type is ModerationActionType.REMOVE


class TestRestrictionResponse:
    def test_constructs_from_a_full_field_set(self) -> None:
        now = datetime.now(UTC)
        response = RestrictionResponse(
            id=uuid4(),
            organization_id=uuid4(),
            community_id=uuid4(),
            user_id=uuid4(),
            issued_by=uuid4(),
            restriction_type=ModerationRestrictionType.WARNING,
            reason="Reason.",
            starts_at=now,
            created_at=now,
        )
        assert response.restriction_type is ModerationRestrictionType.WARNING


class TestModerationStatusResponse:
    def test_constructs_from_a_full_field_set(self) -> None:
        response = ModerationStatusResponse(
            user_id=uuid4(),
            community_id=None,
            current_restriction_type=None,
            restricted_until=None,
            active_restriction_count=0,
            is_restricted=False,
        )
        assert response.is_restricted is False


class TestVerificationResponse:
    def test_constructs_from_a_full_field_set(self) -> None:
        now = datetime.now(UTC)
        response = VerificationResponse(
            id=uuid4(),
            doctor_id=uuid4(),
            user_id=uuid4(),
            organization_id=uuid4(),
            status=VerificationStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        assert response.status is VerificationStatus.PENDING
        assert response.metadata == {}
