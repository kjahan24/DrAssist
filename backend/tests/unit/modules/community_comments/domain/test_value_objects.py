"""Tests for the Community Comments module's domain value objects —
construction, `__post_init__` validation, normalization."""

from uuid import uuid4

import pytest

from app.modules.community_comments.domain.exceptions import (
    CommentBodyRequiredError,
    CommentBodyTooLongError,
)
from app.modules.community_comments.domain.value_objects import CommentBody, CommentId


class TestCommentId:
    def test_wraps_a_uuid(self) -> None:
        value = uuid4()
        comment_id = CommentId(value)
        assert comment_id.value == value

    def test_str_returns_the_uuid_string(self) -> None:
        value = uuid4()
        assert str(CommentId(value)) == str(value)

    def test_equality_is_by_value(self) -> None:
        value = uuid4()
        assert CommentId(value) == CommentId(value)

    def test_inequality_for_different_values(self) -> None:
        assert CommentId(uuid4()) != CommentId(uuid4())

    def test_is_hashable_and_usable_as_a_dict_key(self) -> None:
        value = uuid4()
        mapping = {CommentId(value): "comment"}
        assert mapping[CommentId(value)] == "comment"

    def test_two_ids_wrapping_the_same_uuid_hash_equal(self) -> None:
        value = uuid4()
        assert hash(CommentId(value)) == hash(CommentId(value))


class TestCommentBody:
    def test_valid_body_is_accepted(self) -> None:
        body = "This is a valid comment body."
        assert str(CommentBody(body)) == body

    def test_strips_surrounding_whitespace(self) -> None:
        assert str(CommentBody("  hello  ")) == "hello"

    @pytest.mark.parametrize("raw", ["", "   ", "\n\t"])
    def test_blank_body_raises(self, raw: str) -> None:
        with pytest.raises(CommentBodyRequiredError):
            CommentBody(raw)

    def test_body_over_max_length_raises(self) -> None:
        with pytest.raises(CommentBodyTooLongError):
            CommentBody("a" * 10001)

    def test_body_at_max_length_boundary_is_valid(self) -> None:
        body = "a" * 10000
        assert str(CommentBody(body)) == body

    def test_equality_is_by_value(self) -> None:
        assert CommentBody("same text") == CommentBody("same text")

    def test_inequality_for_different_values(self) -> None:
        assert CommentBody("first") != CommentBody("second")

    def test_body_one_char_over_max_length_raises(self) -> None:
        with pytest.raises(CommentBodyTooLongError):
            CommentBody("a" * 10001)

    def test_body_too_long_error_reports_the_configured_max_length(self) -> None:
        try:
            CommentBody("a" * 10001)
            error = None
        except CommentBodyTooLongError as e:
            error = e
        assert error is not None
        assert error.max_length == 10000

    def test_single_character_body_is_valid(self) -> None:
        assert str(CommentBody("a")) == "a"

    def test_preserves_internal_whitespace(self) -> None:
        assert str(CommentBody("  hello   world  ")) == "hello   world"

    def test_is_hashable_and_usable_as_a_dict_key(self) -> None:
        mapping = {CommentBody("same text"): "value"}
        assert mapping[CommentBody("same text")] == "value"

    def test_str_repr_matches_the_stripped_value(self) -> None:
        body = CommentBody("  padded body  ")
        assert str(body) == body.value
