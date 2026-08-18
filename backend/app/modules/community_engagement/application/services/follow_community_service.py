"""`FollowCommunityService` — "Follow/Unfollow Community" (this task's
own FEATURES list), a deliberately distinct, lighter-weight relationship
from `app.modules.community`'s own membership (`CommunityMember`/
`join`/`leave`, Phase 5.1/5.2 — completed, not touched here): following a
community requires no role and does not grant posting rights, and — like
a real "follow to preview before joining" flow — is *not* gated behind
already being a member. Existence + tenant match against the target
community are both required (`CommunityNotFoundForFollowError` for
either, collapsed into the one exception — see `_target_resolution.py`'s
own docstring for why cross-tenant existence is never distinguishable
from "not found").

Idempotent: following a community you already follow is a silent no-op.
"""

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_engagement.application.dto import (
    FollowCommunityInput,
    FollowerSummaryDTO,
)
from app.modules.community_engagement.application.services._summary_mappers import (
    community_follower_to_summary,
)
from app.modules.community_engagement.domain.entities import CommunityFollower
from app.modules.community_engagement.domain.exceptions import CommunityNotFoundForFollowError
from app.modules.community_engagement.domain.repositories import CommunityFollowerRepository
from app.shared.application.unit_of_work import UnitOfWork


class FollowCommunityService:
    def __init__(
        self,
        *,
        community_follower_repository: CommunityFollowerRepository,
        community_query_port: CommunityQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._followers = community_follower_repository
        self._communities = community_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: FollowCommunityInput) -> FollowerSummaryDTO:
        community = await self._communities.get_community_summary(input_dto.community_id)
        if community is None or community.organization_id != input_dto.organization_id:
            raise CommunityNotFoundForFollowError(input_dto.community_id)

        existing = await self._followers.get_follow(input_dto.user_id, input_dto.community_id)
        if existing is not None:
            return community_follower_to_summary(existing)

        follower = CommunityFollower.create(
            user_id=input_dto.user_id,
            organization_id=input_dto.organization_id,
            community_id=input_dto.community_id,
        )
        await self._followers.add(follower)
        self._uow.collect_events(follower.pull_events())
        await self._uow.commit()
        return community_follower_to_summary(follower)
