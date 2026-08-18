"""Tests for the Community Engagement module's domain enums."""

from enum import StrEnum

from app.modules.community_engagement.domain.enums import (
    EngagementTargetType,
    FollowTargetType,
    VoteType,
)


class TestEngagementTargetType:
    def test_is_a_str_enum(self) -> None:
        assert issubclass(EngagementTargetType, StrEnum)

    def test_has_exactly_four_members(self) -> None:
        assert len(EngagementTargetType) == 4

    def test_post_value(self) -> None:
        assert EngagementTargetType.POST.value == "post"

    def test_question_value(self) -> None:
        assert EngagementTargetType.QUESTION.value == "question"

    def test_answer_value(self) -> None:
        assert EngagementTargetType.ANSWER.value == "answer"

    def test_comment_value(self) -> None:
        assert EngagementTargetType.COMMENT.value == "comment"

    def test_members_are_strings(self) -> None:
        for member in EngagementTargetType:
            assert isinstance(member, str)


class TestVoteType:
    def test_is_a_str_enum(self) -> None:
        assert issubclass(VoteType, StrEnum)

    def test_has_exactly_two_members(self) -> None:
        assert len(VoteType) == 2

    def test_upvote_value(self) -> None:
        assert VoteType.UPVOTE.value == "upvote"

    def test_downvote_value(self) -> None:
        assert VoteType.DOWNVOTE.value == "downvote"

    def test_members_are_strings(self) -> None:
        for member in VoteType:
            assert isinstance(member, str)


class TestFollowTargetType:
    def test_is_a_str_enum(self) -> None:
        assert issubclass(FollowTargetType, StrEnum)

    def test_has_exactly_three_members(self) -> None:
        assert len(FollowTargetType) == 3

    def test_topic_value(self) -> None:
        assert FollowTargetType.TOPIC.value == "topic"

    def test_community_value(self) -> None:
        assert FollowTargetType.COMMUNITY.value == "community"

    def test_doctor_value(self) -> None:
        assert FollowTargetType.DOCTOR.value == "doctor"

    def test_members_are_strings(self) -> None:
        for member in FollowTargetType:
            assert isinstance(member, str)
