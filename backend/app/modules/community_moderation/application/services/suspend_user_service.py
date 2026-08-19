"""`SuspendUserService` — issues a `ModerationRestrictionType.SUSPENSION`
(`duration_days` given, `ends_at = now + duration_days`) or a
`PERMANENT_BAN` (`duration_days is None`, `ends_at = None`) — "Permanent
ban where authorized" (this task's own FEATURES wording): a time-bounded
suspension only requires `MODERATOR`-or-above rank (`ensure_is_moderator`,
same bar as `WarnUserService`/`RestrictUserService`), but a permanent ban
requires the strictly higher `ADMIN`-or-above rank
(`ensure_is_admin`) — the "where authorized" qualifier, enforced via
`_user_restrictions.resolve_and_authorize_user_restriction`'s own
`require_admin` flag rather than a separate, unlisted `BanUser` service.
"""

from datetime import UTC, datetime, timedelta

from app.modules.authentication.public.interfaces import UserQueryPort
from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_moderation.application.dto import (
    RestrictionSummaryDTO,
    SuspendUserInput,
)
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


class SuspendUserService:
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

    async def execute(self, input_dto: SuspendUserInput) -> RestrictionSummaryDTO:
        is_permanent = input_dto.duration_days is None
        await resolve_and_authorize_user_restriction(
            organization_id=input_dto.organization_id,
            community_id=input_dto.community_id,
            moderator_id=input_dto.moderator_id,
            user_id=input_dto.user_id,
            community_query_port=self._communities,
            user_query_port=self._users,
            require_admin=is_permanent,
        )

        restriction_type = (
            ModerationRestrictionType.PERMANENT_BAN
            if is_permanent
            else ModerationRestrictionType.SUSPENSION
        )
        ends_at = (
            None
            if input_dto.duration_days is None
            else datetime.now(UTC) + timedelta(days=input_dto.duration_days)
        )

        restriction = ModerationRestriction.issue(
            organization_id=input_dto.organization_id,
            community_id=input_dto.community_id,
            user_id=input_dto.user_id,
            issued_by=input_dto.moderator_id,
            restriction_type=restriction_type,
            reason=input_dto.reason,
            ends_at=ends_at,
            report_id=input_dto.report_id,
        )
        await self._restrictions.add(restriction)
        self._uow.collect_events(restriction.pull_events())

        action_type = (
            ModerationActionType.BAN_USER if is_permanent else ModerationActionType.SUSPEND_USER
        )
        action = ModerationAction.record(
            organization_id=input_dto.organization_id,
            actor_id=input_dto.moderator_id,
            action_type=action_type,
            target_type=ModerationTargetType.USER,
            target_id=input_dto.user_id,
            reason=input_dto.reason,
            report_id=input_dto.report_id,
            new_state=restriction_type.value,
        )
        await self._actions.add(action)

        await self._uow.commit()
        return restriction_to_summary(restriction)
