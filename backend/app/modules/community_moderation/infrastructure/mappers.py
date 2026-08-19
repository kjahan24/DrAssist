"""ORM model <-> domain entity mappers for the Community Moderation
module. `ModerationRestrictionModel` has no `updated_at` column — see
`models.py`'s own docstring — so `updated_at=model.created_at` is
synthesized on load, the identical choice
`app.modules.community_engagement.infrastructure.mappers` already makes
for `SavedContent`/`TopicFollower`/etc.

`DoctorVerificationModel.verification_metadata` (not `metadata` — that
name is reserved by SQLAlchemy's `DeclarativeBase.metadata`) maps to/from
`DoctorVerification.metadata`.
"""

from app.modules.community_moderation.domain.entities import (
    CommunityReport,
    DoctorVerification,
    ModerationAction,
    ModerationRestriction,
)
from app.modules.community_moderation.infrastructure.models import (
    CommunityReportModel,
    DoctorVerificationModel,
    ModerationActionModel,
    ModerationRestrictionModel,
)


def report_to_domain(model: CommunityReportModel) -> CommunityReport:
    return CommunityReport(
        id=model.id,
        created_at=model.created_at,
        updated_at=model.updated_at,
        organization_id=model.organization_id,
        community_id=model.community_id,
        reporter_id=model.reporter_id,
        target_type=model.target_type,
        target_id=model.target_id,
        reason=model.reason,
        status=model.status,
        priority=model.priority,
        description=model.description,
        assigned_moderator_id=model.assigned_moderator_id,
        moderator_note=model.moderator_note,
        resolution=model.resolution,
        resolved_at=model.resolved_at,
    )


def apply_report_to_model(report: CommunityReport, model: CommunityReportModel) -> None:
    model.id = report.id
    model.organization_id = report.organization_id
    model.community_id = report.community_id
    model.reporter_id = report.reporter_id
    model.target_type = report.target_type
    model.target_id = report.target_id
    model.reason = report.reason
    model.status = report.status
    model.priority = report.priority
    model.description = report.description
    model.assigned_moderator_id = report.assigned_moderator_id
    model.moderator_note = report.moderator_note
    model.resolution = report.resolution
    model.resolved_at = report.resolved_at


def action_to_domain(model: ModerationActionModel) -> ModerationAction:
    return ModerationAction(
        id=model.id,
        created_at=model.created_at,
        organization_id=model.organization_id,
        actor_id=model.actor_id,
        action_type=model.action_type,
        target_type=model.target_type,
        target_id=model.target_id,
        reason=model.reason,
        report_id=model.report_id,
        moderator_note=model.moderator_note,
        previous_state=model.previous_state,
        new_state=model.new_state,
    )


def apply_action_to_model(action: ModerationAction, model: ModerationActionModel) -> None:
    model.id = action.id
    model.organization_id = action.organization_id
    model.actor_id = action.actor_id
    model.action_type = action.action_type
    model.target_type = action.target_type
    model.target_id = action.target_id
    model.reason = action.reason
    model.report_id = action.report_id
    model.moderator_note = action.moderator_note
    model.previous_state = action.previous_state
    model.new_state = action.new_state


def restriction_to_domain(model: ModerationRestrictionModel) -> ModerationRestriction:
    return ModerationRestriction(
        id=model.id,
        created_at=model.created_at,
        updated_at=model.created_at,
        organization_id=model.organization_id,
        community_id=model.community_id,
        user_id=model.user_id,
        issued_by=model.issued_by,
        restriction_type=model.restriction_type,
        reason=model.reason,
        starts_at=model.starts_at,
        ends_at=model.ends_at,
        report_id=model.report_id,
    )


def apply_restriction_to_model(
    restriction: ModerationRestriction, model: ModerationRestrictionModel
) -> None:
    model.id = restriction.id
    model.organization_id = restriction.organization_id
    model.community_id = restriction.community_id
    model.user_id = restriction.user_id
    model.issued_by = restriction.issued_by
    model.restriction_type = restriction.restriction_type
    model.reason = restriction.reason
    model.starts_at = restriction.starts_at
    model.ends_at = restriction.ends_at
    model.report_id = restriction.report_id


def verification_to_domain(model: DoctorVerificationModel) -> DoctorVerification:
    return DoctorVerification(
        id=model.id,
        created_at=model.created_at,
        updated_at=model.updated_at,
        doctor_id=model.doctor_id,
        user_id=model.user_id,
        organization_id=model.organization_id,
        status=model.status,
        specialty=model.specialty,
        verifier_id=model.verifier_id,
        verified_at=model.verified_at,
        rejection_reason=model.rejection_reason,
        revocation_reason=model.revocation_reason,
        metadata=dict(model.verification_metadata),
    )


def apply_verification_to_model(
    verification: DoctorVerification, model: DoctorVerificationModel
) -> None:
    model.id = verification.id
    model.doctor_id = verification.doctor_id
    model.user_id = verification.user_id
    model.organization_id = verification.organization_id
    model.status = verification.status
    model.specialty = verification.specialty
    model.verifier_id = verification.verifier_id
    model.verified_at = verification.verified_at
    model.rejection_reason = verification.rejection_reason
    model.revocation_reason = verification.revocation_reason
    model.verification_metadata = dict(verification.metadata)
