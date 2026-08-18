"""Tests for the Community Engagement module's domain exceptions."""

from uuid import uuid4

from app.modules.community_engagement.domain.enums import EngagementTargetType
from app.modules.community_engagement.domain.exceptions import (
    CannotFollowSelfError,
    CommunityNotFoundForFollowError,
    SaveTargetNotAcceptingSavesError,
    SaveTargetNotFoundError,
    TopicNotFoundForFollowError,
    UnsupportedSaveTargetTypeError,
    UserNotFoundForFollowError,
    VoteTargetNotAcceptingVotesError,
    VoteTargetNotFoundError,
)
from app.shared.domain.exceptions import DomainError


class TestVoteTargetNotFoundError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(VoteTargetNotFoundError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        target_id = uuid4()
        error = VoteTargetNotFoundError(target_id)
        assert str(target_id) in str(error)
        assert error.target_id == target_id


class TestVoteTargetNotAcceptingVotesError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(VoteTargetNotAcceptingVotesError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        target_id = uuid4()
        error = VoteTargetNotAcceptingVotesError(target_id)
        assert str(target_id) in str(error)
        assert error.target_id == target_id


class TestSaveTargetNotFoundError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(SaveTargetNotFoundError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        target_id = uuid4()
        error = SaveTargetNotFoundError(target_id)
        assert str(target_id) in str(error)
        assert error.target_id == target_id


class TestSaveTargetNotAcceptingSavesError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(SaveTargetNotAcceptingSavesError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        target_id = uuid4()
        error = SaveTargetNotAcceptingSavesError(target_id)
        assert str(target_id) in str(error)
        assert error.target_id == target_id


class TestUnsupportedSaveTargetTypeError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(UnsupportedSaveTargetTypeError(EngagementTargetType.COMMENT), DomainError)

    def test_message_includes_target_type(self) -> None:
        error = UnsupportedSaveTargetTypeError(EngagementTargetType.COMMENT)
        assert "comment" in str(error)
        assert error.target_type is EngagementTargetType.COMMENT


class TestTopicNotFoundForFollowError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(TopicNotFoundForFollowError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        topic_id = uuid4()
        error = TopicNotFoundForFollowError(topic_id)
        assert str(topic_id) in str(error)
        assert error.topic_id == topic_id


class TestCommunityNotFoundForFollowError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CommunityNotFoundForFollowError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        community_id = uuid4()
        error = CommunityNotFoundForFollowError(community_id)
        assert str(community_id) in str(error)
        assert error.community_id == community_id


class TestUserNotFoundForFollowError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(UserNotFoundForFollowError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        user_id = uuid4()
        error = UserNotFoundForFollowError(user_id)
        assert str(user_id) in str(error)
        assert error.user_id == user_id


class TestCannotFollowSelfError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CannotFollowSelfError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        user_id = uuid4()
        error = CannotFollowSelfError(user_id)
        assert str(user_id) in str(error)
        assert error.user_id == user_id
