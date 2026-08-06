"""Tests for the Community Posts module's domain value objects —
construction, `__post_init__` validation, normalization, and the
`from_title`/`from_body` generation classmethods."""

from uuid import uuid4

import pytest

from app.modules.community_posts.domain.exceptions import (
    InvalidPostSlugError,
    PostBodyRequiredError,
    PostExcerptRequiredError,
    PostExcerptTooLongError,
    PostTitleRequiredError,
    PostTitleTooLongError,
)
from app.modules.community_posts.domain.value_objects import (
    PostExcerpt,
    PostId,
    PostSlug,
    PostTitle,
)


class TestPostId:
    def test_wraps_a_uuid(self) -> None:
        value = uuid4()
        post_id = PostId(value)
        assert post_id.value == value

    def test_str_returns_the_uuid_string(self) -> None:
        value = uuid4()
        assert str(PostId(value)) == str(value)

    def test_equality_is_by_value(self) -> None:
        value = uuid4()
        assert PostId(value) == PostId(value)

    def test_inequality_for_different_values(self) -> None:
        assert PostId(uuid4()) != PostId(uuid4())

    def test_is_hashable_and_usable_as_a_dict_key(self) -> None:
        value = uuid4()
        mapping = {PostId(value): "post"}
        assert mapping[PostId(value)] == "post"


class TestPostSlug:
    def test_valid_slug_is_accepted(self) -> None:
        assert str(PostSlug("cardiac-arrhythmia-tips")) == "cardiac-arrhythmia-tips"

    def test_normalizes_to_lowercase(self) -> None:
        assert str(PostSlug("Cardiac-Arrhythmia")) == "cardiac-arrhythmia"

    def test_strips_surrounding_whitespace(self) -> None:
        assert str(PostSlug("  cardiac-arrhythmia  ")) == "cardiac-arrhythmia"

    @pytest.mark.parametrize(
        "raw",
        ["ab", "a" * 101, "-post", "post-", "post--title", "post title", "post_title", ""],
    )
    def test_invalid_slugs_raise(self, raw: str) -> None:
        with pytest.raises(InvalidPostSlugError):
            PostSlug(raw)

    def test_minimum_length_boundary_is_valid(self) -> None:
        assert str(PostSlug("abc")) == "abc"

    def test_maximum_length_boundary_is_valid(self) -> None:
        slug = "a" * 100
        assert str(PostSlug(slug)) == slug

    def test_equality_is_by_value(self) -> None:
        assert PostSlug("oncology") == PostSlug("oncology")


class TestPostSlugFromTitle:
    def test_slugifies_a_normal_title(self) -> None:
        assert str(PostSlug.from_title("Cardiac Arrhythmia Tips")) == "cardiac-arrhythmia-tips"

    def test_strips_punctuation(self) -> None:
        assert str(PostSlug.from_title("What's New in Cardiology?")) == "whats-new-in-cardiology"

    def test_collapses_multiple_spaces(self) -> None:
        assert str(PostSlug.from_title("Hello    World")) == "hello-world"

    def test_result_is_a_valid_slug(self) -> None:
        # must not raise
        PostSlug(str(PostSlug.from_title("Any Normal Title")))

    def test_title_of_only_punctuation_falls_back_to_a_generated_slug(self) -> None:
        slug = PostSlug.from_title("???!!!")
        assert str(slug).startswith("post-")
        assert len(str(slug)) >= 3

    def test_very_short_title_gets_a_unique_suffix(self) -> None:
        slug = PostSlug.from_title("A")
        assert str(slug).startswith("a-")

    def test_very_long_title_is_truncated_to_max_length(self) -> None:
        slug = PostSlug.from_title("word " * 100)
        assert len(str(slug)) <= 100

    def test_two_calls_with_punctuation_only_titles_produce_different_slugs(self) -> None:
        first = PostSlug.from_title("???")
        second = PostSlug.from_title("???")
        assert first != second


class TestPostTitle:
    def test_valid_title_is_accepted(self) -> None:
        assert str(PostTitle("Cardiac Arrhythmia Tips")) == "Cardiac Arrhythmia Tips"

    def test_strips_surrounding_whitespace(self) -> None:
        assert str(PostTitle("  Hello  ")) == "Hello"

    @pytest.mark.parametrize("raw", ["", "   "])
    def test_blank_title_raises(self, raw: str) -> None:
        with pytest.raises(PostTitleRequiredError):
            PostTitle(raw)

    def test_title_over_max_length_raises(self) -> None:
        with pytest.raises(PostTitleTooLongError):
            PostTitle("a" * 301)

    def test_title_at_max_length_boundary_is_valid(self) -> None:
        title = "a" * 300
        assert str(PostTitle(title)) == title


class TestPostExcerpt:
    def test_valid_excerpt_is_accepted(self) -> None:
        excerpt = "A short summary of the post."
        assert str(PostExcerpt(excerpt)) == excerpt

    def test_strips_surrounding_whitespace(self) -> None:
        assert str(PostExcerpt("  hello  ")) == "hello"

    @pytest.mark.parametrize("raw", ["", "   "])
    def test_blank_excerpt_raises(self, raw: str) -> None:
        with pytest.raises(PostExcerptRequiredError):
            PostExcerpt(raw)

    def test_excerpt_over_max_length_raises(self) -> None:
        with pytest.raises(PostExcerptTooLongError):
            PostExcerpt("a" * 501)

    def test_excerpt_at_max_length_boundary_is_valid(self) -> None:
        excerpt = "a" * 500
        assert str(PostExcerpt(excerpt)) == excerpt


class TestPostExcerptFromBody:
    def test_generates_from_short_body(self) -> None:
        body = "This is a short post body."
        assert str(PostExcerpt.from_body(body)) == body

    def test_strips_markdown_syntax(self) -> None:
        body = "# Heading\n\nSome **bold** and _italic_ and `code`."
        excerpt = str(PostExcerpt.from_body(body))
        assert "#" not in excerpt
        assert "*" not in excerpt
        assert "`" not in excerpt

    def test_truncates_long_body_with_ellipsis(self) -> None:
        body = "word " * 100
        excerpt = str(PostExcerpt.from_body(body))
        assert excerpt.endswith("...")
        assert len(excerpt) <= 210

    def test_blank_body_raises(self) -> None:
        with pytest.raises(PostBodyRequiredError):
            PostExcerpt.from_body("   ")

    def test_collapses_whitespace(self) -> None:
        body = "Hello\n\n\nWorld"
        assert str(PostExcerpt.from_body(body)) == "Hello World"
