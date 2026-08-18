"""Tests for the Community Answers module's domain value objects —
construction, `__post_init__` validation, normalization, and the
`from_body` generation classmethod."""

from uuid import uuid4

import pytest

from app.modules.community_answers.domain.exceptions import (
    AnswerBodyRequiredError,
    AnswerBodyTooLongError,
    AnswerSummaryRequiredError,
    AnswerSummaryTooLongError,
)
from app.modules.community_answers.domain.value_objects import AnswerBody, AnswerId, AnswerSummary


class TestAnswerId:
    def test_wraps_a_uuid(self) -> None:
        value = uuid4()
        answer_id = AnswerId(value)
        assert answer_id.value == value

    def test_str_returns_the_uuid_string(self) -> None:
        value = uuid4()
        assert str(AnswerId(value)) == str(value)

    def test_equality_is_by_value(self) -> None:
        value = uuid4()
        assert AnswerId(value) == AnswerId(value)

    def test_inequality_for_different_values(self) -> None:
        assert AnswerId(uuid4()) != AnswerId(uuid4())

    def test_is_hashable_and_usable_as_a_dict_key(self) -> None:
        value = uuid4()
        mapping = {AnswerId(value): "answer"}
        assert mapping[AnswerId(value)] == "answer"


class TestAnswerBody:
    def test_valid_body_is_accepted(self) -> None:
        body = "This is a valid answer body."
        assert str(AnswerBody(body)) == body

    def test_strips_surrounding_whitespace(self) -> None:
        assert str(AnswerBody("  hello  ")) == "hello"

    @pytest.mark.parametrize("raw", ["", "   ", "\n\t"])
    def test_blank_body_raises(self, raw: str) -> None:
        with pytest.raises(AnswerBodyRequiredError):
            AnswerBody(raw)

    def test_body_over_max_length_raises(self) -> None:
        with pytest.raises(AnswerBodyTooLongError):
            AnswerBody("a" * 20001)

    def test_body_at_max_length_boundary_is_valid(self) -> None:
        body = "a" * 20000
        assert str(AnswerBody(body)) == body

    def test_equality_is_by_value(self) -> None:
        assert AnswerBody("same text") == AnswerBody("same text")


class TestAnswerSummary:
    def test_valid_summary_is_accepted(self) -> None:
        summary = "A short summary of the answer."
        assert str(AnswerSummary(summary)) == summary

    def test_strips_surrounding_whitespace(self) -> None:
        assert str(AnswerSummary("  hello  ")) == "hello"

    @pytest.mark.parametrize("raw", ["", "   "])
    def test_blank_summary_raises(self, raw: str) -> None:
        with pytest.raises(AnswerSummaryRequiredError):
            AnswerSummary(raw)

    def test_summary_over_max_length_raises(self) -> None:
        with pytest.raises(AnswerSummaryTooLongError):
            AnswerSummary("a" * 501)

    def test_summary_at_max_length_boundary_is_valid(self) -> None:
        summary = "a" * 500
        assert str(AnswerSummary(summary)) == summary


class TestAnswerSummaryFromBody:
    def test_generates_from_short_body(self) -> None:
        body = "This is a short answer body."
        assert str(AnswerSummary.from_body(body)) == body

    def test_strips_markdown_syntax(self) -> None:
        body = "# Heading\n\nSome **bold** and _italic_ and `code`."
        summary = str(AnswerSummary.from_body(body))
        assert "#" not in summary
        assert "*" not in summary
        assert "`" not in summary

    def test_truncates_long_body_with_ellipsis(self) -> None:
        body = "word " * 100
        summary = str(AnswerSummary.from_body(body))
        assert summary.endswith("...")
        assert len(summary) <= 210

    def test_blank_body_raises(self) -> None:
        with pytest.raises(AnswerBodyRequiredError):
            AnswerSummary.from_body("   ")

    def test_collapses_whitespace(self) -> None:
        body = "Hello\n\n\nWorld"
        assert str(AnswerSummary.from_body(body)) == "Hello World"
