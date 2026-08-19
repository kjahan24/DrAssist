"""Sanity tests confirming every enum member the task's own FEATURES/
DOMAIN sections name is actually present."""

from app.modules.community_moderation.domain.enums import (
    ContentModerationStatus,
    ModerationActionType,
    ModerationRestrictionType,
    ModerationTargetType,
    ReportPriority,
    ReportReason,
    ReportStatus,
    VerificationStatus,
)


class TestModerationTargetType:
    def test_has_every_reportable_target(self) -> None:
        assert {member.value for member in ModerationTargetType} == {
            "post",
            "question",
            "answer",
            "comment",
            "community",
            "user",
        }


class TestReportReason:
    def test_has_every_named_reason(self) -> None:
        assert {member.value for member in ReportReason} == {
            "medical_misinformation",
            "spam",
            "harassment",
            "abuse",
            "hate_discrimination",
            "privacy_violation",
            "impersonation",
            "dangerous_medical_advice",
            "self_harm_concern",
            "illegal_content",
            "other",
        }


class TestReportStatus:
    def test_has_every_lifecycle_state(self) -> None:
        assert {member.value for member in ReportStatus} == {
            "open",
            "under_review",
            "resolved",
            "rejected",
        }


class TestReportPriority:
    def test_has_every_priority_level(self) -> None:
        assert {member.value for member in ReportPriority} == {"low", "medium", "high", "critical"}


class TestModerationActionType:
    def test_has_every_named_action(self) -> None:
        assert {member.value for member in ModerationActionType} == {
            "approve",
            "remove",
            "restrict",
            "lock",
            "restore",
            "warn_user",
            "restrict_user",
            "suspend_user",
            "ban_user",
        }


class TestContentModerationStatus:
    def test_has_every_content_state(self) -> None:
        assert {member.value for member in ContentModerationStatus} == {
            "active",
            "removed",
            "restricted",
            "locked",
        }


class TestVerificationStatus:
    def test_has_every_verification_state(self) -> None:
        assert {member.value for member in VerificationStatus} == {
            "pending",
            "verified",
            "rejected",
            "revoked",
        }


class TestModerationRestrictionType:
    def test_has_every_restriction_type(self) -> None:
        assert {member.value for member in ModerationRestrictionType} == {
            "warning",
            "temporary_restriction",
            "suspension",
            "permanent_ban",
        }
