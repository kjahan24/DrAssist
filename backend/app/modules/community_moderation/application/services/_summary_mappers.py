"""Maps domain entities to their application-layer summary DTOs — kept
separate from the services themselves so every service and the public
facade share exactly one mapping definition per entity, the same split
every prior module's own `_summary_mappers.py` establishes."""

from app.modules.community_moderation.application.dto import (
    ModerationActionSummaryDTO,
    ReportSummaryDTO,
    RestrictionSummaryDTO,
    VerificationSummaryDTO,
)
from app.modules.community_moderation.domain.entities import (
    CommunityReport,
    DoctorVerification,
    ModerationAction,
    ModerationRestriction,
)


def report_to_summary(report: CommunityReport) -> ReportSummaryDTO:
    return ReportSummaryDTO(
        report_id=report.id,
        organization_id=report.organization_id,
        community_id=report.community_id,
        reporter_id=report.reporter_id,
        target_type=report.target_type,
        target_id=report.target_id,
        reason=report.reason,
        status=report.status,
        priority=report.priority,
        created_at=report.created_at,
        updated_at=report.updated_at,
        description=report.description,
        assigned_moderator_id=report.assigned_moderator_id,
        moderator_note=report.moderator_note,
        resolution=report.resolution,
        resolved_at=report.resolved_at,
    )


def action_to_summary(action: ModerationAction) -> ModerationActionSummaryDTO:
    return ModerationActionSummaryDTO(
        action_id=action.id,
        organization_id=action.organization_id,
        actor_id=action.actor_id,
        action_type=action.action_type,
        target_type=action.target_type,
        target_id=action.target_id,
        reason=action.reason,
        created_at=action.created_at,
        report_id=action.report_id,
        moderator_note=action.moderator_note,
        previous_state=action.previous_state,
        new_state=action.new_state,
    )


def restriction_to_summary(restriction: ModerationRestriction) -> RestrictionSummaryDTO:
    return RestrictionSummaryDTO(
        restriction_id=restriction.id,
        organization_id=restriction.organization_id,
        community_id=restriction.community_id,
        user_id=restriction.user_id,
        issued_by=restriction.issued_by,
        restriction_type=restriction.restriction_type,
        reason=restriction.reason,
        starts_at=restriction.starts_at,
        created_at=restriction.created_at,
        ends_at=restriction.ends_at,
        report_id=restriction.report_id,
    )


def verification_to_summary(verification: DoctorVerification) -> VerificationSummaryDTO:
    return VerificationSummaryDTO(
        verification_id=verification.id,
        doctor_id=verification.doctor_id,
        user_id=verification.user_id,
        organization_id=verification.organization_id,
        status=verification.status,
        created_at=verification.created_at,
        updated_at=verification.updated_at,
        specialty=verification.specialty,
        verifier_id=verification.verifier_id,
        verified_at=verification.verified_at,
        rejection_reason=verification.rejection_reason,
        revocation_reason=verification.revocation_reason,
        metadata=verification.metadata,
    )
