"""`ModerationFacade` — the one concrete implementation of
`ModerationQueryPort`. Constructed per-request by
`app.modules.community_moderation.container.build_moderation_facade`,
bound to that request's `AsyncSession`. Built directly against the three
repositories it needs, reusing the exact same status-computation logic
`GetModerationStatusService`/`get_current_content_status` (application
layer) already implement — no separate visibility-gating concern the way
`app.modules.community_answers.public.facade.AnswerFacade`'s own
docstring describes, since moderation status is not viewer-dependent.
"""

from uuid import UUID

from app.modules.community_moderation.application.services._content_actions import (
    get_current_content_status,
)
from app.modules.community_moderation.application.services._summary_mappers import (
    verification_to_summary,
)
from app.modules.community_moderation.domain.enums import ModerationTargetType
from app.modules.community_moderation.domain.repositories import (
    DoctorVerificationRepository,
    ModerationActionRepository,
    ModerationRestrictionRepository,
)
from app.modules.community_moderation.domain.value_objects import UserModerationStatus
from app.modules.community_moderation.public.dto import VerificationSummaryDTO
from app.modules.community_moderation.public.interfaces import ModerationQueryPort

_SEVERITY_RANK = {
    "warning": 0,
    "temporary_restriction": 1,
    "suspension": 2,
    "permanent_ban": 3,
}


class ModerationFacade(ModerationQueryPort):
    def __init__(
        self,
        *,
        action_repository: ModerationActionRepository,
        restriction_repository: ModerationRestrictionRepository,
        verification_repository: DoctorVerificationRepository,
    ) -> None:
        self._actions = action_repository
        self._restrictions = restriction_repository
        self._verifications = verification_repository

    async def get_content_moderation_status(
        self, target_type: ModerationTargetType, target_id: UUID
    ) -> str:
        status = await get_current_content_status(self._actions, target_type, target_id)
        return status.value

    async def get_user_moderation_status(
        self, user_id: UUID, *, community_id: UUID | None = None
    ) -> UserModerationStatus:
        active = await self._restrictions.list_active_for_user(user_id, community_id=community_id)
        if not active:
            return UserModerationStatus(
                user_id=user_id,
                community_id=community_id,
                current_restriction_type=None,
                restricted_until=None,
                active_restriction_count=0,
            )
        most_severe = max(active, key=lambda r: _SEVERITY_RANK[r.restriction_type.value])
        return UserModerationStatus(
            user_id=user_id,
            community_id=community_id,
            current_restriction_type=most_severe.restriction_type,
            restricted_until=most_severe.ends_at,
            active_restriction_count=len(active),
        )

    async def get_verification_status(self, doctor_id: UUID) -> VerificationSummaryDTO | None:
        verification = await self._verifications.get_by_doctor_id(doctor_id)
        return verification_to_summary(verification) if verification is not None else None
