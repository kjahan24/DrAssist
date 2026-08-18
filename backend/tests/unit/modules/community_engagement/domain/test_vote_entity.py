"""Tests for the `Vote` aggregate root."""

from uuid import uuid4

from app.modules.community_engagement.domain.entities import Vote
from app.modules.community_engagement.domain.enums import EngagementTargetType, VoteType
from app.modules.community_engagement.domain.events import VoteCast, VoteRemoved, VoteSwitched


def _vote(**overrides: object) -> Vote:
    defaults: dict[str, object] = {
        "user_id": uuid4(),
        "organization_id": uuid4(),
        "target_type": EngagementTargetType.POST,
        "target_id": uuid4(),
        "vote_type": VoteType.UPVOTE,
    }
    defaults.update(overrides)
    return Vote.create(**defaults)  # type: ignore[arg-type]


class TestVoteCreate:
    def test_sets_required_fields(self) -> None:
        user_id = uuid4()
        organization_id = uuid4()
        target_id = uuid4()
        vote = Vote.create(
            user_id=user_id,
            organization_id=organization_id,
            target_type=EngagementTargetType.QUESTION,
            target_id=target_id,
            vote_type=VoteType.DOWNVOTE,
        )
        assert vote.user_id == user_id
        assert vote.organization_id == organization_id
        assert vote.target_type is EngagementTargetType.QUESTION
        assert vote.target_id == target_id
        assert vote.vote_type is VoteType.DOWNVOTE

    def test_assigns_a_unique_id(self) -> None:
        first = _vote()
        second = _vote()
        assert first.id != second.id

    def test_records_a_vote_cast_event(self) -> None:
        user_id = uuid4()
        target_id = uuid4()
        vote = _vote(user_id=user_id, target_id=target_id, vote_type=VoteType.UPVOTE)
        events = vote.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, VoteCast)
        assert event.vote_id == vote.id
        assert event.user_id == user_id
        assert event.target_id == target_id
        assert event.vote_type is VoteType.UPVOTE

    def test_pull_events_drains_the_queue(self) -> None:
        vote = _vote()
        vote.pull_events()
        assert vote.pull_events() == []


class TestVoteSwitch:
    def test_flips_upvote_to_downvote(self) -> None:
        vote = _vote(vote_type=VoteType.UPVOTE)
        vote.switch(VoteType.DOWNVOTE)
        assert vote.vote_type is VoteType.DOWNVOTE

    def test_flips_downvote_to_upvote(self) -> None:
        vote = _vote(vote_type=VoteType.DOWNVOTE)
        vote.switch(VoteType.UPVOTE)
        assert vote.vote_type is VoteType.UPVOTE

    def test_keeps_the_same_row_id(self) -> None:
        vote = _vote(vote_type=VoteType.UPVOTE)
        original_id = vote.id
        vote.switch(VoteType.DOWNVOTE)
        assert vote.id == original_id

    def test_updates_updated_at_timestamp(self) -> None:
        vote = _vote()
        before = vote.updated_at
        vote.switch(VoteType.DOWNVOTE)
        assert vote.updated_at >= before

    def test_records_a_vote_switched_event(self) -> None:
        vote = _vote(vote_type=VoteType.UPVOTE)
        vote.pull_events()
        vote.switch(VoteType.DOWNVOTE)
        events = vote.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, VoteSwitched)
        assert event.vote_id == vote.id
        assert event.previous_vote_type is VoteType.UPVOTE
        assert event.new_vote_type is VoteType.DOWNVOTE


class TestVoteMarkRemoved:
    def test_records_a_vote_removed_event(self) -> None:
        user_id = uuid4()
        target_id = uuid4()
        vote = _vote(user_id=user_id, target_id=target_id)
        vote.pull_events()
        vote.mark_removed()
        events = vote.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, VoteRemoved)
        assert event.vote_id == vote.id
        assert event.user_id == user_id
        assert event.target_id == target_id

    def test_does_not_change_vote_type(self) -> None:
        vote = _vote(vote_type=VoteType.UPVOTE)
        vote.mark_removed()
        assert vote.vote_type is VoteType.UPVOTE
