"""Unit tests for `SOAPNoteRenderer`."""

import json

from app.modules.soap_note_ai.application.services.soap_note_renderer import SOAPNoteRenderer
from app.modules.soap_note_ai.domain.enums import SOAPNoteOutputFormat
from app.modules.soap_note_ai.domain.value_objects import SOAPNote, SOAPSection


def _note() -> SOAPNote:
    return SOAPNote(
        sections=(
            SOAPSection(name="subjective", content="Reports headache"),
            SOAPSection(name="objective", content="BP 120/80"),
            SOAPSection(name="assessment", content="Tension headache"),
            SOAPSection(name="plan", content="OTC analgesics"),
        ),
        raw_text="{}",
        output_format=SOAPNoteOutputFormat.JSON,
    )


class TestSOAPNoteRendererJSON:
    def test_renders_valid_json_with_all_sections(self) -> None:
        result = SOAPNoteRenderer().render(_note(), SOAPNoteOutputFormat.JSON)

        payload = json.loads(result)
        assert payload["subjective"] == "Reports headache"
        assert payload["plan"] == "OTC analgesics"


class TestSOAPNoteRendererMarkdown:
    def test_renders_a_heading_per_section(self) -> None:
        result = SOAPNoteRenderer().render(_note(), SOAPNoteOutputFormat.MARKDOWN)

        assert "## Subjective" in result
        assert "## Objective" in result
        assert "## Assessment" in result
        assert "## Plan" in result
        assert "Reports headache" in result

    def test_sections_are_separated_by_a_blank_line(self) -> None:
        result = SOAPNoteRenderer().render(_note(), SOAPNoteOutputFormat.MARKDOWN)

        assert "\n\n" in result


class TestSOAPNoteRendererText:
    def test_renders_uppercased_labels(self) -> None:
        result = SOAPNoteRenderer().render(_note(), SOAPNoteOutputFormat.TEXT)

        assert "SUBJECTIVE:" in result
        assert "OBJECTIVE:" in result
        assert "ASSESSMENT:" in result
        assert "PLAN:" in result

    def test_content_appears_beneath_each_label(self) -> None:
        result = SOAPNoteRenderer().render(_note(), SOAPNoteOutputFormat.TEXT)

        assert "SUBJECTIVE:\nReports headache" in result
