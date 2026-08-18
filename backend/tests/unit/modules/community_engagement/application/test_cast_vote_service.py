"""Unit tests for `CastVoteService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community_engagement.application.dto import CastVoteInput
from app.modules.community_engagement.application.services.cast_vote_service import (
    CastVoteService,
)
from app.modules.community_engagement.domain.enums import EngagementTargetType, VoteType
from app.modules.community_engagement.domain.events import VoteCast, VoteSwitched
from app.modules.community_engagement.domain.exceptions import (
    VoteTargetNotAcceptingVotesError,
    VoteTargetNotFoundError,
)
from app.modules.community_posts.public.dto import PostStatus
from tests.unit.modules.community_engagement.application.fakes import (
    FakeAnswerQueryPort,
    FakeCommentQueryPort,
    FakePostQueryPort,
    FakeQuestionQueryPort,
    FakeUnitOfWork,
    FakeVoteRepository,
    make_post_summary,
)


def _seeded() -> (
    tuple[
        CastVoteService,
        FakeVoteRepository,
        FakePostQueryPort,
        FakeQuestionQueryPort,
        FakeAnswerQueryPort,
        FakeCommentQueryPort,
        FakeUnitOfWork,
    ]
):
    votes = FakeVoteRepository()
    posts = FakePostQueryPort()
    questions = FakeQuestionQueryPort()
    answers = FakeAnswerQueryPort()
    comments = FakeCommentQueryPort()
    uow = FakeUnitOfWork()
    service = CastVoteService(
        vote_repository=votes,
        post_query_port=posts,
        question_query_port=questions,
        answer_query_port=answers,
        comment_query_port=comments,
        unit_of_work=uow,
    )
    return service, votes, posts, questions, answers, comments, uow


class TestCastVoteOnNewTarget:
    async def test_creates_an_upvote(self) -> None:
        service, votes, posts, _, _, _, _ = _seeded()
        org_id, post_id, user_id = uuid4(), uuid4(), uuid4()
        posts.add_post(make_post_summary(post_id=post_id, organization_id=org_id))

        output = await service.execute(
            CastVoteInput(
                target_type=EngagementTargetType.POST,
                target_id=post_id,
                user_id=user_id,
                organization_id=org_id,
                vote_type=VoteType.UPVOTE,
            )
        )
        assert output.vote_type is VoteType.UPVOTE
        stored = await votes.get_vote(user_id, EngagementTargetType.POST, post_id)
        assert stored is not None
        assert stored.vote_type is VoteType.UPVOTE

    async def test_unknown_target_raises(self) -> None:
        service, _, _, _, _, _, _ = _seeded()
        with pytest.raises(VoteTargetNotFoundError):
            await service.execute(
                CastVoteInput(
                    target_type=EngagementTargetType.POST,
                    target_id=uuid4(),
                    user_id=uuid4(),
                    organization_id=uuid4(),
                    vote_type=VoteType.UPVOTE,
                )
            )

    async def test_cross_tenant_target_raises_not_found(self) -> None:
        service, _, posts, _, _, _, _ = _seeded()
        post_id = uuid4()
        posts.add_post(make_post_summary(post_id=post_id, organization_id=uuid4()))

        with pytest.raises(VoteTargetNotFoundError):
            await service.execute(
                CastVoteInput(
                    target_type=EngagementTargetType.POST,
                    target_id=post_id,
                    user_id=uuid4(),
                    organization_id=uuid4(),
                    vote_type=VoteType.UPVOTE,
                )
            )

    async def test_draft_target_rejects_voting(self) -> None:
        service, _, posts, _, _, _, _ = _seeded()
        org_id, post_id = uuid4(), uuid4()
        posts.add_post(
            make_post_summary(post_id=post_id, organization_id=org_id, status=PostStatus.DRAFT)
        )

        with pytest.raises(VoteTargetNotAcceptingVotesError):
            await service.execute(
                CastVoteInput(
                    target_type=EngagementTargetType.POST,
                    target_id=post_id,
                    user_id=uuid4(),
                    organization_id=org_id,
                    vote_type=VoteType.UPVOTE,
                )
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, _, posts, _, _, _, uow = _seeded()
        org_id, post_id = uuid4(), uuid4()
        posts.add_post(make_post_summary(post_id=post_id, organization_id=org_id))

        await service.execute(
            CastVoteInput(
                target_type=EngagementTargetType.POST,
                target_id=post_id,
                user_id=uuid4(),
                organization_id=org_id,
                vote_type=VoteType.UPVOTE,
            )
        )
        assert uow.committed is True

    async def test_publishes_a_vote_cast_event(self) -> None:
        service, _, posts, _, _, _, uow = _seeded()
        org_id, post_id = uuid4(), uuid4()
        posts.add_post(make_post_summary(post_id=post_id, organization_id=org_id))

        await service.execute(
            CastVoteInput(
                target_type=EngagementTargetType.POST,
                target_id=post_id,
                user_id=uuid4(),
                organization_id=org_id,
                vote_type=VoteType.UPVOTE,
            )
        )
        assert any(isinstance(e, VoteCast) for e in uow.published_events)


class TestCastVoteIdempotentSameDirection:
    async def test_recasting_the_same_direction_is_a_no_op(self) -> None:
        service, votes, posts, _, _, _, uow = _seeded()
        org_id, post_id, user_id = uuid4(), uuid4(), uuid4()
        posts.add_post(make_post_summary(post_id=post_id, organization_id=org_id))
        await service.execute(
            CastVoteInput(
                target_type=EngagementTargetType.POST,
                target_id=post_id,
                user_id=user_id,
                organization_id=org_id,
                vote_type=VoteType.UPVOTE,
            )
        )
        first_vote = await votes.get_vote(user_id, EngagementTargetType.POST, post_id)
        assert first_vote is not None

        uow.committed = False
        output = await service.execute(
            CastVoteInput(
                target_type=EngagementTargetType.POST,
                target_id=post_id,
                user_id=user_id,
                organization_id=org_id,
                vote_type=VoteType.UPVOTE,
            )
        )
        assert output.vote_id == first_vote.id
        assert uow.committed is False

    async def test_does_not_create_a_second_vote_row(self) -> None:
        service, votes, posts, _, _, _, _ = _seeded()
        org_id, post_id, user_id = uuid4(), uuid4(), uuid4()
        posts.add_post(make_post_summary(post_id=post_id, organization_id=org_id))
        for _ in range(2):
            await service.execute(
                CastVoteInput(
                    target_type=EngagementTargetType.POST,
                    target_id=post_id,
                    user_id=user_id,
                    organization_id=org_id,
                    vote_type=VoteType.UPVOTE,
                )
            )

        counts = await votes.count_votes(EngagementTargetType.POST, post_id)
        assert counts[VoteType.UPVOTE] == 1


class TestCastVoteSwitching:
    async def test_switches_upvote_to_downvote(self) -> None:
        service, votes, posts, _, _, _, _ = _seeded()
        org_id, post_id, user_id = uuid4(), uuid4(), uuid4()
        posts.add_post(make_post_summary(post_id=post_id, organization_id=org_id))
        await service.execute(
            CastVoteInput(
                target_type=EngagementTargetType.POST,
                target_id=post_id,
                user_id=user_id,
                organization_id=org_id,
                vote_type=VoteType.UPVOTE,
            )
        )

        output = await service.execute(
            CastVoteInput(
                target_type=EngagementTargetType.POST,
                target_id=post_id,
                user_id=user_id,
                organization_id=org_id,
                vote_type=VoteType.DOWNVOTE,
            )
        )
        assert output.vote_type is VoteType.DOWNVOTE
        counts = await votes.count_votes(EngagementTargetType.POST, post_id)
        assert counts[VoteType.UPVOTE] == 0
        assert counts[VoteType.DOWNVOTE] == 1

    async def test_switching_keeps_the_same_vote_id(self) -> None:
        service, votes, posts, _, _, _, _ = _seeded()
        org_id, post_id, user_id = uuid4(), uuid4(), uuid4()
        posts.add_post(make_post_summary(post_id=post_id, organization_id=org_id))
        first_output = await service.execute(
            CastVoteInput(
                target_type=EngagementTargetType.POST,
                target_id=post_id,
                user_id=user_id,
                organization_id=org_id,
                vote_type=VoteType.UPVOTE,
            )
        )

        second_output = await service.execute(
            CastVoteInput(
                target_type=EngagementTargetType.POST,
                target_id=post_id,
                user_id=user_id,
                organization_id=org_id,
                vote_type=VoteType.DOWNVOTE,
            )
        )
        assert second_output.vote_id == first_output.vote_id

    async def test_publishes_a_vote_switched_event(self) -> None:
        service, _, posts, _, _, _, uow = _seeded()
        org_id, post_id, user_id = uuid4(), uuid4(), uuid4()
        posts.add_post(make_post_summary(post_id=post_id, organization_id=org_id))
        await service.execute(
            CastVoteInput(
                target_type=EngagementTargetType.POST,
                target_id=post_id,
                user_id=user_id,
                organization_id=org_id,
                vote_type=VoteType.UPVOTE,
            )
        )

        await service.execute(
            CastVoteInput(
                target_type=EngagementTargetType.POST,
                target_id=post_id,
                user_id=user_id,
                organization_id=org_id,
                vote_type=VoteType.DOWNVOTE,
            )
        )
        assert any(isinstance(e, VoteSwitched) for e in uow.published_events)
