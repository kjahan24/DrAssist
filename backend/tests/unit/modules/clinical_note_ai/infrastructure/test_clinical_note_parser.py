"""Unit tests for `DefaultClinicalNoteParser`."""

import json

import pytest

from app.modules.clinical_note_ai.domain.enums import ClinicalNoteOutputFormat
from app.modules.clinical_note_ai.domain.exceptions import InvalidClinicalNoteFormatError
from app.modules.clinical_note_ai.infrastructure.parsing.clinical_note_parser import (
    DefaultClinicalNoteParser,
)

_VALID_PAYLOAD = {
    "chief_complaint": "Headache",
    "history_of_present_illness": "Gradual onset",
    "review_of_systems": "Negative",
    "physical_examination": "Unremarkable",
    "assessment": "Tension headache",
    "plan": "OTC analgesics",
}


class TestParsePlainJSON:
    def test_parses_all_six_canonical_sections(self) -> None:
        parser = DefaultClinicalNoteParser()

        note = parser.parse(json.dumps(_VALID_PAYLOAD), output_format=ClinicalNoteOutputFormat.JSON)

        assert note.get_section("chief_complaint") == "Headache"
        assert note.get_section("plan") == "OTC analgesics"
        assert len(note.sections) == 6

    def test_carries_through_the_requested_output_format(self) -> None:
        parser = DefaultClinicalNoteParser()

        note = parser.parse(
            json.dumps(_VALID_PAYLOAD), output_format=ClinicalNoteOutputFormat.MARKDOWN
        )

        assert note.output_format is ClinicalNoteOutputFormat.MARKDOWN

    def test_preserves_the_original_raw_text(self) -> None:
        parser = DefaultClinicalNoteParser()
        raw_text = json.dumps(_VALID_PAYLOAD)

        note = parser.parse(raw_text, output_format=ClinicalNoteOutputFormat.JSON)

        assert note.raw_text == raw_text


class TestParseFencedJSON:
    def test_parses_json_wrapped_in_a_labeled_fence(self) -> None:
        parser = DefaultClinicalNoteParser()
        raw = f"```json\n{json.dumps(_VALID_PAYLOAD)}\n```"

        note = parser.parse(raw, output_format=ClinicalNoteOutputFormat.JSON)

        assert note.get_section("chief_complaint") == "Headache"

    def test_parses_json_wrapped_in_an_unlabeled_fence(self) -> None:
        parser = DefaultClinicalNoteParser()
        raw = f"```\n{json.dumps(_VALID_PAYLOAD)}\n```"

        note = parser.parse(raw, output_format=ClinicalNoteOutputFormat.JSON)

        assert note.get_section("plan") == "OTC analgesics"


class TestParseMissingKeys:
    def test_missing_canonical_keys_become_empty_sections(self) -> None:
        parser = DefaultClinicalNoteParser()
        partial_payload = {"chief_complaint": "Headache"}

        note = parser.parse(
            json.dumps(partial_payload), output_format=ClinicalNoteOutputFormat.JSON
        )

        assert note.get_section("chief_complaint") == "Headache"
        assert note.get_section("plan") == ""

    def test_extra_unrecognized_keys_are_ignored(self) -> None:
        parser = DefaultClinicalNoteParser()
        payload = dict(_VALID_PAYLOAD, unexpected_key="surprise")

        note = parser.parse(json.dumps(payload), output_format=ClinicalNoteOutputFormat.JSON)

        assert note.get_section("unexpected_key") is None


class TestParseFailures:
    def test_raises_on_malformed_json(self) -> None:
        parser = DefaultClinicalNoteParser()
        with pytest.raises(InvalidClinicalNoteFormatError):
            parser.parse("not json at all", output_format=ClinicalNoteOutputFormat.JSON)

    def test_raises_on_empty_response(self) -> None:
        parser = DefaultClinicalNoteParser()
        with pytest.raises(InvalidClinicalNoteFormatError):
            parser.parse("   ", output_format=ClinicalNoteOutputFormat.JSON)

    def test_raises_when_top_level_json_is_a_list_not_an_object(self) -> None:
        parser = DefaultClinicalNoteParser()
        with pytest.raises(InvalidClinicalNoteFormatError):
            parser.parse("[1, 2, 3]", output_format=ClinicalNoteOutputFormat.JSON)

    def test_raises_when_top_level_json_is_a_scalar(self) -> None:
        parser = DefaultClinicalNoteParser()
        with pytest.raises(InvalidClinicalNoteFormatError):
            parser.parse('"just a string"', output_format=ClinicalNoteOutputFormat.JSON)

    def test_raises_on_truncated_json(self) -> None:
        parser = DefaultClinicalNoteParser()
        truncated = json.dumps(_VALID_PAYLOAD)[:-5]
        with pytest.raises(InvalidClinicalNoteFormatError):
            parser.parse(truncated, output_format=ClinicalNoteOutputFormat.JSON)
