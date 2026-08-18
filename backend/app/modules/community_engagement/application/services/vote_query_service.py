"""`GetVoteStatusService`/`GetVoteCountsService` — read-only query
services, the same shape `app.modules.community_answers.application
.services.answer_query_service` establishes for its own analogous
`GetAnswerService`/`ListAnswersService` pairing.

Neither service exposes *who* voted, only the acting user's own status
(`GetVoteStatusService`) or an aggregate count (`GetVoteCountsService`)
— there is no "list voters" read path anywhere in this module, which is
exactly what keeps voting private: this task's own "Anonymous/public
content must not expose private identity" DOMAIN rule, applied to the
voter's own identity rather than the target's (see this module's own
`presentation` docstring for the full reasoning — `ListFollowers`/
`ListFollowing`, by contrast, *do* expose `user_id`, since following is
a public-facing social action on this platform, unlike voting).

`GetVoteCountsService.get_counts` never requires an acting user — vote
counts are public information about the target, computed live from
`VoteRepository.count_votes`, never from a stored counter — see that
repository method's own docstring.
"""

from uuid import UUID

from app.modules.community_engagement.application.dto import VoteCountsDTO, VoteStatusDTO
from app.modules.community_engagement.domain.enums import EngagementTargetType, VoteType
from app.modules.community_engagement.domain.repositories import VoteRepository


class GetVoteStatusService:
    def __init__(self, *, vote_repository: VoteRepository) -> None:
        self._votes = vote_repository

    async def get_status(
        self, target_type: EngagementTargetType, target_id: UUID, *, user_id: UUID
    ) -> VoteStatusDTO:
        vote = await self._votes.get_vote(user_id, target_type, target_id)
        return VoteStatusDTO(
            target_type=target_type,
            target_id=target_id,
            vote_type=vote.vote_type if vote is not None else None,
        )


class GetVoteCountsService:
    def __init__(self, *, vote_repository: VoteRepository) -> None:
        self._votes = vote_repository

    async def get_counts(self, target_type: EngagementTargetType, target_id: UUID) -> VoteCountsDTO:
        counts = await self._votes.count_votes(target_type, target_id)
        return VoteCountsDTO(
            target_type=target_type,
            target_id=target_id,
            upvotes=counts[VoteType.UPVOTE],
            downvotes=counts[VoteType.DOWNVOTE],
        )
