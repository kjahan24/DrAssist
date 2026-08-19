"""Unit tests for the Community Moderation module's application-layer
DTOs — construction with defaults, explicit overrides, and the `.id`
convenience properties every summary DTO exposes."""

from datetime import UTC, datetime
from uuid import uuid4

from app.modules.community_moderation.application.dto import (
    ApproveDoctorVerificationInput,
    AssignReportInput,
    ContentModerationInput,
    CreateModerationActionInput,
    CreateReportInput,
    GetModerationStatusInput,
    ListReportsInput,
    ModerationActionSummaryDTO,
    RejectDoctorVerificationInput,
    RejectReportInput,
    ReportFeedOutput,
    ReportSummaryDTO,
    RequestDoctorVerificationInput,
    ResolveReportInput,
    RestrictionSummaryDTO,
    RestrictUserInput,
    RevokeDoctorVerificationInput,
    SuspendUserInput,
    VerificationSummaryDTO,
    WarnUserInput,
)
from app.modules.community_moderation.domain.enums import (
    ModerationActionType,
    ModerationRestrictionType,
    ModerationTargetType,
    ReportPriority,
    ReportReason,
    ReportStatus,
    VerificationStatus,
)


class TestReportDTOs:
    def test_create_report_input_defaults_description_to_none(self) -> None:
        input_dto = CreateReportInput(
            organization_id=uuid4(),
            community_id=uuid4(),
            reporter_id=uuid4(),
            target_type=ModerationTargetType.POST,
            target_id=uuid4(),
            reason=ReportReason.SPAM,
        )
        assert input_dto.description is None

    def test_report_summary_dto_id_property_aliases_report_id(self) -> None:
        report_id = uuid4()
        now = datetime.now(UTC)
        summary = ReportSummaryDTO(
            report_id=report_id,
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
        assert summary.id == report_id

    def test_list_reports_input_defaults(self) -> None:
        input_dto = ListReportsInput(organization_id=uuid4())
        assert input_dto.community_id is None
        assert input_dto.status is None
        assert input_dto.priority is None
        assert input_dto.assigned_moderator_id is None
        assert input_dto.cursor is None
        assert input_dto.limit == 20

    def test_report_feed_output_defaults_next_cursor_to_none(self) -> None:
        output = ReportFeedOutput(items=[])
        assert output.next_cursor is None

    def test_assign_report_input_defaults_note_to_none(self) -> None:
        input_dto = AssignReportInput(report_id=uuid4(), moderator_id=uuid4(), community_id=uuid4())
        assert input_dto.note is None

    def test_resolve_report_input_requires_resolution(self) -> None:
        input_dto = ResolveReportInput(
            report_id=uuid4(),
            moderator_id=uuid4(),
            community_id=uuid4(),
            resolution="Content removed.",
        )
        assert input_dto.resolution == "Content removed."

    def test_reject_report_input_requires_resolution(self) -> None:
        input_dto = RejectReportInput(
            report_id=uuid4(),
            moderator_id=uuid4(),
            community_id=uuid4(),
            resolution="No violation.",
        )
        assert input_dto.resolution == "No violation."


class TestModerationActionDTOs:
    def test_create_moderation_action_input_defaults(self) -> None:
        input_dto = CreateModerationActionInput(
            organization_id=uuid4(),
            actor_id=uuid4(),
            action_type=ModerationActionType.RESTRICT,
            target_type=ModerationTargetType.POST,
            target_id=uuid4(),
            reason="Reason.",
        )
        assert input_dto.report_id is None
        assert input_dto.moderator_note is None

    def test_content_moderation_input_defaults(self) -> None:
        input_dto = ContentModerationInput(
            organization_id=uuid4(),
            actor_id=uuid4(),
            target_type=ModerationTargetType.POST,
            target_id=uuid4(),
            reason="Reason.",
        )
        assert input_dto.report_id is None
        assert input_dto.moderator_note is None

    def test_moderation_action_summary_dto_id_property_aliases_action_id(self) -> None:
        action_id = uuid4()
        summary = ModerationActionSummaryDTO(
            action_id=action_id,
            organization_id=uuid4(),
            actor_id=uuid4(),
            action_type=ModerationActionType.REMOVE,
            target_type=ModerationTargetType.POST,
            target_id=uuid4(),
            reason="Reason.",
            created_at=datetime.now(UTC),
        )
        assert summary.id == action_id


class TestRestrictionDTOs:
    def test_warn_user_input_defaults_report_id_to_none(self) -> None:
        input_dto = WarnUserInput(
            organization_id=uuid4(),
            community_id=uuid4(),
            moderator_id=uuid4(),
            user_id=uuid4(),
            reason="Reason.",
        )
        assert input_dto.report_id is None

    def test_restrict_user_input_requires_duration(self) -> None:
        input_dto = RestrictUserInput(
            organization_id=uuid4(),
            community_id=uuid4(),
            moderator_id=uuid4(),
            user_id=uuid4(),
            reason="Reason.",
            duration_days=7,
        )
        assert input_dto.duration_days == 7

    def test_suspend_user_input_defaults_duration_to_none(self) -> None:
        input_dto = SuspendUserInput(
            organization_id=uuid4(),
            community_id=uuid4(),
            moderator_id=uuid4(),
            user_id=uuid4(),
            reason="Reason.",
        )
        assert input_dto.duration_days is None

    def test_get_moderation_status_input_defaults_community_id_to_none(self) -> None:
        input_dto = GetModerationStatusInput(user_id=uuid4())
        assert input_dto.community_id is None

    def test_restriction_summary_dto_id_property_aliases_restriction_id(self) -> None:
        restriction_id = uuid4()
        now = datetime.now(UTC)
        summary = RestrictionSummaryDTO(
            restriction_id=restriction_id,
            organization_id=uuid4(),
            community_id=uuid4(),
            user_id=uuid4(),
            issued_by=uuid4(),
            restriction_type=ModerationRestrictionType.WARNING,
            reason="Reason.",
            starts_at=now,
            created_at=now,
        )
        assert summary.id == restriction_id


class TestDoctorVerificationDTOs:
    def test_request_doctor_verification_input_defaults(self) -> None:
        input_dto = RequestDoctorVerificationInput(doctor_id=uuid4(), requesting_user_id=uuid4())
        assert input_dto.specialty is None
        assert input_dto.metadata is None

    def test_approve_doctor_verification_input_defaults_specialty_to_none(self) -> None:
        input_dto = ApproveDoctorVerificationInput(verification_id=uuid4(), verifier_id=uuid4())
        assert input_dto.specialty is None

    def test_reject_doctor_verification_input_requires_reason(self) -> None:
        input_dto = RejectDoctorVerificationInput(
            verification_id=uuid4(), verifier_id=uuid4(), reason="Unverifiable."
        )
        assert input_dto.reason == "Unverifiable."

    def test_revoke_doctor_verification_input_requires_reason(self) -> None:
        input_dto = RevokeDoctorVerificationInput(
            verification_id=uuid4(), verifier_id=uuid4(), reason="Lapsed."
        )
        assert input_dto.reason == "Lapsed."

    def test_verification_summary_dto_id_property_aliases_verification_id(self) -> None:
        verification_id = uuid4()
        now = datetime.now(UTC)
        summary = VerificationSummaryDTO(
            verification_id=verification_id,
            doctor_id=uuid4(),
            user_id=uuid4(),
            organization_id=uuid4(),
            status=VerificationStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        assert summary.id == verification_id
        assert summary.metadata == {}
