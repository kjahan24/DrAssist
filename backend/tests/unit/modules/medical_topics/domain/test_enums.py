"""Tests for the Medical Topics module's domain enums."""

from enum import StrEnum

from app.modules.medical_topics.domain.enums import (
    TopicRelationType,
    TopicStatus,
    TopicVisibility,
)


class TestTopicStatus:
    def test_is_a_str_enum(self) -> None:
        assert issubclass(TopicStatus, StrEnum)

    def test_has_exactly_three_members(self) -> None:
        assert len(TopicStatus) == 3

    def test_draft_value(self) -> None:
        assert TopicStatus.DRAFT.value == "draft"

    def test_published_value(self) -> None:
        assert TopicStatus.PUBLISHED.value == "published"

    def test_archived_value(self) -> None:
        assert TopicStatus.ARCHIVED.value == "archived"

    def test_members_are_strings(self) -> None:
        for member in TopicStatus:
            assert isinstance(member, str)


class TestTopicVisibility:
    def test_is_a_str_enum(self) -> None:
        assert issubclass(TopicVisibility, StrEnum)

    def test_has_exactly_three_members(self) -> None:
        assert len(TopicVisibility) == 3

    def test_public_value(self) -> None:
        assert TopicVisibility.PUBLIC.value == "public"

    def test_unlisted_value(self) -> None:
        assert TopicVisibility.UNLISTED.value == "unlisted"

    def test_private_value(self) -> None:
        assert TopicVisibility.PRIVATE.value == "private"

    def test_members_are_strings(self) -> None:
        for member in TopicVisibility:
            assert isinstance(member, str)


class TestTopicRelationType:
    def test_is_a_str_enum(self) -> None:
        assert issubclass(TopicRelationType, StrEnum)

    def test_has_exactly_two_members(self) -> None:
        assert len(TopicRelationType) == 2

    def test_related_value(self) -> None:
        assert TopicRelationType.RELATED.value == "related"

    def test_see_also_value(self) -> None:
        assert TopicRelationType.SEE_ALSO.value == "see_also"

    def test_members_are_strings(self) -> None:
        for member in TopicRelationType:
            assert isinstance(member, str)
