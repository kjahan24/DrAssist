"""`GetModerationStatusService`/`GetVerificationStatusService` — read-only
status queries, combined in one file for the same reason
`report_query_service.py`'s own docstring gives."""

from uuid import UUID

from app.modules.community_moderation.application.dto import (
    GetModerationStatusInput,
    VerificationSummaryDTO,
)
from app.modules.community_moderation.application.services._summary_mappers import (
    verification_to_summary,
)
from app.modules.community_moderation.domain.enums import ModerationRestrictionType
from app.modules.community_moderation.domain.repositories import (
    DoctorVerificationRepository,
    ModerationRestrictionRepository,
)
from app.modules.community_moderation.domain.value_objects import UserModerationStatus

_SEVERITY_RANK: dict[ModerationRestrictionType, int] = {
    ModerationRestrictionType.WARNING: 0,
    ModerationRestrictionType.TEMPORARY_RESTRICTION: 1,
    ModerationRestrictionType.SUSPENSION: 2,
    ModerationRestrictionType.PERMANENT_BAN: 3,
}


class GetModerationStatusService:
    def __init__(self, *, restriction_repository: ModerationRestrictionRepository) -> None:
        self._restrictions = restriction_repository

    async def get_status(self, input_dto: GetModerationStatusInput) -> UserModerationStatus:
        active = await self._restrictions.list_active_for_user(
            input_dto.user_id, community_id=input_dto.community_id
        )
        if not active:
            return UserModerationStatus(
                user_id=input_dto.user_id,
                community_id=input_dto.community_id,
                current_restriction_type=None,
                restricted_until=None,
                active_restriction_count=0,
            )

        most_severe = max(active, key=lambda r: _SEVERITY_RANK[r.restriction_type])
        return UserModerationStatus(
            user_id=input_dto.user_id,
            community_id=input_dto.community_id,
            current_restriction_type=most_severe.restriction_type,
            restricted_until=most_severe.ends_at,
            active_restriction_count=len(active),
        )


class GetVerificationStatusService:
    def __init__(self, *, verification_repository: DoctorVerificationRepository) -> None:
        self._verifications = verification_repository

    async def get_status(self, doctor_id: UUID) -> VerificationSummaryDTO | None:
        verification = await self._verifications.get_by_doctor_id(doctor_id)
        return verification_to_summary(verification) if verification is not None else None
