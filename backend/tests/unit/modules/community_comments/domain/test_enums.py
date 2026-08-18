"""Tests for the Community Comments module's domain enums."""

from enum import StrEnum

from app.modules.community_comments.domain.enums import CommentStatus, CommentTargetType


class TestCommentStatus:
    def test_is_a_str_enum(self) -> None:
        assert issubclass(CommentStatus, StrEnum)

    def test_has_exactly_four_members(self) -> None:
        assert len(CommentStatus) == 4

    def test_draft_value(self) -> None:
        assert CommentStatus.DRAFT.value == "draft"

    def test_published_value(self) -> None:
        assert CommentStatus.PUBLISHED.value == "published"

    def test_archived_value(self) -> None:
        assert CommentStatus.ARCHIVED.value == "archived"

    def test_deleted_value(self) -> None:
        assert CommentStatus.DELETED.value == "deleted"

    def test_members_are_strings(self) -> None:
        for member in CommentStatus:
            assert isinstance(member, str)


class TestCommentTargetType:
    def test_is_a_str_enum(self) -> None:
        assert issubclass(CommentTargetType, StrEnum)

    def test_has_exactly_three_members(self) -> None:
        assert len(CommentTargetType) == 3

    def test_post_value(self) -> None:
        assert CommentTargetType.POST.value == "post"

    def test_question_value(self) -> None:
        assert CommentTargetType.QUESTION.value == "question"

    def test_answer_value(self) -> None:
        assert CommentTargetType.ANSWER.value == "answer"

    def test_members_are_strings(self) -> None:
        for member in CommentTargetType:
            assert isinstance(member, str)
