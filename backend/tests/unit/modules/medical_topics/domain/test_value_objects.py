"""Tests for the Medical Topics module's domain value objects —
construction, `__post_init__` validation, and normalization."""

from uuid import uuid4

import pytest

from app.modules.medical_topics.domain.exceptions import (
    InvalidTopicColorError,
    InvalidTopicSlugError,
    TopicDescriptionRequiredError,
    TopicDescriptionTooLongError,
    TopicNameRequiredError,
    TopicNameTooLongError,
)
from app.modules.medical_topics.domain.value_objects import (
    TopicColor,
    TopicDescription,
    TopicId,
    TopicName,
    TopicSlug,
)


class TestTopicId:
    def test_wraps_a_uuid(self) -> None:
        value = uuid4()
        topic_id = TopicId(value)
        assert topic_id.value == value

    def test_str_returns_the_uuid_string(self) -> None:
        value = uuid4()
        assert str(TopicId(value)) == str(value)

    def test_equality_is_by_value(self) -> None:
        value = uuid4()
        assert TopicId(value) == TopicId(value)

    def test_inequality_for_different_values(self) -> None:
        assert TopicId(uuid4()) != TopicId(uuid4())

    def test_is_hashable_and_usable_as_a_dict_key(self) -> None:
        value = uuid4()
        mapping = {TopicId(value): "topic"}
        assert mapping[TopicId(value)] == "topic"

    def test_equal_ids_hash_the_same(self) -> None:
        value = uuid4()
        assert hash(TopicId(value)) == hash(TopicId(value))


class TestTopicSlug:
    def test_valid_slug_is_accepted(self) -> None:
        assert str(TopicSlug("cardiac-arrhythmia")) == "cardiac-arrhythmia"

    def test_normalizes_to_lowercase(self) -> None:
        assert str(TopicSlug("Cardiac-Arrhythmia")) == "cardiac-arrhythmia"

    def test_strips_surrounding_whitespace(self) -> None:
        assert str(TopicSlug("  cardiac-arrhythmia  ")) == "cardiac-arrhythmia"

    def test_single_word_slug_is_valid(self) -> None:
        assert str(TopicSlug("oncology")) == "oncology"

    def test_numeric_characters_are_valid(self) -> None:
        assert str(TopicSlug("type-2-diabetes")) == "type-2-diabetes"

    @pytest.mark.parametrize(
        "raw",
        [
            "ab",
            "a" * 65,
            "-topic",
            "topic-",
            "topic--name",
            "topic name",
            "topic_name",
            "topic!",
            "",
            "   ",
        ],
    )
    def test_invalid_slugs_raise(self, raw: str) -> None:
        with pytest.raises(InvalidTopicSlugError):
            TopicSlug(raw)

    def test_minimum_length_boundary_is_valid(self) -> None:
        assert str(TopicSlug("abc")) == "abc"

    def test_maximum_length_boundary_is_valid(self) -> None:
        slug = "a" * 64
        assert str(TopicSlug(slug)) == slug

    def test_hashable_and_usable_as_a_dict_key(self) -> None:
        mapping = {TopicSlug("oncology"): "value"}
        assert mapping[TopicSlug("oncology")] == "value"

    def test_equality_is_by_value(self) -> None:
        assert TopicSlug("oncology") == TopicSlug("oncology")


class TestTopicName:
    def test_valid_name_is_accepted(self) -> None:
        assert str(TopicName("Cardiac Arrhythmia")) == "Cardiac Arrhythmia"

    def test_strips_surrounding_whitespace(self) -> None:
        assert str(TopicName("  Cardiac Arrhythmia  ")) == "Cardiac Arrhythmia"

    @pytest.mark.parametrize("raw", ["", "   "])
    def test_blank_name_raises(self, raw: str) -> None:
        with pytest.raises(TopicNameRequiredError):
            TopicName(raw)

    def test_name_over_max_length_raises(self) -> None:
        with pytest.raises(TopicNameTooLongError):
            TopicName("a" * 201)

    def test_name_at_max_length_boundary_is_valid(self) -> None:
        name = "a" * 200
        assert str(TopicName(name)) == name


class TestTopicDescription:
    def test_valid_description_is_accepted(self) -> None:
        description = "Covers irregular heart rhythms."
        assert str(TopicDescription(description)) == description

    def test_strips_surrounding_whitespace(self) -> None:
        assert str(TopicDescription("  hello  ")) == "hello"

    @pytest.mark.parametrize("raw", ["", "   "])
    def test_blank_description_raises(self, raw: str) -> None:
        with pytest.raises(TopicDescriptionRequiredError):
            TopicDescription(raw)

    def test_description_over_max_length_raises(self) -> None:
        with pytest.raises(TopicDescriptionTooLongError):
            TopicDescription("a" * 2001)

    def test_description_at_max_length_boundary_is_valid(self) -> None:
        description = "a" * 2000
        assert str(TopicDescription(description)) == description


class TestTopicColor:
    def test_valid_color_is_accepted(self) -> None:
        assert str(TopicColor("#FF5733")) == "#FF5733"

    def test_normalizes_to_uppercase(self) -> None:
        assert str(TopicColor("#ff5733")) == "#FF5733"

    def test_strips_surrounding_whitespace(self) -> None:
        assert str(TopicColor("  #FF5733  ")) == "#FF5733"

    def test_equal_after_case_normalization(self) -> None:
        assert TopicColor("#ff5733") == TopicColor("#FF5733")

    @pytest.mark.parametrize(
        "raw",
        [
            "FF5733",  # missing #
            "#FF573",  # too short
            "#FF57333",  # too long
            "#GG5733",  # invalid hex digits
            "",
            "red",
        ],
    )
    def test_invalid_colors_raise(self, raw: str) -> None:
        with pytest.raises(InvalidTopicColorError):
            TopicColor(raw)
