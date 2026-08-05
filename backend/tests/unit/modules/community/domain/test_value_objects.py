"""Tests for the Community module's domain value objects — construction,
`__post_init__` validation, and normalization."""

from uuid import uuid4

import pytest

from app.modules.community.domain.exceptions import (
    CommunityDescriptionRequiredError,
    CommunityDescriptionTooLongError,
    CommunityNameRequiredError,
    CommunityNameTooLongError,
    InvalidCommunitySlugError,
)
from app.modules.community.domain.value_objects import (
    CommunityDescription,
    CommunityId,
    CommunityName,
    CommunitySlug,
)


class TestCommunityId:
    def test_wraps_a_uuid(self) -> None:
        value = uuid4()
        community_id = CommunityId(value)
        assert community_id.value == value

    def test_str_returns_the_uuid_string(self) -> None:
        value = uuid4()
        assert str(CommunityId(value)) == str(value)

    def test_equality_is_by_value(self) -> None:
        value = uuid4()
        assert CommunityId(value) == CommunityId(value)

    def test_inequality_for_different_values(self) -> None:
        assert CommunityId(uuid4()) != CommunityId(uuid4())

    def test_is_hashable_and_usable_as_a_dict_key(self) -> None:
        value = uuid4()
        mapping = {CommunityId(value): "community"}
        assert mapping[CommunityId(value)] == "community"

    def test_equal_ids_hash_the_same(self) -> None:
        value = uuid4()
        assert hash(CommunityId(value)) == hash(CommunityId(value))


class TestCommunitySlug:
    def test_valid_slug_is_accepted(self) -> None:
        assert str(CommunitySlug("diabetes-support")) == "diabetes-support"

    def test_normalizes_to_lowercase(self) -> None:
        assert str(CommunitySlug("Diabetes-Support")) == "diabetes-support"

    def test_strips_surrounding_whitespace(self) -> None:
        assert str(CommunitySlug("  diabetes-support  ")) == "diabetes-support"

    def test_single_word_slug_is_valid(self) -> None:
        assert str(CommunitySlug("oncology")) == "oncology"

    def test_numeric_characters_are_valid(self) -> None:
        assert str(CommunitySlug("type-2-diabetes")) == "type-2-diabetes"

    @pytest.mark.parametrize(
        "raw",
        [
            "ab",  # too short
            "a" * 65,  # too long
            "-diabetes",  # leading hyphen
            "diabetes-",  # trailing hyphen
            "diabetes--support",  # consecutive hyphens
            "diabetes support",  # space
            "diabetes_support",  # underscore
            "diabetes!",  # punctuation
            "",  # empty
            "   ",  # blank
        ],
    )
    def test_invalid_slugs_raise(self, raw: str) -> None:
        with pytest.raises(InvalidCommunitySlugError):
            CommunitySlug(raw)

    def test_minimum_length_boundary_is_valid(self) -> None:
        assert str(CommunitySlug("abc")) == "abc"

    def test_maximum_length_boundary_is_valid(self) -> None:
        slug = "a" * 64
        assert str(CommunitySlug(slug)) == slug

    def test_multiple_hyphens_in_separate_positions_are_valid(self) -> None:
        assert str(CommunitySlug("type-2-diabetes-support")) == "type-2-diabetes-support"

    def test_hashable_and_usable_as_a_dict_key(self) -> None:
        mapping = {CommunitySlug("oncology"): "value"}
        assert mapping[CommunitySlug("oncology")] == "value"

    def test_mixed_case_with_numbers_normalizes_correctly(self) -> None:
        assert str(CommunitySlug("Type2-DIABETES")) == "type2-diabetes"

    def test_equality_is_by_value(self) -> None:
        assert CommunitySlug("oncology") == CommunitySlug("oncology")


class TestCommunityName:
    def test_valid_name_is_accepted(self) -> None:
        assert str(CommunityName("Diabetes Support")) == "Diabetes Support"

    def test_strips_surrounding_whitespace(self) -> None:
        assert str(CommunityName("  Diabetes Support  ")) == "Diabetes Support"

    @pytest.mark.parametrize("raw", ["", "   "])
    def test_blank_name_raises(self, raw: str) -> None:
        with pytest.raises(CommunityNameRequiredError):
            CommunityName(raw)

    def test_name_over_max_length_raises(self) -> None:
        with pytest.raises(CommunityNameTooLongError):
            CommunityName("a" * 201)

    def test_name_at_max_length_boundary_is_valid(self) -> None:
        name = "a" * 200
        assert str(CommunityName(name)) == name


class TestCommunityDescription:
    def test_valid_description_is_accepted(self) -> None:
        description = "A support group for people managing diabetes."
        assert str(CommunityDescription(description)) == description

    def test_strips_surrounding_whitespace(self) -> None:
        assert str(CommunityDescription("  hello  ")) == "hello"

    @pytest.mark.parametrize("raw", ["", "   "])
    def test_blank_description_raises(self, raw: str) -> None:
        with pytest.raises(CommunityDescriptionRequiredError):
            CommunityDescription(raw)

    def test_description_over_max_length_raises(self) -> None:
        with pytest.raises(CommunityDescriptionTooLongError):
            CommunityDescription("a" * 2001)

    def test_description_at_max_length_boundary_is_valid(self) -> None:
        description = "a" * 2000
        assert str(CommunityDescription(description)) == description
