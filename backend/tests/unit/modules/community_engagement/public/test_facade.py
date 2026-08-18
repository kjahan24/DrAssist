"""Unit tests for `EngagementFacade` — exercised through
`EngagementQueryPort` exactly as a future consumer module would call it,
per `docs/backend-architecture/12_testing_architecture.md`'s "Contract
tests" framing."""

from uuid import uuid4

from app.modules.community_engagement.domain.entities import Vote
from app.modules.community_engagement.domain.enums import EngagementTargetType, VoteType
from app.modules.community_engagement.public.facade import EngagementFacade
from app.modules.community_engagement.public.interfaces import EngagementQueryPort
from tests.unit.modules.community_engagement.application.fakes import FakeVoteRepository


def _facade() -> tuple[EngagementFacade, FakeVoteRepository]:
    votes = FakeVoteRepository()
    facade = EngagementFacade(vote_repository=votes)
    return facade, votes


class TestEngagementFacade:
    def test_is_an_engagement_query_port(self) -> None:
        facade, _ = _facade()
        assert isinstance(facade, EngagementQueryPort)

    async def test_get_vote_counts_returns_zero_when_no_votes(self) -> None:
        facade, _ = _facade()
        target_id = uuid4()

        counts = await facade.get_vote_counts(EngagementTargetType.POST, target_id)

        assert counts.upvotes == 0
        assert counts.downvotes == 0
        assert counts.net_score == 0

    async def test_get_vote_counts_reflects_stored_votes(self) -> None:
        facade, votes = _facade()
        org_id, target_id = uuid4(), uuid4()
        await votes.add(
            Vote.create(
                user_id=uuid4(),
                organization_id=org_id,
                target_type=EngagementTargetType.POST,
                target_id=target_id,
                vote_type=VoteType.UPVOTE,
            )
        )
        await votes.add(
            Vote.create(
                user_id=uuid4(),
                organization_id=org_id,
                target_type=EngagementTargetType.POST,
                target_id=target_id,
                vote_type=VoteType.UPVOTE,
            )
        )
        await votes.add(
            Vote.create(
                user_id=uuid4(),
                organization_id=org_id,
                target_type=EngagementTargetType.POST,
                target_id=target_id,
                vote_type=VoteType.DOWNVOTE,
            )
        )

        counts = await facade.get_vote_counts(EngagementTargetType.POST, target_id)

        assert counts.upvotes == 2
        assert counts.downvotes == 1
        assert counts.net_score == 1

    async def test_get_vote_counts_is_scoped_to_the_given_target(self) -> None:
        facade, votes = _facade()
        org_id = uuid4()
        target_id, other_target_id = uuid4(), uuid4()
        await votes.add(
            Vote.create(
                user_id=uuid4(),
                organization_id=org_id,
                target_type=EngagementTargetType.POST,
                target_id=target_id,
                vote_type=VoteType.UPVOTE,
            )
        )
        await votes.add(
            Vote.create(
                user_id=uuid4(),
                organization_id=org_id,
                target_type=EngagementTargetType.POST,
                target_id=other_target_id,
                vote_type=VoteType.UPVOTE,
            )
        )

        counts = await facade.get_vote_counts(EngagementTargetType.POST, target_id)
        assert counts.upvotes == 1

    async def test_get_vote_counts_is_scoped_to_the_given_target_type(self) -> None:
        facade, votes = _facade()
        org_id, target_id = uuid4(), uuid4()
        await votes.add(
            Vote.create(
                user_id=uuid4(),
                organization_id=org_id,
                target_type=EngagementTargetType.POST,
                target_id=target_id,
                vote_type=VoteType.UPVOTE,
            )
        )
        await votes.add(
            Vote.create(
                user_id=uuid4(),
                organization_id=org_id,
                target_type=EngagementTargetType.QUESTION,
                target_id=target_id,
                vote_type=VoteType.UPVOTE,
            )
        )

        counts = await facade.get_vote_counts(EngagementTargetType.QUESTION, target_id)
        assert counts.upvotes == 1
