"""Unit tests for `extract_json_object`."""

import json

import pytest

from app.shared.infrastructure.text_processing.json_extraction import extract_json_object


class TestExtractPlainJSON:
    def test_parses_a_plain_json_object(self) -> None:
        assert extract_json_object('{"a": 1}') == {"a": 1}

    def test_parses_a_json_object_with_multiple_keys(self) -> None:
        payload = {"a": 1, "b": "two", "c": [1, 2, 3]}
        assert extract_json_object(json.dumps(payload)) == payload


class TestExtractFencedJSON:
    def test_parses_json_wrapped_in_a_labeled_fence(self) -> None:
        raw = '```json\n{"a": 1}\n```'
        assert extract_json_object(raw) == {"a": 1}

    def test_parses_json_wrapped_in_an_unlabeled_fence(self) -> None:
        raw = '```\n{"a": 1}\n```'
        assert extract_json_object(raw) == {"a": 1}

    def test_strips_surrounding_whitespace(self) -> None:
        assert extract_json_object('  \n{"a": 1}\n  ') == {"a": 1}


class TestExtractFailures:
    def test_raises_value_error_on_malformed_json(self) -> None:
        with pytest.raises(ValueError, match="malformed JSON"):
            extract_json_object("not json at all")

    def test_raises_value_error_on_empty_text(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            extract_json_object("   ")

    def test_raises_value_error_when_top_level_is_a_list(self) -> None:
        with pytest.raises(ValueError, match="expected a JSON object"):
            extract_json_object("[1, 2, 3]")

    def test_raises_value_error_when_top_level_is_a_scalar(self) -> None:
        with pytest.raises(ValueError, match="expected a JSON object"):
            extract_json_object('"just a string"')

    def test_raises_value_error_on_truncated_json(self) -> None:
        truncated = json.dumps({"a": 1})[:-3]
        with pytest.raises(ValueError):
            extract_json_object(truncated)
