"""`EngagementFacade` — the one concrete implementation of
`EngagementQueryPort`. Constructed per-request by
`app.modules.community_engagement.container.build_engagement_facade`,
bound to that request's `AsyncSession`.

Built directly against `VoteRepository`, reusing the exact same
`count_votes` computation `vote_query_service.GetVoteCountsService`
itself uses — vote counts are public information with no viewer-context
gating, so there is no analogous "bypass visibility rules" concern the
way `app.modules.community_answers.public.facade.AnswerFacade`'s own
docstring describes for content visibility.
"""

from uuid import UUID

from app.modules.community_engagement.domain.enums import EngagementTargetType, VoteType
from app.modules.community_engagement.domain.repositories import VoteRepository
from app.modules.community_engagement.public.dto import VoteCountsDTO
from app.modules.community_engagement.public.interfaces import EngagementQueryPort


class EngagementFacade(EngagementQueryPort):
    def __init__(self, *, vote_repository: VoteRepository) -> None:
        self._votes = vote_repository

    async def get_vote_counts(
        self, target_type: EngagementTargetType, target_id: UUID
    ) -> VoteCountsDTO:
        counts = await self._votes.count_votes(target_type, target_id)
        return VoteCountsDTO(
            target_type=target_type,
            target_id=target_id,
            upvotes=counts[VoteType.UPVOTE],
            downvotes=counts[VoteType.DOWNVOTE],
        )
