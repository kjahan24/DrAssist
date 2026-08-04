"""Unit tests for `DefaultSOAPNoteParser`."""

import json

import pytest

from app.modules.soap_note_ai.domain.enums import SOAPNoteOutputFormat
from app.modules.soap_note_ai.domain.exceptions import InvalidSOAPNoteFormatError
from app.modules.soap_note_ai.infrastructure.parsing.soap_note_parser import DefaultSOAPNoteParser

_VALID_PAYLOAD = {
    "subjective": "Reports headache since yesterday",
    "objective": "BP 120/80, afebrile",
    "assessment": "Tension headache",
    "plan": "OTC analgesics, follow up in 1 week",
}


class TestParsePlainJSON:
    def test_parses_all_four_canonical_sections(self) -> None:
        parser = DefaultSOAPNoteParser()

        note = parser.parse(json.dumps(_VALID_PAYLOAD), output_format=SOAPNoteOutputFormat.JSON)

        assert note.get_section("subjective") == "Reports headache since yesterday"
        assert note.get_section("plan") == "OTC analgesics, follow up in 1 week"
        assert len(note.sections) == 4

    def test_carries_through_the_requested_output_format(self) -> None:
        parser = DefaultSOAPNoteParser()

        note = parser.parse(json.dumps(_VALID_PAYLOAD), output_format=SOAPNoteOutputFormat.MARKDOWN)

        assert note.output_format is SOAPNoteOutputFormat.MARKDOWN

    def test_preserves_the_original_raw_text(self) -> None:
        parser = DefaultSOAPNoteParser()
        raw_text = json.dumps(_VALID_PAYLOAD)

        note = parser.parse(raw_text, output_format=SOAPNoteOutputFormat.JSON)

        assert note.raw_text == raw_text


class TestParseFencedJSON:
    def test_parses_json_wrapped_in_a_labeled_fence(self) -> None:
        parser = DefaultSOAPNoteParser()
        raw = f"```json\n{json.dumps(_VALID_PAYLOAD)}\n```"

        note = parser.parse(raw, output_format=SOAPNoteOutputFormat.JSON)

        assert note.get_section("subjective") == "Reports headache since yesterday"

    def test_parses_json_wrapped_in_an_unlabeled_fence(self) -> None:
        parser = DefaultSOAPNoteParser()
        raw = f"```\n{json.dumps(_VALID_PAYLOAD)}\n```"

        note = parser.parse(raw, output_format=SOAPNoteOutputFormat.JSON)

        assert note.get_section("plan") == "OTC analgesics, follow up in 1 week"


class TestParseMissingKeys:
    def test_missing_canonical_keys_become_empty_sections(self) -> None:
        parser = DefaultSOAPNoteParser()
        partial_payload = {"subjective": "Reports headache"}

        note = parser.parse(json.dumps(partial_payload), output_format=SOAPNoteOutputFormat.JSON)

        assert note.get_section("subjective") == "Reports headache"
        assert note.get_section("plan") == ""

    def test_extra_unrecognized_keys_are_ignored(self) -> None:
        parser = DefaultSOAPNoteParser()
        payload = dict(_VALID_PAYLOAD, unexpected_key="surprise")

        note = parser.parse(json.dumps(payload), output_format=SOAPNoteOutputFormat.JSON)

        assert note.get_section("unexpected_key") is None


class TestParseFailures:
    def test_raises_on_malformed_json(self) -> None:
        parser = DefaultSOAPNoteParser()
        with pytest.raises(InvalidSOAPNoteFormatError):
            parser.parse("not json at all", output_format=SOAPNoteOutputFormat.JSON)

    def test_raises_on_empty_response(self) -> None:
        parser = DefaultSOAPNoteParser()
        with pytest.raises(InvalidSOAPNoteFormatError):
            parser.parse("   ", output_format=SOAPNoteOutputFormat.JSON)

    def test_raises_when_top_level_json_is_a_list_not_an_object(self) -> None:
        parser = DefaultSOAPNoteParser()
        with pytest.raises(InvalidSOAPNoteFormatError):
            parser.parse("[1, 2, 3]", output_format=SOAPNoteOutputFormat.JSON)

    def test_raises_when_top_level_json_is_a_scalar(self) -> None:
        parser = DefaultSOAPNoteParser()
        with pytest.raises(InvalidSOAPNoteFormatError):
            parser.parse('"just a string"', output_format=SOAPNoteOutputFormat.JSON)

    def test_raises_on_truncated_json(self) -> None:
        parser = DefaultSOAPNoteParser()
        truncated = json.dumps(_VALID_PAYLOAD)[:-5]
        with pytest.raises(InvalidSOAPNoteFormatError):
            parser.parse(truncated, output_format=SOAPNoteOutputFormat.JSON)
