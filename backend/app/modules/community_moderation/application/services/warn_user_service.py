"""`WarnUserService` — issues a `ModerationRestrictionType.WARNING`, the
lightest-weight restriction (no `ends_at`, purely a recorded fact — a
warning never itself gates any behavior the way a suspension/ban would)."""

from app.modules.authentication.public.interfaces import UserQueryPort
from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_moderation.application.dto import RestrictionSummaryDTO, WarnUserInput
from app.modules.community_moderation.application.services._summary_mappers import (
    restriction_to_summary,
)
from app.modules.community_moderation.application.services._user_restrictions import (
    resolve_and_authorize_user_restriction,
)
from app.modules.community_moderation.domain.entities import ModerationAction, ModerationRestriction
from app.modules.community_moderation.domain.enums import (
    ModerationActionType,
    ModerationRestrictionType,
    ModerationTargetType,
)
from app.modules.community_moderation.domain.repositories import (
    ModerationActionRepository,
    ModerationRestrictionRepository,
)
from app.shared.application.unit_of_work import UnitOfWork


class WarnUserService:
    def __init__(
        self,
        *,
        restriction_repository: ModerationRestrictionRepository,
        action_repository: ModerationActionRepository,
        community_query_port: CommunityQueryPort,
        user_query_port: UserQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._restrictions = restriction_repository
        self._actions = action_repository
        self._communities = community_query_port
        self._users = user_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: WarnUserInput) -> RestrictionSummaryDTO:
        await resolve_and_authorize_user_restriction(
            organization_id=input_dto.organization_id,
            community_id=input_dto.community_id,
            moderator_id=input_dto.moderator_id,
            user_id=input_dto.user_id,
            community_query_port=self._communities,
            user_query_port=self._users,
        )

        restriction = ModerationRestriction.issue(
            organization_id=input_dto.organization_id,
            community_id=input_dto.community_id,
            user_id=input_dto.user_id,
            issued_by=input_dto.moderator_id,
            restriction_type=ModerationRestrictionType.WARNING,
            reason=input_dto.reason,
            report_id=input_dto.report_id,
        )
        await self._restrictions.add(restriction)
        self._uow.collect_events(restriction.pull_events())

        action = ModerationAction.record(
            organization_id=input_dto.organization_id,
            actor_id=input_dto.moderator_id,
            action_type=ModerationActionType.WARN_USER,
            target_type=ModerationTargetType.USER,
            target_id=input_dto.user_id,
            reason=input_dto.reason,
            report_id=input_dto.report_id,
            new_state=ModerationRestrictionType.WARNING.value,
        )
        await self._actions.add(action)

        await self._uow.commit()
        return restriction_to_summary(restriction)
