"""Unit tests for `RemoveVoteService` — unconditionally idempotent."""

from uuid import uuid4

from app.modules.community_engagement.application.dto import RemoveVoteInput
from app.modules.community_engagement.application.services.remove_vote_service import (
    RemoveVoteService,
)
from app.modules.community_engagement.domain.entities import Vote
from app.modules.community_engagement.domain.enums import EngagementTargetType, VoteType
from app.modules.community_engagement.domain.events import VoteRemoved
from tests.unit.modules.community_engagement.application.fakes import (
    FakeUnitOfWork,
    FakeVoteRepository,
)


def _seeded() -> tuple[RemoveVoteService, FakeVoteRepository, FakeUnitOfWork]:
    votes = FakeVoteRepository()
    uow = FakeUnitOfWork()
    service = RemoveVoteService(vote_repository=votes, unit_of_work=uow)
    return service, votes, uow


class TestRemoveVote:
    async def test_removes_an_existing_vote(self) -> None:
        service, votes, _ = _seeded()
        user_id, target_id = uuid4(), uuid4()
        vote = Vote.create(
            user_id=user_id,
            organization_id=uuid4(),
            target_type=EngagementTargetType.POST,
            target_id=target_id,
            vote_type=VoteType.UPVOTE,
        )
        await votes.add(vote)

        await service.execute(
            RemoveVoteInput(
                target_type=EngagementTargetType.POST, target_id=target_id, user_id=user_id
            )
        )
        assert await votes.get_vote(user_id, EngagementTargetType.POST, target_id) is None

    async def test_removing_a_nonexistent_vote_is_a_silent_no_op(self) -> None:
        service, _, uow = _seeded()
        await service.execute(
            RemoveVoteInput(
                target_type=EngagementTargetType.POST, target_id=uuid4(), user_id=uuid4()
            )
        )
        assert uow.committed is False

    async def test_commits_the_unit_of_work_when_a_vote_is_removed(self) -> None:
        service, votes, uow = _seeded()
        user_id, target_id = uuid4(), uuid4()
        vote = Vote.create(
            user_id=user_id,
            organization_id=uuid4(),
            target_type=EngagementTargetType.ANSWER,
            target_id=target_id,
            vote_type=VoteType.DOWNVOTE,
        )
        await votes.add(vote)

        await service.execute(
            RemoveVoteInput(
                target_type=EngagementTargetType.ANSWER, target_id=target_id, user_id=user_id
            )
        )
        assert uow.committed is True

    async def test_publishes_a_vote_removed_event(self) -> None:
        service, votes, uow = _seeded()
        user_id, target_id = uuid4(), uuid4()
        vote = Vote.create(
            user_id=user_id,
            organization_id=uuid4(),
            target_type=EngagementTargetType.COMMENT,
            target_id=target_id,
            vote_type=VoteType.UPVOTE,
        )
        await votes.add(vote)

        await service.execute(
            RemoveVoteInput(
                target_type=EngagementTargetType.COMMENT, target_id=target_id, user_id=user_id
            )
        )
        assert any(isinstance(e, VoteRemoved) for e in uow.published_events)

    async def test_calling_remove_twice_is_idempotent(self) -> None:
        service, votes, _ = _seeded()
        user_id, target_id = uuid4(), uuid4()
        vote = Vote.create(
            user_id=user_id,
            organization_id=uuid4(),
            target_type=EngagementTargetType.QUESTION,
            target_id=target_id,
            vote_type=VoteType.UPVOTE,
        )
        await votes.add(vote)

        input_dto = RemoveVoteInput(
            target_type=EngagementTargetType.QUESTION, target_id=target_id, user_id=user_id
        )
        await service.execute(input_dto)
        await service.execute(input_dto)
        assert await votes.get_vote(user_id, EngagementTargetType.QUESTION, target_id) is None
