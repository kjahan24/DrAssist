"""Tests for the Community Questions module's domain value objects —
construction, `__post_init__` validation, normalization, and the
`from_title`/`from_body` generation classmethods."""

from uuid import uuid4

import pytest

from app.modules.community_questions.domain.exceptions import (
    InvalidQuestionSlugError,
    QuestionBodyRequiredError,
    QuestionSummaryRequiredError,
    QuestionSummaryTooLongError,
    QuestionTitleRequiredError,
    QuestionTitleTooLongError,
)
from app.modules.community_questions.domain.value_objects import (
    QuestionId,
    QuestionSlug,
    QuestionSummary,
    QuestionTitle,
)


class TestQuestionId:
    def test_wraps_a_uuid(self) -> None:
        value = uuid4()
        question_id = QuestionId(value)
        assert question_id.value == value

    def test_str_returns_the_uuid_string(self) -> None:
        value = uuid4()
        assert str(QuestionId(value)) == str(value)

    def test_equality_is_by_value(self) -> None:
        value = uuid4()
        assert QuestionId(value) == QuestionId(value)

    def test_inequality_for_different_values(self) -> None:
        assert QuestionId(uuid4()) != QuestionId(uuid4())

    def test_is_hashable_and_usable_as_a_dict_key(self) -> None:
        value = uuid4()
        mapping = {QuestionId(value): "question"}
        assert mapping[QuestionId(value)] == "question"


class TestQuestionSlug:
    def test_valid_slug_is_accepted(self) -> None:
        assert str(QuestionSlug("how-to-manage-hypertension")) == "how-to-manage-hypertension"

    def test_normalizes_to_lowercase(self) -> None:
        assert str(QuestionSlug("How-To-Manage")) == "how-to-manage"

    def test_strips_surrounding_whitespace(self) -> None:
        assert str(QuestionSlug("  how-to-manage  ")) == "how-to-manage"

    @pytest.mark.parametrize(
        "raw",
        [
            "ab",
            "a" * 101,
            "-question",
            "question-",
            "question--title",
            "question title",
            "question_title",
            "",
        ],
    )
    def test_invalid_slugs_raise(self, raw: str) -> None:
        with pytest.raises(InvalidQuestionSlugError):
            QuestionSlug(raw)

    def test_minimum_length_boundary_is_valid(self) -> None:
        assert str(QuestionSlug("abc")) == "abc"

    def test_maximum_length_boundary_is_valid(self) -> None:
        slug = "a" * 100
        assert str(QuestionSlug(slug)) == slug

    def test_equality_is_by_value(self) -> None:
        assert QuestionSlug("oncology") == QuestionSlug("oncology")


class TestQuestionSlugFromTitle:
    def test_slugifies_a_normal_title(self) -> None:
        assert (
            str(QuestionSlug.from_title("How to Manage Hypertension"))
            == "how-to-manage-hypertension"
        )

    def test_strips_punctuation(self) -> None:
        assert (
            str(QuestionSlug.from_title("What's New in Cardiology?")) == "whats-new-in-cardiology"
        )

    def test_collapses_multiple_spaces(self) -> None:
        assert str(QuestionSlug.from_title("Hello    World")) == "hello-world"

    def test_result_is_a_valid_slug(self) -> None:
        # must not raise
        QuestionSlug(str(QuestionSlug.from_title("Any Normal Title")))

    def test_title_of_only_punctuation_falls_back_to_a_generated_slug(self) -> None:
        slug = QuestionSlug.from_title("???!!!")
        assert str(slug).startswith("question-")
        assert len(str(slug)) >= 3

    def test_very_short_title_gets_a_unique_suffix(self) -> None:
        slug = QuestionSlug.from_title("A")
        assert str(slug).startswith("a-")

    def test_very_long_title_is_truncated_to_max_length(self) -> None:
        slug = QuestionSlug.from_title("word " * 100)
        assert len(str(slug)) <= 100

    def test_two_calls_with_punctuation_only_titles_produce_different_slugs(self) -> None:
        first = QuestionSlug.from_title("???")
        second = QuestionSlug.from_title("???")
        assert first != second


class TestQuestionTitle:
    def test_valid_title_is_accepted(self) -> None:
        assert str(QuestionTitle("How to Manage Hypertension")) == "How to Manage Hypertension"

    def test_strips_surrounding_whitespace(self) -> None:
        assert str(QuestionTitle("  Hello  ")) == "Hello"

    @pytest.mark.parametrize("raw", ["", "   "])
    def test_blank_title_raises(self, raw: str) -> None:
        with pytest.raises(QuestionTitleRequiredError):
            QuestionTitle(raw)

    def test_title_over_max_length_raises(self) -> None:
        with pytest.raises(QuestionTitleTooLongError):
            QuestionTitle("a" * 301)

    def test_title_at_max_length_boundary_is_valid(self) -> None:
        title = "a" * 300
        assert str(QuestionTitle(title)) == title


class TestQuestionSummary:
    def test_valid_summary_is_accepted(self) -> None:
        summary = "A short summary of the question."
        assert str(QuestionSummary(summary)) == summary

    def test_strips_surrounding_whitespace(self) -> None:
        assert str(QuestionSummary("  hello  ")) == "hello"

    @pytest.mark.parametrize("raw", ["", "   "])
    def test_blank_summary_raises(self, raw: str) -> None:
        with pytest.raises(QuestionSummaryRequiredError):
            QuestionSummary(raw)

    def test_summary_over_max_length_raises(self) -> None:
        with pytest.raises(QuestionSummaryTooLongError):
            QuestionSummary("a" * 501)

    def test_summary_at_max_length_boundary_is_valid(self) -> None:
        summary = "a" * 500
        assert str(QuestionSummary(summary)) == summary


class TestQuestionSummaryFromBody:
    def test_generates_from_short_body(self) -> None:
        body = "This is a short question body."
        assert str(QuestionSummary.from_body(body)) == body

    def test_strips_markdown_syntax(self) -> None:
        body = "# Heading\n\nSome **bold** and _italic_ and `code`."
        summary = str(QuestionSummary.from_body(body))
        assert "#" not in summary
        assert "*" not in summary
        assert "`" not in summary

    def test_truncates_long_body_with_ellipsis(self) -> None:
        body = "word " * 100
        summary = str(QuestionSummary.from_body(body))
        assert summary.endswith("...")
        assert len(summary) <= 210

    def test_blank_body_raises(self) -> None:
        with pytest.raises(QuestionBodyRequiredError):
            QuestionSummary.from_body("   ")

    def test_collapses_whitespace(self) -> None:
        body = "Hello\n\n\nWorld"
        assert str(QuestionSummary.from_body(body)) == "Hello World"
