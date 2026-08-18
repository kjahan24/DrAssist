"""Integration tests for `SqlAlchemyVoteRepository` against a real
PostgreSQL instance: round-trip persistence, `get_vote`, `count_votes`,
`switch()` persistence (updating the same row in place), and the
`(user_id, target_type, target_id)` uniqueness constraint that backs
"Prevent duplicate votes" as a concurrency safety net underneath the
application layer's own idempotency checks."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.community_engagement._helpers import persist_org_user

from app.modules.community_engagement.domain.entities import Vote
from app.modules.community_engagement.domain.enums import EngagementTargetType, VoteType
from app.modules.community_engagement.infrastructure.repositories import SqlAlchemyVoteRepository


class TestVoteRoundTrip:
    async def test_save_and_reload_a_vote(self, db_session: AsyncSession) -> None:
        organization, user = await persist_org_user(db_session)
        repo = SqlAlchemyVoteRepository(db_session)
        target_id = uuid4()
        vote = Vote.create(
            user_id=user.id,
            organization_id=organization.id,
            target_type=EngagementTargetType.POST,
            target_id=target_id,
            vote_type=VoteType.UPVOTE,
        )

        await repo.add(vote)
        await db_session.commit()

        reloaded = await repo.get_by_id(vote.id)
        assert reloaded is not None
        assert reloaded.user_id == user.id
        assert reloaded.organization_id == organization.id
        assert reloaded.target_type is EngagementTargetType.POST
        assert reloaded.target_id == target_id
        assert reloaded.vote_type is VoteType.UPVOTE


class TestGetVote:
    async def test_returns_none_when_absent(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyVoteRepository(db_session)
        assert await repo.get_vote(uuid4(), EngagementTargetType.POST, uuid4()) is None

    async def test_returns_the_matching_vote(self, db_session: AsyncSession) -> None:
        organization, user = await persist_org_user(db_session)
        repo = SqlAlchemyVoteRepository(db_session)
        target_id = uuid4()
        vote = Vote.create(
            user_id=user.id,
            organization_id=organization.id,
            target_type=EngagementTargetType.ANSWER,
            target_id=target_id,
            vote_type=VoteType.DOWNVOTE,
        )
        await repo.add(vote)
        await db_session.commit()

        found = await repo.get_vote(user.id, EngagementTargetType.ANSWER, target_id)
        assert found is not None
        assert found.id == vote.id


class TestSwitch:
    async def test_switching_updates_the_same_row_in_place(self, db_session: AsyncSession) -> None:
        organization, user = await persist_org_user(db_session)
        repo = SqlAlchemyVoteRepository(db_session)
        target_id = uuid4()
        vote = Vote.create(
            user_id=user.id,
            organization_id=organization.id,
            target_type=EngagementTargetType.POST,
            target_id=target_id,
            vote_type=VoteType.UPVOTE,
        )
        await repo.add(vote)
        await db_session.commit()

        vote.switch(VoteType.DOWNVOTE)
        await repo.add(vote)
        await db_session.commit()

        reloaded = await repo.get_by_id(vote.id)
        assert reloaded is not None
        assert reloaded.vote_type is VoteType.DOWNVOTE

        counts = await repo.count_votes(EngagementTargetType.POST, target_id)
        assert counts == {VoteType.UPVOTE: 0, VoteType.DOWNVOTE: 1}


class TestCountVotes:
    async def test_zero_filled_when_no_votes_exist(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyVoteRepository(db_session)
        counts = await repo.count_votes(EngagementTargetType.POST, uuid4())
        assert counts == {VoteType.UPVOTE: 0, VoteType.DOWNVOTE: 0}

    async def test_counts_both_directions(self, db_session: AsyncSession) -> None:
        organization, _ = await persist_org_user(db_session)
        repo = SqlAlchemyVoteRepository(db_session)
        target_id = uuid4()

        for vote_type in (VoteType.UPVOTE, VoteType.UPVOTE, VoteType.DOWNVOTE):
            _, voter = await persist_org_user(db_session)
            await repo.add(
                Vote.create(
                    user_id=voter.id,
                    organization_id=organization.id,
                    target_type=EngagementTargetType.QUESTION,
                    target_id=target_id,
                    vote_type=vote_type,
                )
            )
        await db_session.commit()

        counts = await repo.count_votes(EngagementTargetType.QUESTION, target_id)
        assert counts[VoteType.UPVOTE] == 2
        assert counts[VoteType.DOWNVOTE] == 1

    async def test_is_scoped_to_target_type(self, db_session: AsyncSession) -> None:
        organization, user = await persist_org_user(db_session)
        repo = SqlAlchemyVoteRepository(db_session)
        target_id = uuid4()
        await repo.add(
            Vote.create(
                user_id=user.id,
                organization_id=organization.id,
                target_type=EngagementTargetType.POST,
                target_id=target_id,
                vote_type=VoteType.UPVOTE,
            )
        )
        await db_session.commit()

        counts = await repo.count_votes(EngagementTargetType.ANSWER, target_id)
        assert counts == {VoteType.UPVOTE: 0, VoteType.DOWNVOTE: 0}


class TestRemove:
    async def test_removes_the_vote_row(self, db_session: AsyncSession) -> None:
        organization, user = await persist_org_user(db_session)
        repo = SqlAlchemyVoteRepository(db_session)
        vote = Vote.create(
            user_id=user.id,
            organization_id=organization.id,
            target_type=EngagementTargetType.POST,
            target_id=uuid4(),
            vote_type=VoteType.UPVOTE,
        )
        await repo.add(vote)
        await db_session.commit()

        await repo.remove(vote.id)
        await db_session.commit()

        assert await repo.get_by_id(vote.id) is None

    async def test_is_a_no_op_when_the_row_is_already_gone(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyVoteRepository(db_session)
        await repo.remove(uuid4())  # must not raise
        await db_session.commit()


class TestUniqueUserTargetConstraint:
    async def test_duplicate_vote_row_violates_the_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, user = await persist_org_user(db_session)
        repo = SqlAlchemyVoteRepository(db_session)
        target_id = uuid4()

        first = Vote.create(
            user_id=user.id,
            organization_id=organization.id,
            target_type=EngagementTargetType.POST,
            target_id=target_id,
            vote_type=VoteType.UPVOTE,
        )
        await repo.add(first)
        await db_session.commit()

        second = Vote.create(
            user_id=user.id,
            organization_id=organization.id,
            target_type=EngagementTargetType.POST,
            target_id=target_id,
            vote_type=VoteType.DOWNVOTE,
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestVoteRequiresValidReferences:
    async def test_nonexistent_user_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _ = await persist_org_user(db_session)
        repo = SqlAlchemyVoteRepository(db_session)
        vote = Vote.create(
            user_id=uuid4(),
            organization_id=organization.id,
            target_type=EngagementTargetType.POST,
            target_id=uuid4(),
            vote_type=VoteType.UPVOTE,
        )
        await repo.add(vote)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_organization_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        _, user = await persist_org_user(db_session)
        repo = SqlAlchemyVoteRepository(db_session)
        vote = Vote.create(
            user_id=user.id,
            organization_id=uuid4(),
            target_type=EngagementTargetType.POST,
            target_id=uuid4(),
            vote_type=VoteType.UPVOTE,
        )
        await repo.add(vote)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
