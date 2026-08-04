"""Unit tests for `DefaultCopilotOutputParser`."""

import pytest

from app.modules.ai_copilot.domain.enums import CopilotOutputFormat
from app.modules.ai_copilot.domain.exceptions import StructuredResponseParsingError
from app.modules.ai_copilot.infrastructure.parsing.structured_output_parser import (
    DefaultCopilotOutputParser,
)


class TestParseJSON:
    def test_parses_plain_json_object(self) -> None:
        parser = DefaultCopilotOutputParser()
        assert parser.parse('{"a": 1}', CopilotOutputFormat.JSON) == {"a": 1}

    def test_parses_json_wrapped_in_a_fenced_code_block(self) -> None:
        parser = DefaultCopilotOutputParser()
        raw = '```json\n{"a": 1}\n```'
        assert parser.parse(raw, CopilotOutputFormat.JSON) == {"a": 1}

    def test_parses_json_wrapped_in_an_unlabeled_fence(self) -> None:
        parser = DefaultCopilotOutputParser()
        raw = '```\n{"a": 1}\n```'
        assert parser.parse(raw, CopilotOutputFormat.JSON) == {"a": 1}

    def test_parses_a_json_array(self) -> None:
        parser = DefaultCopilotOutputParser()
        assert parser.parse("[1, 2, 3]", CopilotOutputFormat.JSON) == [1, 2, 3]

    def test_raises_normalized_error_on_malformed_json(self) -> None:
        parser = DefaultCopilotOutputParser()
        with pytest.raises(StructuredResponseParsingError):
            parser.parse("not json at all", CopilotOutputFormat.JSON)


class TestParseMarkdown:
    def test_splits_sections_by_heading(self) -> None:
        parser = DefaultCopilotOutputParser()
        raw = "# Section One\nBody one.\n\n## Section Two\nBody two."
        result = parser.parse(raw, CopilotOutputFormat.MARKDOWN)
        assert result == {"Section One": "Body one.", "Section Two": "Body two."}

    def test_document_with_no_headings_becomes_a_single_content_section(self) -> None:
        parser = DefaultCopilotOutputParser()
        result = parser.parse("Just plain markdown text.", CopilotOutputFormat.MARKDOWN)
        assert result == {"content": "Just plain markdown text."}

    def test_raises_on_empty_markdown(self) -> None:
        parser = DefaultCopilotOutputParser()
        with pytest.raises(StructuredResponseParsingError):
            parser.parse("   ", CopilotOutputFormat.MARKDOWN)


class TestParseText:
    def test_strips_surrounding_whitespace(self) -> None:
        parser = DefaultCopilotOutputParser()
        assert parser.parse("  hello world  ", CopilotOutputFormat.TEXT) == "hello world"

    def test_empty_text_parses_to_an_empty_string(self) -> None:
        parser = DefaultCopilotOutputParser()
        assert parser.parse("   ", CopilotOutputFormat.TEXT) == ""
