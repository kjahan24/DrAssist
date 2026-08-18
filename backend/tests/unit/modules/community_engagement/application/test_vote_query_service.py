"""Unit tests for `GetVoteStatusService`/`GetVoteCountsService`."""

from uuid import uuid4

from app.modules.community_engagement.application.services.vote_query_service import (
    GetVoteCountsService,
    GetVoteStatusService,
)
from app.modules.community_engagement.domain.entities import Vote
from app.modules.community_engagement.domain.enums import EngagementTargetType, VoteType
from tests.unit.modules.community_engagement.application.fakes import FakeVoteRepository


class TestGetVoteStatus:
    async def test_returns_none_when_the_user_has_not_voted(self) -> None:
        votes = FakeVoteRepository()
        service = GetVoteStatusService(vote_repository=votes)

        result = await service.get_status(EngagementTargetType.POST, uuid4(), user_id=uuid4())
        assert result.vote_type is None

    async def test_returns_the_users_own_vote_type(self) -> None:
        votes = FakeVoteRepository()
        service = GetVoteStatusService(vote_repository=votes)
        user_id, target_id = uuid4(), uuid4()
        await votes.add(
            Vote.create(
                user_id=user_id,
                organization_id=uuid4(),
                target_type=EngagementTargetType.ANSWER,
                target_id=target_id,
                vote_type=VoteType.DOWNVOTE,
            )
        )

        result = await service.get_status(EngagementTargetType.ANSWER, target_id, user_id=user_id)
        assert result.vote_type is VoteType.DOWNVOTE

    async def test_only_returns_the_requesting_users_own_vote(self) -> None:
        votes = FakeVoteRepository()
        service = GetVoteStatusService(vote_repository=votes)
        target_id = uuid4()
        await votes.add(
            Vote.create(
                user_id=uuid4(),
                organization_id=uuid4(),
                target_type=EngagementTargetType.POST,
                target_id=target_id,
                vote_type=VoteType.UPVOTE,
            )
        )

        result = await service.get_status(EngagementTargetType.POST, target_id, user_id=uuid4())
        assert result.vote_type is None

    async def test_result_echoes_the_requested_target(self) -> None:
        votes = FakeVoteRepository()
        service = GetVoteStatusService(vote_repository=votes)
        target_id = uuid4()

        result = await service.get_status(EngagementTargetType.COMMENT, target_id, user_id=uuid4())
        assert result.target_type is EngagementTargetType.COMMENT
        assert result.target_id == target_id


class TestGetVoteCounts:
    async def test_zero_counts_for_a_target_with_no_votes(self) -> None:
        votes = FakeVoteRepository()
        service = GetVoteCountsService(vote_repository=votes)

        result = await service.get_counts(EngagementTargetType.POST, uuid4())
        assert result.upvotes == 0
        assert result.downvotes == 0
        assert result.net_score == 0

    async def test_counts_upvotes_and_downvotes_separately(self) -> None:
        votes = FakeVoteRepository()
        service = GetVoteCountsService(vote_repository=votes)
        target_id = uuid4()
        await votes.add(
            Vote.create(
                user_id=uuid4(),
                organization_id=uuid4(),
                target_type=EngagementTargetType.QUESTION,
                target_id=target_id,
                vote_type=VoteType.UPVOTE,
            )
        )
        await votes.add(
            Vote.create(
                user_id=uuid4(),
                organization_id=uuid4(),
                target_type=EngagementTargetType.QUESTION,
                target_id=target_id,
                vote_type=VoteType.UPVOTE,
            )
        )
        await votes.add(
            Vote.create(
                user_id=uuid4(),
                organization_id=uuid4(),
                target_type=EngagementTargetType.QUESTION,
                target_id=target_id,
                vote_type=VoteType.DOWNVOTE,
            )
        )

        result = await service.get_counts(EngagementTargetType.QUESTION, target_id)
        assert result.upvotes == 2
        assert result.downvotes == 1

    async def test_net_score_is_upvotes_minus_downvotes(self) -> None:
        votes = FakeVoteRepository()
        service = GetVoteCountsService(vote_repository=votes)
        target_id = uuid4()
        for _ in range(3):
            await votes.add(
                Vote.create(
                    user_id=uuid4(),
                    organization_id=uuid4(),
                    target_type=EngagementTargetType.ANSWER,
                    target_id=target_id,
                    vote_type=VoteType.UPVOTE,
                )
            )
        await votes.add(
            Vote.create(
                user_id=uuid4(),
                organization_id=uuid4(),
                target_type=EngagementTargetType.ANSWER,
                target_id=target_id,
                vote_type=VoteType.DOWNVOTE,
            )
        )

        result = await service.get_counts(EngagementTargetType.ANSWER, target_id)
        assert result.net_score == 2

    async def test_does_not_count_votes_for_other_targets(self) -> None:
        votes = FakeVoteRepository()
        service = GetVoteCountsService(vote_repository=votes)
        target_id, other_target_id = uuid4(), uuid4()
        await votes.add(
            Vote.create(
                user_id=uuid4(),
                organization_id=uuid4(),
                target_type=EngagementTargetType.POST,
                target_id=other_target_id,
                vote_type=VoteType.UPVOTE,
            )
        )

        result = await service.get_counts(EngagementTargetType.POST, target_id)
        assert result.upvotes == 0
