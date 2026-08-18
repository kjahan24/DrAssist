"""Unit tests for the Community Engagement module's application-layer
DTOs — construction, defaults, and the `.id`/`.net_score` computed
properties."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.modules.community_engagement.application.dto import (
    CastVoteInput,
    CastVoteOutput,
    FollowCommunityInput,
    FollowDoctorInput,
    FollowerFeedOutput,
    FollowerSummaryDTO,
    FollowTopicInput,
    ListFollowersInput,
    ListFollowingInput,
    ListSavedContentInput,
    RemoveVoteInput,
    SaveContentInput,
    SaveContentOutput,
    SavedContentFeedOutput,
    SavedContentSummaryDTO,
    UnfollowCommunityInput,
    UnfollowDoctorInput,
    UnfollowTopicInput,
    UnsaveContentInput,
    VoteCountsDTO,
    VoteStatusDTO,
)
from app.modules.community_engagement.domain.enums import (
    EngagementTargetType,
    FollowTargetType,
    VoteType,
)


class TestVoteDTOs:
    def test_cast_vote_input(self) -> None:
        target_id, user_id, org_id = uuid4(), uuid4(), uuid4()
        dto = CastVoteInput(
            target_type=EngagementTargetType.POST,
            target_id=target_id,
            user_id=user_id,
            organization_id=org_id,
            vote_type=VoteType.UPVOTE,
        )
        assert dto.target_id == target_id
        assert dto.user_id == user_id
        assert dto.organization_id == org_id
        assert dto.vote_type is VoteType.UPVOTE

    def test_cast_vote_input_is_immutable(self) -> None:
        dto = CastVoteInput(
            target_type=EngagementTargetType.POST,
            target_id=uuid4(),
            user_id=uuid4(),
            organization_id=uuid4(),
            vote_type=VoteType.UPVOTE,
        )
        with pytest.raises(FrozenInstanceError):
            dto.vote_type = VoteType.DOWNVOTE  # type: ignore[misc]

    def test_cast_vote_output(self) -> None:
        vote_id, target_id = uuid4(), uuid4()
        dto = CastVoteOutput(
            vote_id=vote_id,
            target_type=EngagementTargetType.ANSWER,
            target_id=target_id,
            vote_type=VoteType.DOWNVOTE,
        )
        assert dto.vote_id == vote_id
        assert dto.vote_type is VoteType.DOWNVOTE

    def test_remove_vote_input(self) -> None:
        target_id, user_id = uuid4(), uuid4()
        dto = RemoveVoteInput(
            target_type=EngagementTargetType.COMMENT, target_id=target_id, user_id=user_id
        )
        assert dto.target_id == target_id
        assert dto.user_id == user_id

    def test_vote_status_dto_defaults_to_none(self) -> None:
        dto = VoteStatusDTO(target_type=EngagementTargetType.POST, target_id=uuid4())
        assert dto.vote_type is None

    def test_vote_status_dto_accepts_an_explicit_vote_type(self) -> None:
        dto = VoteStatusDTO(
            target_type=EngagementTargetType.POST, target_id=uuid4(), vote_type=VoteType.UPVOTE
        )
        assert dto.vote_type is VoteType.UPVOTE

    def test_vote_counts_dto_net_score_positive(self) -> None:
        dto = VoteCountsDTO(
            target_type=EngagementTargetType.POST, target_id=uuid4(), upvotes=5, downvotes=2
        )
        assert dto.net_score == 3

    def test_vote_counts_dto_net_score_negative(self) -> None:
        dto = VoteCountsDTO(
            target_type=EngagementTargetType.POST, target_id=uuid4(), upvotes=1, downvotes=4
        )
        assert dto.net_score == -3

    def test_vote_counts_dto_net_score_zero(self) -> None:
        dto = VoteCountsDTO(
            target_type=EngagementTargetType.POST, target_id=uuid4(), upvotes=0, downvotes=0
        )
        assert dto.net_score == 0


class TestSaveDTOs:
    def test_save_content_input(self) -> None:
        target_id, user_id, org_id = uuid4(), uuid4(), uuid4()
        dto = SaveContentInput(
            target_type=EngagementTargetType.QUESTION,
            target_id=target_id,
            user_id=user_id,
            organization_id=org_id,
        )
        assert dto.target_id == target_id
        assert dto.organization_id == org_id

    def test_save_content_output(self) -> None:
        saved_content_id, target_id = uuid4(), uuid4()
        dto = SaveContentOutput(
            saved_content_id=saved_content_id,
            target_type=EngagementTargetType.ANSWER,
            target_id=target_id,
        )
        assert dto.saved_content_id == saved_content_id

    def test_unsave_content_input(self) -> None:
        dto = UnsaveContentInput(
            target_type=EngagementTargetType.POST, target_id=uuid4(), user_id=uuid4()
        )
        assert dto.target_type is EngagementTargetType.POST

    def test_saved_content_summary_id_alias(self) -> None:
        saved_content_id = uuid4()
        dto = SavedContentSummaryDTO(
            saved_content_id=saved_content_id,
            user_id=uuid4(),
            target_type=EngagementTargetType.POST,
            target_id=uuid4(),
            created_at=datetime.now(UTC),
        )
        assert dto.id == saved_content_id

    def test_list_saved_content_input_defaults(self) -> None:
        org_id, user_id = uuid4(), uuid4()
        dto = ListSavedContentInput(organization_id=org_id, user_id=user_id)
        assert dto.target_type is None
        assert dto.cursor is None
        assert dto.limit == 20

    def test_list_saved_content_input_is_immutable(self) -> None:
        dto = ListSavedContentInput(organization_id=uuid4(), user_id=uuid4())
        with pytest.raises(FrozenInstanceError):
            dto.limit = 99  # type: ignore[misc]

    def test_saved_content_feed_output_defaults(self) -> None:
        dto = SavedContentFeedOutput(items=())
        assert dto.next_cursor is None


class TestFollowDTOs:
    def test_follow_topic_input(self) -> None:
        user_id, org_id, topic_id = uuid4(), uuid4(), uuid4()
        dto = FollowTopicInput(user_id=user_id, organization_id=org_id, topic_id=topic_id)
        assert dto.topic_id == topic_id

    def test_unfollow_topic_input(self) -> None:
        dto = UnfollowTopicInput(user_id=uuid4(), topic_id=uuid4())
        assert isinstance(dto.topic_id, UUID)

    def test_follow_community_input(self) -> None:
        community_id = uuid4()
        dto = FollowCommunityInput(
            user_id=uuid4(), organization_id=uuid4(), community_id=community_id
        )
        assert dto.community_id == community_id

    def test_unfollow_community_input(self) -> None:
        dto = UnfollowCommunityInput(user_id=uuid4(), community_id=uuid4())
        assert isinstance(dto.community_id, UUID)

    def test_follow_doctor_input(self) -> None:
        follower_id, followed_id = uuid4(), uuid4()
        dto = FollowDoctorInput(
            follower_user_id=follower_id, organization_id=uuid4(), followed_user_id=followed_id
        )
        assert dto.follower_user_id == follower_id
        assert dto.followed_user_id == followed_id

    def test_unfollow_doctor_input(self) -> None:
        dto = UnfollowDoctorInput(follower_user_id=uuid4(), followed_user_id=uuid4())
        assert isinstance(dto.followed_user_id, UUID)

    def test_follower_summary_id_alias(self) -> None:
        follow_id = uuid4()
        dto = FollowerSummaryDTO(
            follow_id=follow_id,
            follow_target_type=FollowTargetType.TOPIC,
            target_id=uuid4(),
            user_id=uuid4(),
            created_at=datetime.now(UTC),
        )
        assert dto.id == follow_id

    def test_list_followers_input_defaults(self) -> None:
        target_id = uuid4()
        dto = ListFollowersInput(follow_target_type=FollowTargetType.COMMUNITY, target_id=target_id)
        assert dto.cursor is None
        assert dto.limit == 20

    def test_list_following_input_defaults(self) -> None:
        user_id = uuid4()
        dto = ListFollowingInput(follow_target_type=FollowTargetType.DOCTOR, user_id=user_id)
        assert dto.user_id == user_id
        assert dto.limit == 20

    def test_follower_feed_output_defaults(self) -> None:
        dto = FollowerFeedOutput(items=())
        assert dto.next_cursor is None
