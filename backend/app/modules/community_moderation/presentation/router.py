"""HTTP routes for the Community Moderation module.

Follows the pattern established in
`app.modules.community_engagement.presentation.router`. Every endpoint
depends on `CurrentUser`. Doctor-verification review endpoints
(`approve`/`reject`/`revoke`) additionally require the
`moderation.verify_doctor` organization-level permission via
`Depends(require_permission(...))` — the same org-admin-permission-code
gate `app.modules.community.presentation.router` already uses for
`communities.verify`/`communities.feature` — since granting a platform-
wide trust badge has no natural single-community scope, unlike every
other endpoint here (all authorized via `CommunityRole` rank, enforced
inside the service layer itself against `CurrentUser.organization_id`/
`community_id`).

There is no `ensure_same_organization` call anywhere in this router,
matching `community_engagement`'s own precedent: every service already
enforces tenant isolation itself via the explicit `organization_id`
comparison pattern threaded through every Input DTO.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, require_permission
from app.modules.authentication.public.dto import AuthenticatedPrincipalDTO
from app.modules.community_moderation.application.dto import (
    ApproveDoctorVerificationInput,
    AssignReportInput,
    ContentModerationInput,
    CreateModerationActionInput,
    CreateReportInput,
    GetModerationStatusInput,
    ListReportsInput,
    RejectDoctorVerificationInput,
    RejectReportInput,
    RequestDoctorVerificationInput,
    ResolveReportInput,
    RestrictUserInput,
    RevokeDoctorVerificationInput,
    SuspendUserInput,
    WarnUserInput,
)
from app.modules.community_moderation.domain.enums import (
    ReportPriority,
    ReportStatus,
)
from app.modules.community_moderation.presentation.dependencies import (
    ApproveDoctorVerificationUseCase,
    AssignReportUseCase,
    CreateModerationActionUseCase,
    CreateReportUseCase,
    GetModerationStatusQS,
    GetReportQS,
    GetVerificationStatusQS,
    ListReportsQS,
    LockContentUseCase,
    RejectDoctorVerificationUseCase,
    RejectReportUseCase,
    RemoveContentUseCase,
    RequestDoctorVerificationUseCase,
    ResolveReportUseCase,
    RestoreContentUseCase,
    RestrictUserUseCase,
    ReviewContentUseCase,
    RevokeDoctorVerificationUseCase,
    SuspendUserUseCase,
    WarnUserUseCase,
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

router = APIRouter()


@router.get("/health")
async def get_community_moderation_health() -> dict[str, str]:
    return {"status": "ok", "module": "community_moderation"}


# --- Reports ---------------------------------------------------------------------------


@router.post("/reports", response_model=ReportResponse)
async def create_report(
    body: CreateReportRequest, use_case: CreateReportUseCase, current_user: CurrentUser
) -> ReportResponse:
    output = await use_case.execute(
        CreateReportInput(
            organization_id=current_user.organization_id,
            community_id=body.community_id,
            reporter_id=current_user.user_id,
            target_type=body.target_type,
            target_id=body.target_id,
            reason=body.reason,
            description=body.description,
        )
    )
    return ReportResponse.model_validate(output)


@router.get("/reports", response_model=ReportFeedResponse)
async def list_reports(
    query_service: ListReportsQS,
    current_user: CurrentUser,
    community_id: UUID | None = None,
    status_: ReportStatus | None = Query(default=None, alias="status"),
    priority: ReportPriority | None = None,
    assigned_moderator_id: UUID | None = None,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> ReportFeedResponse:
    result = await query_service.list_reports(
        ListReportsInput(
            organization_id=current_user.organization_id,
            community_id=community_id,
            status=status_,
            priority=priority,
            assigned_moderator_id=assigned_moderator_id,
            cursor=cursor,
            limit=limit,
        )
    )
    return ReportFeedResponse(
        items=[ReportResponse.model_validate(r) for r in result.items],
        next_cursor=result.next_cursor,
    )


@router.get("/reports/{report_id}", response_model=ReportResponse)
async def get_report(report_id: UUID, query_service: GetReportQS) -> ReportResponse:
    result = await query_service.get_report(report_id)
    return ReportResponse.model_validate(result)


@router.post("/reports/{report_id}/assign", response_model=ReportResponse)
async def assign_report(
    report_id: UUID,
    body: AssignReportRequest,
    use_case: AssignReportUseCase,
    current_user: CurrentUser,
) -> ReportResponse:
    output = await use_case.execute(
        AssignReportInput(
            report_id=report_id,
            moderator_id=current_user.user_id,
            community_id=body.community_id,
            note=body.note,
        )
    )
    return ReportResponse.model_validate(output)


@router.post("/reports/{report_id}/resolve", response_model=ReportResponse)
async def resolve_report(
    report_id: UUID,
    body: ResolveReportRequest,
    use_case: ResolveReportUseCase,
    current_user: CurrentUser,
) -> ReportResponse:
    output = await use_case.execute(
        ResolveReportInput(
            report_id=report_id,
            moderator_id=current_user.user_id,
            community_id=body.community_id,
            resolution=body.resolution,
            note=body.note,
        )
    )
    return ReportResponse.model_validate(output)


@router.post("/reports/{report_id}/reject", response_model=ReportResponse)
async def reject_report(
    report_id: UUID,
    body: RejectReportRequest,
    use_case: RejectReportUseCase,
    current_user: CurrentUser,
) -> ReportResponse:
    output = await use_case.execute(
        RejectReportInput(
            report_id=report_id,
            moderator_id=current_user.user_id,
            community_id=body.community_id,
            resolution=body.resolution,
            note=body.note,
        )
    )
    return ReportResponse.model_validate(output)


# --- Moderation actions ------------------------------------------------------------------


@router.post("/moderation-actions", response_model=ModerationActionResponse)
async def create_moderation_action(
    body: CreateModerationActionRequest,
    use_case: CreateModerationActionUseCase,
    current_user: CurrentUser,
) -> ModerationActionResponse:
    output = await use_case.execute(
        CreateModerationActionInput(
            organization_id=current_user.organization_id,
            actor_id=current_user.user_id,
            action_type=body.action_type,
            target_type=body.target_type,
            target_id=body.target_id,
            reason=body.reason,
            report_id=body.report_id,
            moderator_note=body.moderator_note,
        )
    )
    return ModerationActionResponse.model_validate(output)


@router.post("/content/review", response_model=ModerationActionResponse)
async def review_content(
    body: ContentModerationRequest, use_case: ReviewContentUseCase, current_user: CurrentUser
) -> ModerationActionResponse:
    output = await use_case.execute(
        ContentModerationInput(
            organization_id=current_user.organization_id,
            actor_id=current_user.user_id,
            target_type=body.target_type,
            target_id=body.target_id,
            reason=body.reason,
            report_id=body.report_id,
            moderator_note=body.moderator_note,
        )
    )
    return ModerationActionResponse.model_validate(output)


@router.post("/content/remove", response_model=ModerationActionResponse)
async def remove_content(
    body: ContentModerationRequest, use_case: RemoveContentUseCase, current_user: CurrentUser
) -> ModerationActionResponse:
    output = await use_case.execute(
        ContentModerationInput(
            organization_id=current_user.organization_id,
            actor_id=current_user.user_id,
            target_type=body.target_type,
            target_id=body.target_id,
            reason=body.reason,
            report_id=body.report_id,
            moderator_note=body.moderator_note,
        )
    )
    return ModerationActionResponse.model_validate(output)


@router.post("/content/restore", response_model=ModerationActionResponse)
async def restore_content(
    body: ContentModerationRequest, use_case: RestoreContentUseCase, current_user: CurrentUser
) -> ModerationActionResponse:
    output = await use_case.execute(
        ContentModerationInput(
            organization_id=current_user.organization_id,
            actor_id=current_user.user_id,
            target_type=body.target_type,
            target_id=body.target_id,
            reason=body.reason,
            report_id=body.report_id,
            moderator_note=body.moderator_note,
        )
    )
    return ModerationActionResponse.model_validate(output)


@router.post("/content/lock", response_model=ModerationActionResponse)
async def lock_content(
    body: ContentModerationRequest, use_case: LockContentUseCase, current_user: CurrentUser
) -> ModerationActionResponse:
    output = await use_case.execute(
        ContentModerationInput(
            organization_id=current_user.organization_id,
            actor_id=current_user.user_id,
            target_type=body.target_type,
            target_id=body.target_id,
            reason=body.reason,
            report_id=body.report_id,
            moderator_note=body.moderator_note,
        )
    )
    return ModerationActionResponse.model_validate(output)


# --- User restrictions -----------------------------------------------------------------


@router.post("/users/{user_id}/warn", response_model=RestrictionResponse)
async def warn_user(
    user_id: UUID, body: WarnUserRequest, use_case: WarnUserUseCase, current_user: CurrentUser
) -> RestrictionResponse:
    output = await use_case.execute(
        WarnUserInput(
            organization_id=current_user.organization_id,
            community_id=body.community_id,
            moderator_id=current_user.user_id,
            user_id=user_id,
            reason=body.reason,
            report_id=body.report_id,
        )
    )
    return RestrictionResponse.model_validate(output)


@router.post("/users/{user_id}/restrict", response_model=RestrictionResponse)
async def restrict_user(
    user_id: UUID,
    body: RestrictUserRequest,
    use_case: RestrictUserUseCase,
    current_user: CurrentUser,
) -> RestrictionResponse:
    output = await use_case.execute(
        RestrictUserInput(
            organization_id=current_user.organization_id,
            community_id=body.community_id,
            moderator_id=current_user.user_id,
            user_id=user_id,
            reason=body.reason,
            duration_days=body.duration_days,
            report_id=body.report_id,
        )
    )
    return RestrictionResponse.model_validate(output)


@router.post("/users/{user_id}/suspend", response_model=RestrictionResponse)
async def suspend_user(
    user_id: UUID,
    body: SuspendUserRequest,
    use_case: SuspendUserUseCase,
    current_user: CurrentUser,
) -> RestrictionResponse:
    output = await use_case.execute(
        SuspendUserInput(
            organization_id=current_user.organization_id,
            community_id=body.community_id,
            moderator_id=current_user.user_id,
            user_id=user_id,
            reason=body.reason,
            duration_days=body.duration_days,
            report_id=body.report_id,
        )
    )
    return RestrictionResponse.model_validate(output)


@router.get("/users/{user_id}/moderation-status", response_model=ModerationStatusResponse)
async def get_user_moderation_status(
    user_id: UUID, query_service: GetModerationStatusQS, community_id: UUID | None = None
) -> ModerationStatusResponse:
    result = await query_service.get_status(
        GetModerationStatusInput(user_id=user_id, community_id=community_id)
    )
    return ModerationStatusResponse(
        user_id=result.user_id,
        community_id=result.community_id,
        current_restriction_type=result.current_restriction_type,
        restricted_until=result.restricted_until,
        active_restriction_count=result.active_restriction_count,
        is_restricted=result.is_restricted,
    )


# --- Doctor verification -----------------------------------------------------------------


@router.post("/doctors/{doctor_id}/verification/request", response_model=VerificationResponse)
async def request_doctor_verification(
    doctor_id: UUID,
    body: RequestDoctorVerificationRequest,
    use_case: RequestDoctorVerificationUseCase,
    current_user: CurrentUser,
) -> VerificationResponse:
    output = await use_case.execute(
        RequestDoctorVerificationInput(
            doctor_id=doctor_id,
            requesting_user_id=current_user.user_id,
            specialty=body.specialty,
            metadata=body.metadata,
        )
    )
    return VerificationResponse.model_validate(output)


@router.get("/doctors/{doctor_id}/verification", response_model=VerificationResponse | None)
async def get_doctor_verification_status(
    doctor_id: UUID, query_service: GetVerificationStatusQS
) -> VerificationResponse | None:
    result = await query_service.get_status(doctor_id)
    return VerificationResponse.model_validate(result) if result is not None else None


VerifierUser = Annotated[
    AuthenticatedPrincipalDTO, Depends(require_permission("moderation.verify_doctor"))
]


@router.post("/verifications/{verification_id}/approve", response_model=VerificationResponse)
async def approve_doctor_verification(
    verification_id: UUID,
    body: ApproveDoctorVerificationRequest,
    use_case: ApproveDoctorVerificationUseCase,
    current_user: VerifierUser,
) -> VerificationResponse:
    output = await use_case.execute(
        ApproveDoctorVerificationInput(
            verification_id=verification_id,
            verifier_id=current_user.user_id,
            specialty=body.specialty,
        )
    )
    return VerificationResponse.model_validate(output)


@router.post("/verifications/{verification_id}/reject", response_model=VerificationResponse)
async def reject_doctor_verification(
    verification_id: UUID,
    body: RejectDoctorVerificationRequest,
    use_case: RejectDoctorVerificationUseCase,
    current_user: VerifierUser,
) -> VerificationResponse:
    output = await use_case.execute(
        RejectDoctorVerificationInput(
            verification_id=verification_id, verifier_id=current_user.user_id, reason=body.reason
        )
    )
    return VerificationResponse.model_validate(output)


@router.post("/verifications/{verification_id}/revoke", response_model=VerificationResponse)
async def revoke_doctor_verification(
    verification_id: UUID,
    body: RevokeDoctorVerificationRequest,
    use_case: RevokeDoctorVerificationUseCase,
    current_user: VerifierUser,
) -> VerificationResponse:
    output = await use_case.execute(
        RevokeDoctorVerificationInput(
            verification_id=verification_id, verifier_id=current_user.user_id, reason=body.reason
        )
    )
    return VerificationResponse.model_validate(output)
