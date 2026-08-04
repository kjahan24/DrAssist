"""Unit tests for `JSONResponseParser`."""

import pytest

from app.modules.ai.domain.exceptions import AIProviderResponseParsingError
from app.modules.ai.infrastructure.parsers.json_parser import JSONResponseParser


class TestJSONResponseParser:
    def test_parses_plain_json(self) -> None:
        parser = JSONResponseParser()
        assert parser.parse('{"a": 1}') == {"a": 1}

    def test_parses_json_wrapped_in_a_fenced_code_block(self) -> None:
        parser = JSONResponseParser()
        raw = '```json\n{"a": 1}\n```'
        assert parser.parse(raw) == {"a": 1}

    def test_parses_json_wrapped_in_an_unlabeled_fence(self) -> None:
        parser = JSONResponseParser()
        raw = '```\n{"a": 1}\n```'
        assert parser.parse(raw) == {"a": 1}

    def test_strips_surrounding_whitespace(self) -> None:
        parser = JSONResponseParser()
        assert parser.parse('  \n{"a": 1}\n  ') == {"a": 1}

    def test_parses_a_json_array(self) -> None:
        parser = JSONResponseParser()
        assert parser.parse("[1, 2, 3]") == [1, 2, 3]

    def test_raises_normalized_error_on_malformed_json(self) -> None:
        parser = JSONResponseParser()
        with pytest.raises(AIProviderResponseParsingError):
            parser.parse("not json at all")
