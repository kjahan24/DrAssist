"""Tests for the Community Answers module's domain enums."""

from enum import StrEnum

from app.modules.community_answers.domain.enums import AnswerStatus, AnswerVisibility


class TestAnswerStatus:
    def test_is_a_str_enum(self) -> None:
        assert issubclass(AnswerStatus, StrEnum)

    def test_has_exactly_four_members(self) -> None:
        assert len(AnswerStatus) == 4

    def test_draft_value(self) -> None:
        assert AnswerStatus.DRAFT.value == "draft"

    def test_published_value(self) -> None:
        assert AnswerStatus.PUBLISHED.value == "published"

    def test_archived_value(self) -> None:
        assert AnswerStatus.ARCHIVED.value == "archived"

    def test_deleted_value(self) -> None:
        assert AnswerStatus.DELETED.value == "deleted"

    def test_has_no_closed_member(self) -> None:
        assert not hasattr(AnswerStatus, "CLOSED")

    def test_members_are_strings(self) -> None:
        for member in AnswerStatus:
            assert isinstance(member, str)


class TestAnswerVisibility:
    def test_is_a_str_enum(self) -> None:
        assert issubclass(AnswerVisibility, StrEnum)

    def test_has_exactly_three_members(self) -> None:
        assert len(AnswerVisibility) == 3

    def test_public_value(self) -> None:
        assert AnswerVisibility.PUBLIC.value == "public"

    def test_members_only_value(self) -> None:
        assert AnswerVisibility.MEMBERS_ONLY.value == "members_only"

    def test_private_value(self) -> None:
        assert AnswerVisibility.PRIVATE.value == "private"

    def test_members_are_strings(self) -> None:
        for member in AnswerVisibility:
            assert isinstance(member, str)
