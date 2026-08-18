"""Validation tests for the Community Engagement module's Pydantic v2
response schemas. No request schemas exist in this module — see
`schemas.py`'s own docstring for why."""

from datetime import UTC, datetime
from uuid import uuid4

from app.modules.community_engagement.domain.enums import (
    EngagementTargetType,
    FollowTargetType,
    VoteType,
)
from app.modules.community_engagement.presentation.schemas import (
    FollowerFeedResponse,
    FollowerResponse,
    SavedContentFeedResponse,
    SavedContentResponse,
    SavedContentSummaryResponse,
    VoteCountsResponse,
    VoteResponse,
    VoteStatusResponse,
)


class TestVoteResponse:
    def test_constructs_from_a_full_field_set(self) -> None:
        vote_id, target_id = uuid4(), uuid4()
        response = VoteResponse(
            vote_id=vote_id,
            target_type=EngagementTargetType.POST,
            target_id=target_id,
            vote_type=VoteType.UPVOTE,
        )
        assert response.vote_id == vote_id
        assert response.vote_type is VoteType.UPVOTE

    def test_constructs_from_attributes(self) -> None:
        class _FakeOutput:
            vote_id = uuid4()
            target_type = EngagementTargetType.ANSWER
            target_id = uuid4()
            vote_type = VoteType.DOWNVOTE

        response = VoteResponse.model_validate(_FakeOutput())
        assert response.vote_type is VoteType.DOWNVOTE


class TestVoteStatusResponse:
    def test_defaults_vote_type_to_none(self) -> None:
        response = VoteStatusResponse(target_type=EngagementTargetType.POST, target_id=uuid4())
        assert response.vote_type is None

    def test_accepts_an_explicit_vote_type(self) -> None:
        response = VoteStatusResponse(
            target_type=EngagementTargetType.POST, target_id=uuid4(), vote_type=VoteType.UPVOTE
        )
        assert response.vote_type is VoteType.UPVOTE


class TestVoteCountsResponse:
    def test_constructs_from_a_full_field_set(self) -> None:
        response = VoteCountsResponse(
            target_type=EngagementTargetType.QUESTION,
            target_id=uuid4(),
            upvotes=5,
            downvotes=2,
            net_score=3,
        )
        assert response.upvotes == 5
        assert response.net_score == 3


class TestSavedContentResponse:
    def test_constructs_from_a_full_field_set(self) -> None:
        saved_content_id, target_id = uuid4(), uuid4()
        response = SavedContentResponse(
            saved_content_id=saved_content_id,
            target_type=EngagementTargetType.ANSWER,
            target_id=target_id,
        )
        assert response.saved_content_id == saved_content_id


class TestSavedContentSummaryResponse:
    def test_constructs_from_a_full_field_set(self) -> None:
        response = SavedContentSummaryResponse(
            id=uuid4(),
            user_id=uuid4(),
            target_type=EngagementTargetType.POST,
            target_id=uuid4(),
            created_at=datetime.now(UTC),
        )
        assert response.target_type is EngagementTargetType.POST


class TestSavedContentFeedResponse:
    def test_defaults_next_cursor_to_none(self) -> None:
        response = SavedContentFeedResponse(items=[])
        assert response.next_cursor is None

    def test_accepts_a_cursor(self) -> None:
        response = SavedContentFeedResponse(items=[], next_cursor="abc123")
        assert response.next_cursor == "abc123"


class TestFollowerResponse:
    def test_constructs_from_a_full_field_set(self) -> None:
        follow_id, target_id, user_id = uuid4(), uuid4(), uuid4()
        response = FollowerResponse(
            id=follow_id,
            follow_target_type=FollowTargetType.TOPIC,
            target_id=target_id,
            user_id=user_id,
            created_at=datetime.now(UTC),
        )
        assert response.id == follow_id
        assert response.follow_target_type is FollowTargetType.TOPIC


class TestFollowerFeedResponse:
    def test_defaults_next_cursor_to_none(self) -> None:
        response = FollowerFeedResponse(items=[])
        assert response.next_cursor is None

    def test_accepts_a_cursor(self) -> None:
        response = FollowerFeedResponse(items=[], next_cursor="xyz789")
        assert response.next_cursor == "xyz789"
